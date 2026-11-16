from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QDate, QDateTime, QTime, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDateTimeEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTextEdit, QTimeEdit, QVBoxLayout, QWidget,
)
from sqlalchemy import and_, func, select
from sqlalchemy.sql.sqltypes import Boolean, Date, DateTime, Integer, SmallInteger, Text, Time

from .database import PROJECT_ROOT, SessionLocal
from .models import Display, MODELS, Playlist, PlaylistItem, Role, Schedule
from .theme import set_variant

LABELS = {
    "role_id": "Роль", "role_name": "Название роли", "description": "Описание",
    "user_id": "ID", "username": "Логин", "password_hash": "Хеш пароля",
    "full_name": "ФИО", "created_at": "Создано", "is_active": "Активно",
    "category_id": "Категория", "name": "Название", "source_id": "Источник",
    "source_type": "Тип источника", "url": "Ссылка", "audience_id": "Аудитория",
    "event_id": "Мероприятие", "title": "Заголовок", "event_date": "Дата и время",
    "location": "Место", "status": "Статус", "organizer_id": "Организатор",
    "media_id": "Медиаматериал", "media_type": "Тип файла", "file_path": "Файл",
    "added_by": "Добавил", "announcement_id": "Объявление", "content": "Текст",
    "author_id": "Автор", "start_date": "Дата начала", "end_date": "Дата окончания",
    "playlist_id": "Плейлист", "created_by": "Создал", "item_id": "ID элемента",
    "position": "Позиция", "display_duration": "Длительность, сек.",
    "display_id": "Экран", "schedule_id": "ID расписания", "start_time": "Время начала",
    "end_time": "Время окончания",
    "screen": "Экран",
}
CHOICES = {
    "status": [("Запланировано", "planned"), ("Идёт", "ongoing"),
                ("Завершено", "completed"), ("Отменено", "cancelled")],
    "media_type": [("Изображение", "image"), ("Видео", "video")],
    "source_type": [("Внутренний", "internal"), ("Социальная сеть", "social"), ("Веб-сайт", "website")],
}
ENTITY_NAMES = {
    "events": "мероприятия", "media": "медиаматериала", "announcements": "объявления",
    "categories": "категории", "sources": "источника", "audiences": "аудитории",
    "playlists": "плейлиста", "schedules": "расписания", "displays": "экрана",
    "users": "пользователя", "roles": "роли", "playlist_items": "элемента плейлиста",
}


class GuestDemoSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Запуск демонстрации")
        self.setMinimumWidth(460)
        self.display = QComboBox()
        self.display.addItem("Автоматически по расписанию", None)
        with SessionLocal() as session:
            for screen in session.scalars(select(Display).where(Display.is_active.is_(True)).order_by(Display.name)):
                self.display.addItem(screen.name, screen.display_id)
        self.monitor = QComboBox()
        for index, screen in enumerate(QGuiApplication.screens()):
            label = "Основной монитор" if index == 0 else f"Монитор {index + 1}"
            self.monitor.addItem(f"{label} · {screen.name()}", index)
        form = QFormLayout()
        form.addRow("Экран в расписании", self.display)
        form.addRow("Монитор компьютера", self.monitor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Запустить демонстрацию")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        set_variant(buttons.button(QDialogButtonBox.StandardButton.Ok), "primary")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        heading = QLabel("Выберите экран для показа")
        heading.setObjectName("pageTitle")
        hint = QLabel("Вход не требуется. Демонстрация сама переключится между расписанием и заставкой ожидания.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(hint)
        layout.addLayout(form)
        layout.addWidget(buttons)


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в систему")
        self.setMinimumWidth(440)
        self.user = None
        self.login = QLineEdit()
        self.login.setPlaceholderText("Введите логин")
        self.login.setClearButtonEnabled(True)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Введите пароль")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.buttons = QDialogButtonBox()
        self.enter_button = self.buttons.addButton("Войти", QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.rejected.connect(self.reject)
        self.enter_button.clicked.connect(self._login)
        set_variant(self.enter_button, "primary")
        demo_button = QPushButton("Открыть демонстрацию без входа")
        demo_button.clicked.connect(self._demo)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)
        brand = QLabel("События кафедры")
        brand.setObjectName("heroTitle")
        subtitle = QLabel("Доступ к управлению выдаёт администратор. Для просмотра демонстрации вход не нужен.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("Логин", self.login)
        form.addRow("Пароль", self.password)
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(4)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(self.buttons)
        layout.addWidget(demo_button)
        self.password.returnPressed.connect(self._login)

    def _login(self):
        from .auth import authenticate
        self.user = authenticate(self.login.text(), self.password.text())
        if self.user:
            self.accept()
        else:
            self.error.setText("Неверный логин или пароль либо учётная запись заблокирована.")

    def _demo(self):
        from .demo import FullscreenDemo
        with SessionLocal() as session:
            screens = session.scalars(select(Display).where(Display.is_active.is_(True)).order_by(Display.name)).all()
        monitors = QGuiApplication.screens()
        if len(screens) > 1 or len(monitors) > 1:
            setup = GuestDemoSetupDialog(self)
            if setup.exec() != QDialog.DialogCode.Accepted:
                return
            display_id = setup.display.currentData()
            display_name = setup.display.currentText() if display_id is not None else "Экран кафедры"
            screen_index = setup.monitor.currentData() or 0
        else:
            display_id = screens[0].display_id if screens else None
            display_name = screens[0].name if screens else "Экран кафедры"
            screen_index = 0
        FullscreenDemo(self, display_name=display_name, display_id=display_id,
                       screen_index=screen_index, full_screen=True, standby=True).exec()


class RecordDialog(QDialog):
    """Metadata-driven editor. Foreign keys become readable selection lists."""
    def __init__(self, model, values: dict | None = None, fixed: dict | None = None,
                 parent=None):
        super().__init__(parent)
        self.model = model
        self.values = values or {}
        self.fixed = fixed or {}
        self.widgets: dict[str, QWidget] = {}
        self.selected_file: Path | None = None
        entity = ENTITY_NAMES.get(model.__tablename__, "записи")
        self.setWindowTitle(f"Изменение {entity}" if values else f"Новая запись: {entity}")
        self.setMinimumSize(580, 400)
        self.form = QFormLayout()
        self.form.setSpacing(9)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table = model.__table__
        for column in table.columns:
            name = column.name
            if column.primary_key or name in {"created_at", "password_hash"} or name in self.fixed:
                continue
            control = self._make_control(column)
            self.widgets[name] = control
            label = LABELS.get(name, name)
            if not column.nullable and column.server_default is None:
                label += " *"
            self.form.addRow(label, control)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        set_variant(buttons.button(QDialogButtonBox.StandardButton.Save), "primary")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)
        hint = QLabel("Поля со звёздочкой обязательны.")
        hint.setObjectName("fieldHint")
        layout.addWidget(hint)
        layout.addLayout(self.form)
        layout.addWidget(buttons)

    def _make_control(self, column):
        name, value = column.name, self.values.get(column.name)
        if column.foreign_keys:
            target = next(iter(column.foreign_keys)).column.table
            target_model = MODELS[target.name]
            pk = next(iter(target.primary_key.columns)).name
            display = next(
                field for field in ("name", "full_name", "username", "role_name", "title")
                if field in target.columns
            )
            combo = QComboBox()
            if column.nullable:
                combo.addItem("— нет —", None)
            with SessionLocal() as session:
                rows = session.scalars(select(target_model).order_by(getattr(target_model, display))).all()
                for row in rows:
                    combo.addItem(str(getattr(row, display)), getattr(row, pk))
            if value is not None:
                combo.setCurrentIndex(max(0, combo.findData(value)))
            return combo
        if name == "file_path":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            path = Path(str(value or ""))
            if value and not path.is_absolute():
                path = PROJECT_ROOT / path
            line = QLineEdit(str(path.resolve()) if value else "")
            button = QPushButton("Выбрать…")
            button.clicked.connect(lambda: self._choose_media(line))
            row.addWidget(line, 1)
            row.addWidget(button)
            line.setToolTip(str(path.resolve()) if value else "Полный путь к файлу появится после выбора материала.")
            container.line = line
            return container
        if name in CHOICES:
            combo = QComboBox()
            for label, stored in CHOICES[name]:
                combo.addItem(label, stored)
            if value is not None:
                combo.setCurrentIndex(max(0, combo.findData(value)))
            return combo
        if isinstance(column.type, Boolean):
            box = QCheckBox()
            box.setChecked(bool(value) if value is not None else True)
            return box
        if isinstance(column.type, DateTime):
            edit = QDateTimeEdit()
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("dd.MM.yyyy HH:mm")
            edit.setDateTime(QDateTime(value) if isinstance(value, datetime) else QDateTime.currentDateTime())
            return edit
        if isinstance(column.type, Date):
            edit = QDateEdit()
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("dd.MM.yyyy")
            edit.setDate(QDate(value.year, value.month, value.day) if isinstance(value, date) else QDate.currentDate())
            return edit
        if isinstance(column.type, Time):
            edit = QTimeEdit()
            edit.setDisplayFormat("HH:mm")
            edit.setTime(QTime(value.hour, value.minute) if isinstance(value, time) else QTime.currentTime())
            return edit
        if isinstance(column.type, (Integer, SmallInteger)):
            spin = QSpinBox()
            spin.setRange(0, 10000000)
            spin.setValue(int(value or 0))
            return spin
        if isinstance(column.type, Text) or name in {"description", "content"}:
            edit = QTextEdit()
            edit.setPlainText(str(value or ""))
            edit.setMinimumHeight(80)
            return edit
        edit = QLineEdit(str(value or ""))
        if name == "url":
            edit.setPlaceholderText("https://…")
        return edit

    def _choose_media(self, line: QLineEdit):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите медиаматериал", str(PROJECT_ROOT),
            "Медиафайлы (*.png *.jpg *.jpeg *.mp4 *.avi *.mkv)",
        )
        if file_path:
            self.selected_file = Path(file_path)
            line.setText(file_path)
            media_type = self.widgets.get("media_type")
            if isinstance(media_type, QComboBox):
                detected = "video" if self.selected_file.suffix.lower() in {".mp4", ".avi", ".mkv"} else "image"
                media_type.setCurrentIndex(media_type.findData(detected))

    def _accept(self):
        for name, widget in self.widgets.items():
            if name in {"title", "name", "username", "full_name", "content", "location"}:
                value = widget.toPlainText().strip() if isinstance(widget, QTextEdit) else widget.text().strip()
                if not value:
                    QMessageBox.warning(self, "Проверка данных", f"Заполните поле «{LABELS.get(name,name)}».")
                    return
        if self.selected_file:
            category = "videos" if self.selected_file.suffix.lower() in {".mp4", ".avi", ".mkv"} else "images"
            extension = self.selected_file.suffix.lower()
            directory = PROJECT_ROOT / "media" / category
            directory.mkdir(parents=True, exist_ok=True)
            destination = directory / f"{uuid4().hex}{extension}"
            try:
                destination.write_bytes(self.selected_file.read_bytes())
            except OSError as exc:
                QMessageBox.critical(self, "Файл", f"Не удалось скопировать файл: {exc}")
                return
            line = self.widgets["file_path"].line
            line.setText(destination.relative_to(PROJECT_ROOT).as_posix())

        self.values_out = dict(self.fixed)
        for name, widget in self.widgets.items():
            if name == "file_path":
                raw_path = widget.line.text().strip()
                path = Path(raw_path).expanduser()
                if raw_path and not path.is_absolute():
                    path = PROJECT_ROOT / path
                if raw_path:
                    path = path.resolve()
                    try:
                        value = path.relative_to(PROJECT_ROOT).as_posix()
                    except ValueError:
                        value = str(path)
                else:
                    value = None
            elif isinstance(widget, QComboBox):
                value = widget.currentData()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QDateTimeEdit):
                value = widget.dateTime().toPython()
            elif isinstance(widget, QDateEdit):
                value = widget.date().toPython()
            elif isinstance(widget, QTimeEdit):
                value = widget.time().toPython()
            elif isinstance(widget, QSpinBox):
                value = widget.value()
            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText().strip() or None
            else:
                value = widget.text().strip() or None
            self.values_out[name] = value
        if "file_path" in self.values_out and not self.values_out["file_path"]:
            QMessageBox.warning(self, "Файл", "Выберите файл для медиаматериала.")
            return
        if self.model.__tablename__ == "schedules" and not self._validate_schedule():
            return
        self.accept()

    def _validate_schedule(self) -> bool:
        values = self.values_out
        start_date, end_date = values.get("start_date"), values.get("end_date")
        start_time, end_time = values.get("start_time"), values.get("end_time")
        if end_date < start_date:
            QMessageBox.warning(self, "Проверка расписания", "Дата окончания должна быть не раньше даты начала.")
            return False
        if end_time <= start_time:
            QMessageBox.warning(self, "Проверка расписания", "Время окончания должно быть позже времени начала.")
            return False

        playlist_id = values.get("playlist_id")
        with SessionLocal() as session:
            playlist = session.get(Playlist, playlist_id)
            item_count = session.scalar(select(func.count()).select_from(PlaylistItem).where(
                PlaylistItem.playlist_id == playlist_id
            )) if playlist else 0
            if not playlist or not playlist.is_active or not item_count:
                reason = "неактивен" if playlist and not playlist.is_active else "пуст"
                answer = QMessageBox.question(
                    self, "Плейлист недоступен",
                    f"Выбранный плейлист {reason}. Всё равно сохранить расписание?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return False
            if values.get("is_active", True):
                query = select(Schedule).where(
                    Schedule.display_id == values.get("display_id"),
                    Schedule.is_active.is_(True),
                    Schedule.start_date <= end_date,
                    Schedule.end_date >= start_date,
                    Schedule.start_time < end_time,
                    Schedule.end_time > start_time,
                )
                pk = next(iter(self.model.__table__.primary_key.columns)).name
                current_id = self.values.get(pk)
                if current_id is not None:
                    query = query.where(Schedule.schedule_id != current_id)
                conflict = session.scalar(query.limit(1))
                if conflict:
                    QMessageBox.warning(
                        self, "Пересечение расписаний",
                        f"На выбранном экране уже есть расписание «{conflict.name}» на пересекающиеся даты и время.",
                    )
                    return False
        return True


class AdminUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Новый пользователь")
        self.setMinimumWidth(480)
        self.values_out = {}
        self.full_name = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.confirm = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = QComboBox()
        with SessionLocal() as session:
            for role in session.scalars(select(Role).order_by(Role.role_id)):
                self.role.addItem("Администратор" if role.role_name == "admin" else "Редактор", role.role_id)
        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        form = QFormLayout()
        form.setSpacing(10)
        form.addRow("ФИО", self.full_name)
        form.addRow("Логин", self.username)
        form.addRow("Роль", self.role)
        form.addRow("Пароль (не менее 8 символов)", self.password)
        form.addRow("Повторите пароль", self.confirm)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Создать пользователя")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        set_variant(buttons.button(QDialogButtonBox.StandardButton.Save), "primary")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(14)
        heading = QLabel("Добавить учётную запись")
        heading.setObjectName("pageTitle")
        layout.addWidget(heading)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)

    def _accept(self):
        full_name = self.full_name.text().strip()
        username = self.username.text().strip()
        password = self.password.text()
        if not full_name or not username:
            self.error.setText("Заполните ФИО и логин.")
            return
        if len(password) < 8:
            self.error.setText("Пароль должен содержать не менее 8 символов.")
            return
        if len(password.encode("utf-8")) > 72:
            self.error.setText("Пароль не должен превышать 72 байта.")
            return
        if password != self.confirm.text():
            self.error.setText("Пароли не совпадают.")
            return
        if self.role.currentData() is None:
            self.error.setText("В базе данных не найдены роли.")
            return
        self.values_out = {
            "username": username,
            "full_name": full_name,
            "role_id": self.role.currentData(),
            "password": password,
            "is_active": True,
        }
        self.accept()
