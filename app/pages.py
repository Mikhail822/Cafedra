from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QGridLayout, QLineEdit, QMenu, QMessageBox, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
)
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from .database import PROJECT_ROOT, SessionLocal
from .dialogs import AdminUserDialog, LABELS, RecordDialog
from .models import (
    Announcement, Audience, Category, Display, Event, Media, MODELS,
    Playlist, PlaylistItem, Role, Schedule, Source, User,
)

TITLES = {
    "roles": "Роли", "users": "Пользователи", "categories": "Категории",
    "sources": "Источники", "audiences": "Целевые аудитории", "events": "Мероприятия",
    "media": "Медиаматериалы", "announcements": "Объявления", "playlists": "Плейлисты",
    "playlist_items": "Элементы плейлистов", "displays": "Экраны демонстрации",
    "schedules": "Расписание",
}
FIELDS = {
    "roles": ["role_name", "description"],
    "users": ["username", "full_name", "role_id", "created_at", "is_active"],
    "categories": ["name", "description"],
    "sources": ["name", "source_type", "url", "description"],
    "audiences": ["name", "description"],
    "events": ["title", "category_id", "event_date", "location", "organizer_id", "status"],
    "media": ["title", "media_type", "category_id", "created_at", "is_active"],
    "announcements": ["title", "category_id", "audience_id", "start_date", "end_date", "author_id", "is_active"],
    "playlists": ["name", "description", "created_by", "created_at", "is_active"],
    "playlist_items": ["playlist_id", "position", "display_duration", "media_id", "announcement_id", "event_id"],
    "displays": ["name", "location", "description", "is_active"],
    "schedules": ["name", "playlist_id", "display_id", "start_date", "end_date", "start_time", "end_time", "is_active"],
}
REFERENCES = {
    "role_id": (Role, "role_id", "role_name"),
    "category_id": (Category, "category_id", "name"),
    "source_id": (Source, "source_id", "name"),
    "audience_id": (Audience, "audience_id", "name"),
    "organizer_id": (User, "user_id", "full_name"),
    "added_by": (User, "user_id", "full_name"),
    "author_id": (User, "user_id", "full_name"),
    "created_by": (User, "user_id", "full_name"),
    "playlist_id": (Playlist, "playlist_id", "name"),
    "display_id": (Display, "display_id", "name"),
    "media_id": (Media, "media_id", "title"),
    "announcement_id": (Announcement, "announcement_id", "title"),
    "event_id": (Event, "event_id", "title"),
}
OWNER_FIELD = {"events": "organizer_id", "media": "added_by", "announcements": "author_id", "playlists": "created_by"}
SEARCH_HINTS = {
    "roles": "Поиск по названию роли или описанию…", "users": "Поиск по ФИО или логину…",
    "categories": "Поиск по названию или описанию категории…", "sources": "Поиск по источнику или типу…",
    "audiences": "Поиск по названию аудитории…", "events": "Поиск по мероприятию, месту или статусу…",
    "media": "Поиск по названию медиаматериала…", "announcements": "Поиск по заголовку объявления…",
    "playlists": "Поиск по названию плейлиста…", "playlist_items": "Поиск по составу плейлиста…",
    "displays": "Поиск по названию экрана или расположению…", "schedules": "Поиск по названию расписания…",
}
ADD_LABELS = {
    "events": "Добавить мероприятие", "media": "Добавить материал",
    "announcements": "Добавить объявление", "categories": "Добавить категорию",
    "sources": "Добавить источник", "audiences": "Добавить аудиторию",
    "playlists": "Создать плейлист", "schedules": "Создать расписание",
    "displays": "Добавить экран", "users": "Добавить пользователя",
    "roles": "Добавить роль", "playlist_items": "Добавить элемент",
}


class CrudPage(QWidget):
    def __init__(self, table_name: str, user: User, role: str, parent=None, controller=None):
        super().__init__(parent)
        self.table_name, self.model = table_name, MODELS[table_name]
        self.pk_name = next(iter(self.model.__table__.primary_key.columns)).name
        self.user, self.role = user, role
        self.controller = controller
        self.owner_field = OWNER_FIELD.get(table_name)
        self.fields = FIELDS[table_name]
        self.editable = self._can_edit()
        self.search = QLineEdit()
        self.search.setPlaceholderText(SEARCH_HINTS.get(table_name, "Поиск…"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.refresh)
        extra_columns = 1 if table_name in {"playlists", "schedules"} else 0
        self.table = QTableWidget(0, len(self.fields) + extra_columns)
        headers = [LABELS.get(f, f) for f in self.fields]
        if table_name == "playlists":
            headers.append("Элементов")
        elif table_name == "schedules":
            headers.append("Состояние")
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.setMinimumHeight(250)
        self.table.doubleClicked.connect(self._double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.add_button = QPushButton("Добавить")
        self.add_button.setVisible(self.editable)
        self.add_button.setText(ADD_LABELS.get(table_name, "Добавить"))
        self.add_button.clicked.connect(self.add_record)
        self.action_button = QPushButton("Действия")
        self.action_menu = QMenu(self.action_button)
        self.edit_action = self.action_menu.addAction("Изменить запись", self.edit_record)
        self.delete_action = self.action_menu.addAction("Удалить запись", self.delete_record)
        self.delete_action.setText("Деактивировать пользователя" if table_name == "users" else "Удалить запись")
        self.action_menu.addSeparator()
        self.playlist_action = self.action_menu.addAction("Состав плейлиста", self.manage_playlist)
        self.preview_action = self.action_menu.addAction("Предпросмотр", self.preview_selected)
        self.preview_button = QPushButton("Просмотреть" if table_name == "media" else "Предпросмотр")
        self.preview_button.setVisible(table_name in {"media", "playlists"})
        self.preview_button.clicked.connect(self.preview_selected)
        self.refresh_action = self.action_menu.addAction("Обновить список", self.refresh)
        self.action_button.setMenu(self.action_menu)
        self.action_button.setEnabled(True)
        self.table.itemSelectionChanged.connect(self._update_actions)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.addWidget(self.search, 1)
        if self.editable:
            toolbar.addWidget(self.add_button)
        if table_name in {"media", "playlists"}:
            toolbar.addWidget(self.preview_button)
        toolbar.addWidget(self.action_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addLayout(toolbar)
        if table_name == "events":
            from PySide6.QtCore import QDate
            self.category_filter = QComboBox()
            self.category_filter.addItem("Все категории", None)
            with SessionLocal() as session:
                for category in session.scalars(select(Category).order_by(Category.name)):
                    self.category_filter.addItem(category.name, category.category_id)
            self.from_enabled, self.to_enabled = QCheckBox("С даты"), QCheckBox("По дату")
            self.from_date, self.to_date = QDateEdit(), QDateEdit()
            self.from_date.setEnabled(False)
            self.to_date.setEnabled(False)
            self.from_enabled.toggled.connect(self.from_date.setEnabled)
            self.to_enabled.toggled.connect(self.to_date.setEnabled)
            for edit in (self.from_date, self.to_date):
                edit.setCalendarPopup(True)
                edit.setDisplayFormat("dd.MM.yyyy")
                edit.setDate(QDate.currentDate())
            self.category_filter.currentIndexChanged.connect(self.refresh)
            self.from_enabled.toggled.connect(self.refresh)
            self.to_enabled.toggled.connect(self.refresh)
            self.from_date.dateChanged.connect(self.refresh)
            self.to_date.dateChanged.connect(self.refresh)
            filter_panel = QFrame()
            filter_panel.setObjectName("panel")
            filters = QHBoxLayout(filter_panel)
            filters.setContentsMargins(12, 10, 12, 10)
            filters.setSpacing(10)
            filters.addWidget(QLabel("Категория"))
            filters.addWidget(self.category_filter)
            filters.addWidget(self.from_enabled)
            filters.addWidget(self.from_date)
            filters.addWidget(self.to_enabled)
            filters.addWidget(self.to_date)
            filters.addStretch(1)
            layout.addWidget(filter_panel)
        self.content_stack = QStackedWidget()
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(10)
        self.empty_title = QLabel("Пока нет записей")
        self.empty_title.setObjectName("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_description = QLabel("Добавьте первую запись, чтобы она появилась в этом разделе.")
        self.empty_description.setObjectName("emptyDescription")
        self.empty_description.setWordWrap(True)
        self.empty_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_description.setMaximumWidth(480)
        self.empty_add = QPushButton(ADD_LABELS.get(table_name, "Добавить"))
        self.empty_add.clicked.connect(self.add_record)
        self.empty_add.setVisible(self.editable)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_description, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(self.empty_add, 0, Qt.AlignmentFlag.AlignHCenter)
        self.content_stack.addWidget(self.table)
        self.content_stack.addWidget(self.empty_state)
        layout.addWidget(self.content_stack, 1)
        self.refresh()

    def _can_edit(self) -> bool:
        if self.role == "admin":
            return True
        return self.table_name in OWNER_FIELD

    def _records(self, session, term: str):
        query = select(self.model)
        if term:
            search_fields = [f for f in self.fields if f in {
                "title", "name", "username", "full_name", "content", "location", "role_name", "source_type", "status"
            }]
            if search_fields:
                query = query.where(or_(*(getattr(self.model, field).ilike(f"%{term}%") for field in search_fields)))
        if self.table_name == "events":
            category_id = self.category_filter.currentData()
            if category_id is not None:
                query = query.where(Event.category_id == category_id)
            if self.from_enabled.isChecked():
                query = query.where(func.date(Event.event_date) >= self.from_date.date().toPython())
            if self.to_enabled.isChecked():
                query = query.where(func.date(Event.event_date) <= self.to_date.date().toPython())
        if self.role != "admin" and self.owner_field:
            if self.table_name == "events":
                pass  # Editors can view all events, but may mutate only their own.
            else:
                query = query.where(getattr(self.model, self.owner_field) == self.user.user_id)
        return session.scalars(query.order_by(getattr(self.model, self.pk_name).desc())).all()

    def refresh(self, *_):
        try:
            with SessionLocal() as session:
                records = self._records(session, self.search.text().strip())
                self.table.setRowCount(len(records))
                for row_index, record in enumerate(records):
                    for col_index, name in enumerate(self.fields):
                        value = getattr(record, name)
                        if name in REFERENCES and value is not None:
                            model, pk, label = REFERENCES[name]
                            value = session.scalar(select(getattr(model, label)).where(getattr(model, pk) == value)) or value
                        elif isinstance(value, bool):
                            pending_owner = self.owner_field and getattr(record, self.owner_field) == self.user.user_id
                            value = "Активен" if value else (
                                "На проверке" if self.role != "admin" and pending_owner
                                and name == "is_active" else "Неактивен"
                            )
                        elif name == "media_type" and value:
                            value = "Изображение" if value == "image" else "Видео"
                        elif name == "status" and value:
                            value = {"planned": "Запланировано", "ongoing": "Идёт",
                                     "completed": "Завершено", "cancelled": "Отменено"}.get(value, value)
                        elif name == "source_type" and value:
                            value = {"internal": "Внутренний", "social": "Социальная сеть", "website": "Веб-сайт"}.get(value, value)
                        elif value is None:
                            value = "—"
                        elif isinstance(value, datetime):
                            value = value.strftime("%d.%m.%Y %H:%M")
                        elif isinstance(value, date):
                            value = value.strftime("%d.%m.%Y")
                        item = QTableWidgetItem(str(value))
                        item.setToolTip(str(value))
                        item.setData(Qt.ItemDataRole.UserRole, getattr(record, self.pk_name))
                        if name == "is_active":
                            if record.is_active:
                                item.setBackground(QColor("#E8F5EE")); item.setForeground(QColor("#16713A"))
                            elif self.role != "admin" and self.owner_field and getattr(record, self.owner_field) == self.user.user_id:
                                item.setBackground(QColor("#FFF5DD")); item.setForeground(QColor("#946200"))
                            else:
                                item.setBackground(QColor("#EEF0F5")); item.setForeground(QColor("#555B6E"))
                        if self.table_name == "media" and name == "title" and record.media_type == "image":
                            image_path = PROJECT_ROOT / record.file_path
                            if image_path.is_file():
                                pixmap = QPixmap(str(image_path))
                                if not pixmap.isNull():
                                    item.setIcon(QIcon(pixmap.scaled(50, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                                                      Qt.TransformationMode.SmoothTransformation)))
                        self.table.setItem(row_index, col_index, item)
                    if self.table_name == "playlists":
                        count = session.scalar(
                            select(func.count()).select_from(PlaylistItem).where(
                                PlaylistItem.playlist_id == record.playlist_id
                            )
                        ) or 0
                        self.table.setItem(row_index, len(self.fields), QTableWidgetItem(str(count)))
                    elif self.table_name == "schedules":
                        now = datetime.now()
                        if not record.is_active:
                            state = "Отключено"
                        elif record.start_date <= now.date() <= record.end_date and record.start_time <= now.time() < record.end_time:
                            state = ("Идёт показ" if self.controller and record.display_id in self.controller.manual_demos
                                     else "Ожидание запуска")
                        elif now.date() < record.start_date or (now.date() == record.start_date and now.time() < record.start_time):
                            state = "Ожидание"
                        else:
                            state = "Завершено"
                        cell = QTableWidgetItem(state)
                        cell.setData(Qt.ItemDataRole.UserRole, getattr(record, self.pk_name))
                        colors = {"Идёт показ": ("#E8F5EE", "#16713A"), "Ожидание": ("#FFF5DD", "#946200"),
                                  "Ожидание запуска": ("#FFF5DD", "#946200"),
                                  "Завершено": ("#EEF0F5", "#555B6E"), "Отключено": ("#FDECEC", "#A33A3A")}
                        bg, fg = colors[state]
                        cell.setBackground(QColor(bg)); cell.setForeground(QColor(fg))
                        self.table.setItem(row_index, len(self.fields), cell)
                    self.table.item(row_index, 0).setData(Qt.ItemDataRole.UserRole, getattr(record, self.pk_name))
                    self.table.setRowHeight(row_index, 52 if self.table_name == "media" else 42)
                header = self.table.horizontalHeader()
                header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
                if self.fields and self.fields[0] in {"title", "name"}:
                    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
                if self.table_name in {"media", "schedules"}:
                    header.setStretchLastSection(True)
                if records:
                    self.content_stack.setCurrentWidget(self.table)
                else:
                    filtered = bool(self.search.text().strip())
                    self.empty_title.setText("Ничего не найдено" if filtered else "Пока здесь нет записей")
                    self.empty_description.setText(
                        "Измените запрос поиска или сбросьте фильтры." if filtered else
                        f"Добавьте первую запись в раздел «{TITLES[self.table_name]}»."
                    )
                    self.empty_add.setVisible(self.editable and not filtered)
                    self.content_stack.setCurrentWidget(self.empty_state)
                self._update_actions()
        except Exception as exc:
            self._error("Не удалось загрузить данные", exc)

    def _update_actions(self, *_):
        selected = self.table.currentRow() >= 0
        self.action_button.setEnabled(True)
        self.edit_action.setEnabled(selected and self.editable)
        self.delete_action.setEnabled(selected and self.editable)
        self.delete_action.setText("Деактивировать пользователя" if self.table_name == "users" else "Удалить запись")
        self.playlist_action.setVisible(self.table_name == "playlists")
        self.playlist_action.setEnabled(selected and self.table_name == "playlists")
        self.preview_action.setVisible(self.table_name in {"media", "playlists"})
        self.preview_action.setEnabled(selected and self.table_name in {"media", "playlists"})
        self.preview_button.setEnabled(selected and self.table_name in {"media", "playlists"})

    def _context_menu(self, position):
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        self.table.selectRow(row)
        self._update_actions()
        self.action_menu.exec(self.table.viewport().mapToGlobal(position))

    def _selected_record(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, TITLES[self.table_name], "Сначала выберите запись.")
            return None
        key = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        with SessionLocal() as session:
            return session.get(self.model, key)

    def _may_mutate(self, record) -> bool:
        if self.role == "admin" or not self.owner_field:
            return self.role == "admin"
        # An event may already be referenced by an approved, active playlist.
        # Editors can submit new events, but only an admin can change an existing one.
        if self.table_name == "events":
            return False
        return getattr(record, self.owner_field) == self.user.user_id

    def add_record(self):
        if not self.editable:
            return
        if self.table_name == "users":
            dialog = AdminUserDialog(parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._save_new_user(dialog.values_out)
            return
        fixed = {}
        if self.role != "admin" and self.owner_field:
            fixed[self.owner_field] = self.user.user_id
        if self.role != "admin" and self.table_name in {"media", "announcements", "playlists"}:
            fixed["is_active"] = False
        dialog = RecordDialog(self.model, fixed=fixed, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save(dialog.values_out, requires_approval=self.role != "admin" and
                       self.table_name in {"media", "announcements", "playlists"})

    def _save_new_user(self, values: dict):
        import bcrypt
        try:
            password_hash = bcrypt.hashpw(values.pop("password").encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")
            with SessionLocal.begin() as session:
                session.add(User(password_hash=password_hash, **values))
        except IntegrityError as exc:
            self._error("Такой логин уже существует", exc.orig)
            return
        except Exception as exc:
            self._error("Не удалось создать пользователя", exc)
            return
        self.refresh()
        QMessageBox.information(self, "Пользователь создан", "Новая учётная запись добавлена.")

    def edit_record(self):
        record = self._selected_record()
        if record is None:
            return
        if not self._may_mutate(record):
            QMessageBox.warning(self, "Доступ запрещён", "Редактор может изменять только собственные материалы.")
            return
        values = {column.name: getattr(record, column.name) for column in self.model.__table__.columns}
        fixed = {}
        needs_approval = self.role != "admin" and self.table_name in {"media", "announcements", "playlists"}
        if needs_approval:
            fixed["is_active"] = False
        dialog = RecordDialog(self.model, values=values, fixed=fixed, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._save(dialog.values_out, getattr(record, self.pk_name), requires_approval=needs_approval)

    def _save(self, values: dict, key=None, requires_approval=False):
        try:
            with SessionLocal.begin() as session:
                record = session.get(self.model, key) if key is not None else self.model()
                if key is None:
                    session.add(record)
                for name, value in values.items():
                    setattr(record, name, value)
        except IntegrityError as exc:
            self._error("Запись нарушает ограничение базы данных", exc.orig)
            return
        except Exception as exc:
            self._error("Не удалось сохранить запись", exc)
            return
        self.refresh()
        message = ("Сохранено как черновик. Перед показом администратор должен проверить и активировать запись."
                   if requires_approval else "Изменения сохранены в базе данных.")
        QMessageBox.information(self, "Сохранено", message)

    def delete_record(self):
        record = self._selected_record()
        if record is None:
            return
        if not self._may_mutate(record):
            QMessageBox.warning(self, "Доступ запрещён", "Редактор может удалять только собственные материалы.")
            return
        if self.table_name == "users":
            if not record.is_active:
                QMessageBox.information(self, "Учётная запись", "Эта учётная запись уже деактивирована.")
                return
            if QMessageBox.question(
                self, "Деактивация пользователя",
                f"Заблокировать вход для пользователя «{record.username}»? Его материалы и история сохранятся.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            ) != QMessageBox.StandardButton.Yes:
                return
            try:
                with SessionLocal.begin() as session:
                    current = session.get(User, record.user_id)
                    current.is_active = False
            except Exception as exc:
                self._error("Не удалось деактивировать пользователя", exc)
                return
            self.refresh()
            QMessageBox.information(self, "Учётная запись заблокирована", "Пользователь деактивирован.")
            return
        if self.table_name == "media":
            with SessionLocal() as session:
                uses = session.scalar(select(func.count()).select_from(PlaylistItem).where(PlaylistItem.media_id == record.media_id))
            if uses:
                QMessageBox.warning(self, "Медиаматериал используется",
                                    f"Материал входит в {uses} элемент(ов) плейлистов. Удалите его из плейлистов перед удалением.")
                return
        label = getattr(record, "title", None) or getattr(record, "name", None) or getattr(record, "username", None) or TITLES[self.table_name]
        if QMessageBox.question(
            self, "Подтверждение удаления", f"Удалить запись «{label}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            with SessionLocal.begin() as session:
                current = session.get(self.model, getattr(record, self.pk_name))
                session.delete(current)
        except IntegrityError:
            QMessageBox.warning(self, "Запись используется", "Сначала удалите или отвяжите связанные записи.")
            return
        self.refresh()
        QMessageBox.information(self, "Удалено", "Запись удалена.")

    def _double_click(self, *_):
        if self.table_name == "media":
            record = self._selected_record()
            if record:
                MediaPreview(record.file_path, record.media_type, self).exec()
        elif self.editable:
            self.edit_record()

    def preview_selected(self):
        record = self._selected_record()
        if record is None:
            return
        if self.table_name == "media":
            MediaPreview(record.file_path, record.media_type, self).exec()
        elif self.table_name == "playlists":
            name = record.name
            from .demo import FullscreenDemo
            FullscreenDemo(self, playlist_id=record.playlist_id, display_name="Предварительный просмотр",
                           full_screen=False, preview=True).exec()

    def manage_playlist(self):
        playlist = self._selected_record()
        if playlist is not None:
            PlaylistItemsDialog(playlist, self.user, self.role, self).exec()


    def _error(self, title, exc):
        details = str(exc).strip().splitlines()[0] if str(exc).strip() else "Проверьте данные и подключение к базе."
        QMessageBox.critical(self, title, details)


class MediaPreview(QDialog):
    def __init__(self, relative_path: str, media_type: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Просмотр медиаматериала")
        self.resize(900, 600)
        path = PROJECT_ROOT / relative_path
        layout = QVBoxLayout(self)
        path_label = QLabel(f"Файл: {path.resolve()}")
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(path_label)
        if not path.is_file():
            layout.addWidget(QLabel(f"Файл не найден: {path}"))
        elif media_type == "image":
            image = QLabel()
            image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                image.setText("Не удалось открыть изображение.")
            else:
                image.setPixmap(pixmap.scaled(860, 520, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(image)
        else:
            video = QVideoWidget()
            player = QMediaPlayer(self)
            audio = QAudioOutput(self)
            player.setAudioOutput(audio)
            player.setVideoOutput(video)
            player.setSource(QUrl.fromLocalFile(str(path)))
            player.play()
            self.player = player
            self.audio = audio
            layout.addWidget(video, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class PlaylistItemsDialog(QDialog):
    def __init__(self, playlist: Playlist, user: User, role: str, parent=None):
        super().__init__(parent)
        self.playlist_id = playlist.playlist_id
        self.user, self.role = user, role
        self.editable = role == "admin" or playlist.created_by == user.user_id
        self.setWindowTitle(f"Состав плейлиста — {playlist.name}")
        self.resize(820, 520)
        self.items_table = QTableWidget(0, 3)
        self.items_table.setHorizontalHeaderLabels(["Позиция", "Содержимое", "Длительность, сек."])
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.kind = QComboBox()
        self.kind.addItem("Медиаматериал", "media")
        self.kind.addItem("Объявление", "announcement")
        self.kind.addItem("Мероприятие", "event")
        self.content = QComboBox()
        self.duration = QSpinBox()
        self.duration.setRange(1, 3600)
        self.duration.setValue(12)
        self.kind.currentIndexChanged.connect(self._load_content_options)
        self._load_content_options()
        self.add_button = QPushButton("Добавить")
        self.remove_button = QPushButton("Убрать")
        self.up_button = QPushButton("Выше")
        self.down_button = QPushButton("Ниже")
        self.add_button.clicked.connect(self.add_item)
        self.remove_button.clicked.connect(self.remove_item)
        self.up_button.clicked.connect(lambda: self.move_item(-1))
        self.down_button.clicked.connect(lambda: self.move_item(1))
        self.preview_button = QPushButton("Предпросмотр плейлиста")
        self.preview_button.clicked.connect(self.preview_playlist)
        self.add_button.setEnabled(self.editable)
        self.remove_button.setEnabled(self.editable)
        self.up_button.setEnabled(self.editable)
        self.down_button.setEnabled(self.editable)
        entry = QHBoxLayout()
        entry.addWidget(self.kind)
        entry.addWidget(self.content, 1)
        entry.addWidget(QLabel("Показ, сек."))
        entry.addWidget(self.duration)
        entry.addWidget(self.add_button)
        actions = QHBoxLayout()
        actions.addWidget(self.remove_button)
        actions.addWidget(self.up_button)
        actions.addWidget(self.down_button)
        actions.addWidget(self.preview_button)
        actions.addStretch(1)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        layout = QVBoxLayout(self)
        if role != "admin":
            moderation_hint = QLabel("Изменения будут скрыты от демонстрации до проверки и активации плейлиста администратором.")
            moderation_hint.setObjectName("fieldHint")
            moderation_hint.setWordWrap(True)
            layout.addWidget(moderation_hint)
        layout.addLayout(entry)
        layout.addWidget(self.items_table, 1)
        layout.addLayout(actions)
        self.refresh_items()

    def _load_content_options(self, *_):
        self.content.clear()
        mapping = {
            "media": (Media, "media_id", "title", Media.is_active.is_(True)),
            "announcement": (Announcement, "announcement_id", "title", Announcement.is_active.is_(True)),
            "event": (Event, "event_id", "title", Event.status != "cancelled"),
        }
        kind = self.kind.currentData()
        if not kind:
            return
        model, key, label, condition = mapping[kind]
        with SessionLocal() as session:
            query = select(model)
            if condition is not None:
                if self.role != "admin" and kind == "media":
                    condition = or_(condition, Media.added_by == self.user.user_id)
                elif self.role != "admin" and kind == "announcement":
                    condition = or_(condition, Announcement.author_id == self.user.user_id)
                query = query.where(condition)
            for record in session.scalars(query.order_by(getattr(model, label))):
                self.content.addItem(getattr(record, label), (kind, getattr(record, key)))

    def refresh_items(self):
        with SessionLocal() as session:
            items = session.scalars(select(PlaylistItem).where(
                PlaylistItem.playlist_id == self.playlist_id
            ).order_by(PlaylistItem.position)).all()
            self.items_table.setRowCount(len(items))
            for row, item in enumerate(items):
                ref = ("media", item.media_id) if item.media_id else (
                    "announcement", item.announcement_id) if item.announcement_id else ("event", item.event_id)
                model, key, label = {
                    "media": (Media, "media_id", "title"),
                    "announcement": (Announcement, "announcement_id", "title"),
                    "event": (Event, "event_id", "title"),
                }[ref[0]]
                referenced = session.get(model, ref[1])
                title = getattr(referenced, label, None) or "(удалённый материал)"
                if referenced is not None and hasattr(referenced, "is_active") and not referenced.is_active:
                    title += " · черновик"
                kind_label = {"media": "Материал", "announcement": "Объявление", "event": "Мероприятие"}[ref[0]]
                for col, value in enumerate((item.position, f"{kind_label}: {title}", item.display_duration)):
                    cell = QTableWidgetItem(str(value))
                    cell.setData(Qt.ItemDataRole.UserRole, item.item_id)
                    self.items_table.setItem(row, col, cell)
            self.items_table.resizeColumnsToContents()
            self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def preview_playlist(self):
        from .demo import FullscreenDemo
        FullscreenDemo(self, playlist_id=self.playlist_id, display_name="Предварительный просмотр",
                       full_screen=False, preview=True).exec()

    def add_item(self):
        selected = self.content.currentData()
        if not selected:
            QMessageBox.information(self, "Плейлист", "Нет доступных записей выбранного типа.")
            return
        kind, key = selected
        with SessionLocal.begin() as session:
            self._mark_pending(session)
            position = (session.scalar(select(func.max(PlaylistItem.position)).where(
                PlaylistItem.playlist_id == self.playlist_id)) or 0) + 1
            item = PlaylistItem(playlist_id=self.playlist_id, position=position,
                                display_duration=self.duration.value())
            setattr(item, f"{kind}_id", key)
            session.add(item)
        self.refresh_items()

    def remove_item(self):
        row = self.items_table.currentRow()
        if row < 0:
            return
        item_id = self.items_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        with SessionLocal.begin() as session:
            self._mark_pending(session)
            item = session.get(PlaylistItem, item_id)
            if item:
                session.delete(item)
            others = session.scalars(select(PlaylistItem).where(
                PlaylistItem.playlist_id == self.playlist_id,
                PlaylistItem.item_id != item_id,
            ).order_by(PlaylistItem.position)).all()
            for index, other in enumerate(others, 1):
                other.position = index + 10000
            session.flush()
            for index, other in enumerate(others, 1):
                other.position = index
        self.refresh_items()

    def move_item(self, direction: int):
        row = self.items_table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.items_table.rowCount():
            return
        ids = [self.items_table.item(i, 0).data(Qt.ItemDataRole.UserRole)
               for i in range(self.items_table.rowCount())]
        ids[row], ids[target] = ids[target], ids[row]
        with SessionLocal.begin() as session:
            self._mark_pending(session)
            records = [session.get(PlaylistItem, item_id) for item_id in ids]
            for index, record in enumerate(records, 1):
                record.position = index + 10000
            session.flush()
            for index, record in enumerate(records, 1):
                record.position = index
        self.refresh_items()
        self.items_table.selectRow(target)

    def _mark_pending(self, session):
        if self.role != "admin":
            playlist = session.get(Playlist, self.playlist_id)
            if playlist:
                playlist.is_active = False


class DisplayManagementPage(QWidget):
    """Status cards and controls for each configured television/display."""
    def __init__(self, user: User, role: str, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(12)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.addLayout(self.cards_layout)
        self.registry = CrudPage("displays", user, role, self)
        registry_title = QLabel("Управление экранами")
        registry_title.setObjectName("sectionHeading")
        content_layout.addWidget(registry_title)
        content_layout.addWidget(self.registry)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        self.refresh()
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(60_000)
        self.status_timer.timeout.connect(self.refresh)
        self.status_timer.start()

    def refresh(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        with SessionLocal() as session:
            displays = session.scalars(select(Display).order_by(Display.name)).all()
            playlists = session.scalars(select(Playlist).where(Playlist.is_active.is_(True)).order_by(Playlist.name)).all()
            item_counts = {p.playlist_id: session.scalar(select(func.count()).select_from(PlaylistItem).where(
                PlaylistItem.playlist_id == p.playlist_id)) or 0 for p in playlists}
            for index, display in enumerate(displays):
                schedules = session.execute(
                    select(Schedule, Playlist).join(Playlist, Playlist.playlist_id == Schedule.playlist_id)
                    .where(Schedule.display_id == display.display_id, Schedule.is_active.is_(True), Playlist.is_active.is_(True))
                    .order_by(Schedule.start_date, Schedule.start_time)
                ).all()
                current = None
                upcoming = None
                now = datetime.now()
                for schedule, playlist in schedules:
                    if schedule.start_date <= now.date() <= schedule.end_date and schedule.start_time <= now.time() < schedule.end_time:
                        current = (schedule, playlist)
                        break
                    if (schedule.end_date >= now.date() and
                        (schedule.start_date > now.date() or schedule.start_time > now.time())) and upcoming is None:
                        upcoming = (schedule, playlist)
                card = QFrame()
                card.setObjectName("panel")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(16, 14, 16, 14)
                heading = QLabel(display.name)
                heading.setObjectName("sectionHeading")
                location = QLabel(display.location or "Место не указано")
                location.setObjectName("muted")
                if not display.is_active:
                    state, playlist_text, next_text = "Отключено", "—", "—"
                elif display.display_id in self.controller.manual_demos:
                    demo = self.controller.manual_demos[display.display_id]
                    state, playlist_text = "Идёт показ", demo.playlist_name
                    next_text = "Ручной запуск" if demo.manual else "Запуск по расписанию"
                elif current:
                    state, playlist_text, next_text = "Ожидание запуска", current[1].name, f"Окно расписания до {current[0].end_time:%H:%M}"
                elif upcoming:
                    state, playlist_text = "Ожидание", upcoming[1].name
                    next_text = f"{upcoming[0].start_date:%d.%m.%Y} {upcoming[0].start_time:%H:%M}"
                else:
                    state, playlist_text, next_text = "Нет расписания", "—", "—"
                details = QLabel(f"Состояние: {state}\nТекущий плейлист: {playlist_text}\nСледующий показ: {next_text}")
                details.setObjectName("muted")
                details.setWordWrap(True)
                card_layout.addWidget(heading)
                card_layout.addWidget(location)
                card_layout.addWidget(details)
                choose = QComboBox()
                choose.addItem("Выберите плейлист…", None)
                for playlist in playlists:
                    label = playlist.name + (" · пустой" if not item_counts.get(playlist.playlist_id) else "")
                    choose.addItem(label, playlist.playlist_id)
                card_layout.addWidget(choose)
                screen_choice = QComboBox()
                screens = QGuiApplication.screens()
                for screen_index, screen in enumerate(screens):
                    label = "Основной монитор" if screen_index == 0 else f"Монитор {screen_index + 1}"
                    screen_choice.addItem(f"{label} · {screen.name()}", screen_index)
                card_layout.addWidget(screen_choice)
                buttons = QHBoxLayout()
                preview = QPushButton("Предпросмотр")
                run = QPushButton("Запустить показ сейчас")
                stop = QPushButton("Остановить показ")
                open_schedule = QPushButton("Открыть расписание")
                preview.clicked.connect(lambda _=False, d=display.display_id, c=choose, s=screen_choice:
                                         self.controller.preview_display(d, c.currentData(), s.currentData()))
                run.clicked.connect(lambda _=False, d=display.display_id, c=choose, s=screen_choice:
                                    self.controller.start_display(d, c.currentData(), s.currentData()))
                stop.clicked.connect(lambda _=False, d=display.display_id: self.controller.stop_display(d))
                open_schedule.clicked.connect(lambda _=False: self.controller.navigate_to("schedules"))
                buttons.addWidget(preview); buttons.addWidget(run)
                card_layout.addLayout(buttons)
                buttons2 = QHBoxLayout()
                buttons2.addWidget(stop); buttons2.addWidget(open_schedule)
                card_layout.addLayout(buttons2)
                stop.setEnabled(display.display_id in self.controller.manual_demos)
                preview.setEnabled(bool(playlists))
                run.setEnabled(display.is_active and bool(playlists))
                self.cards_layout.addWidget(card, index // 2, index % 2)
