from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QStyle,
)
from sqlalchemy import func, select

from .database import PROJECT_ROOT, SessionLocal, engine
from .demo import FullscreenDemo
from .models import Announcement, Display, Event, Media, Playlist, PlaylistItem, Schedule, User
from .pages import CrudPage, DisplayManagementPage
from .theme import apply_theme, set_variant


def make_panel(title: str, description: str | None = None) -> QFrame:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    heading = QLabel(title)
    heading.setObjectName("sectionHeading")
    layout.addWidget(heading)
    if description:
        note = QLabel(description)
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
    panel.content_layout = layout
    return panel


def make_card(title: str, value: str) -> QFrame:
    box = QFrame()
    box.setObjectName("statCard")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(4)
    label = QLabel(title)
    label.setObjectName("muted")
    number = QLabel(value)
    number.setObjectName("cardValue")
    layout.addWidget(label)
    layout.addWidget(number)
    box.value_label = number
    return box


def prepare_summary_table(table: QTableWidget, headers: list[str]) -> None:
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.verticalHeader().hide()
    table.setMinimumHeight(150)
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    for column in range(1, len(headers)):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)


def fill_table(table: QTableWidget, rows: list[tuple]) -> None:
    table.setRowCount(len(rows))
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setToolTip(str(value))
            table.setItem(row, column, item)
    table.resizeRowsToContents()


class Dashboard(QWidget):
    def __init__(self, user: User, role: str, controller=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.role = role
        self.controller = controller
        self.cards = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        welcome = QFrame()
        welcome.setObjectName("heroCard")
        welcome_layout = QHBoxLayout(welcome)
        welcome_layout.setContentsMargins(20, 16, 20, 16)
        message = QVBoxLayout()
        greeting = QLabel(f"Здравствуйте, {user.full_name}")
        greeting.setObjectName("heroTitle")
        role_label = QLabel("Администратор" if role == "admin" else "Редактор")
        role_label.setObjectName("heroSubtitle")
        message.addWidget(greeting)
        message.addWidget(role_label)
        today = QLabel(datetime.now().strftime("%d.%m.%Y"))
        today.setObjectName("muted")
        welcome_layout.addLayout(message, 1)
        welcome_layout.addWidget(today, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(welcome)

        card_row = QHBoxLayout()
        card_row.setSpacing(12)
        for key, title in (
            ("events", "Мероприятия"),
            ("media", "Медиаматериалы"),
            ("announcements", "Активные объявления"),
            ("playlists", "Плейлисты"),
        ):
            widget = make_card(title, "0")
            card_row.addWidget(widget, 1)
            self.cards[key] = widget.value_label
        root.addLayout(card_row)

        data_row = QHBoxLayout()
        data_row.setSpacing(12)
        events_panel = make_panel("Ближайшие мероприятия", "Предстоящие события кафедры")
        self.events_table = QTableWidget(0, 3)
        prepare_summary_table(self.events_table, ["Мероприятие", "Дата", "Место"])
        events_panel.content_layout.addWidget(self.events_table)
        self.events_empty = QLabel("Ближайших мероприятий пока нет.")
        self.events_empty.setObjectName("muted")
        events_panel.content_layout.addWidget(self.events_empty)

        media_panel = make_panel("Последние медиаматериалы", "Недавно добавленный контент")
        self.media_table = QTableWidget(0, 3)
        prepare_summary_table(self.media_table, ["Материал", "Тип", "Добавлен"])
        media_panel.content_layout.addWidget(self.media_table)
        self.media_empty = QLabel("Медиаматериалы ещё не добавляли.")
        self.media_empty.setObjectName("muted")
        media_panel.content_layout.addWidget(self.media_empty)
        data_row.addWidget(events_panel, 1)
        data_row.addWidget(media_panel, 1)
        root.addLayout(data_row, 1)

        schedule_panel = make_panel("Расписание демонстрации")
        self.schedule_status = QLabel()
        self.schedule_status.setObjectName("statusBadge")
        self.schedule_status.setWordWrap(True)
        schedule_panel.content_layout.addWidget(self.schedule_status)
        schedule_hint = QLabel("Активное расписание показывает доступность по датам и времени; показ запускается отдельно.")
        schedule_hint.setObjectName("muted")
        schedule_hint.setWordWrap(True)
        schedule_panel.content_layout.addWidget(schedule_hint)
        root.addWidget(schedule_panel)
        self.refresh()
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(60_000)
        self.status_timer.timeout.connect(self.refresh)
        self.status_timer.start()

    def refresh(self):
        with SessionLocal() as session:
            counts = {
                "events": session.scalar(select(func.count()).select_from(Event)),
                "media": session.scalar(select(func.count()).select_from(Media)),
                "announcements": session.scalar(
                    select(func.count()).select_from(Announcement).where(
                        Announcement.is_active.is_(True),
                        Announcement.start_date <= func.current_date(),
                        Announcement.end_date >= func.current_date(),
                    )
                ),
                "playlists": session.scalar(select(func.count()).select_from(Playlist).where(
                    Playlist.is_active.is_(True)
                )),
            }
            for key, value in counts.items():
                self.cards[key].setText(str(value or 0))

            events = session.scalars(
                select(Event).where(Event.event_date >= func.now())
                .order_by(Event.event_date).limit(5)
            ).all()
            fill_table(self.events_table, [
                (event.title, event.event_date.strftime("%d.%m.%Y %H:%M"), event.location or "—")
                for event in events
            ])
            self.events_empty.setVisible(not events)
            self.events_table.setVisible(bool(events))

            media = session.scalars(select(Media).order_by(Media.created_at.desc()).limit(5)).all()
            fill_table(self.media_table, [
                (item.title, "Изображение" if item.media_type == "image" else "Видео",
                 item.created_at.strftime("%d.%m.%Y"))
                for item in media
            ])
            self.media_empty.setVisible(not media)
            self.media_table.setVisible(bool(media))

            current = session.execute(
                select(Schedule.display_id, Schedule.name, Playlist.name, Display.name, Schedule.start_time, Schedule.end_time)
                .join(Playlist, Playlist.playlist_id == Schedule.playlist_id)
                .join(Display, Display.display_id == Schedule.display_id)
                .where(
                    Schedule.is_active.is_(True), Playlist.is_active.is_(True), Display.is_active.is_(True),
                    Schedule.start_date <= func.current_date(), Schedule.end_date >= func.current_date(),
                    Schedule.start_time <= func.localtime(), Schedule.end_time > func.localtime(),
                ).order_by(Schedule.start_time.desc()).limit(1)
                ).first()
            upcoming = None if current else session.execute(
                select(Schedule.name, Playlist.name, Display.name, Schedule.start_date, Schedule.start_time)
                .join(Playlist, Playlist.playlist_id == Schedule.playlist_id)
                .join(Display, Display.display_id == Schedule.display_id)
                .where(Schedule.is_active.is_(True), Playlist.is_active.is_(True), Display.is_active.is_(True),
                       Schedule.end_date >= func.current_date(),
                       (Schedule.start_date > func.current_date()) |
                       (Schedule.start_time > func.localtime()))
                .order_by(Schedule.start_date, Schedule.start_time).limit(1)
            ).first()
        manual_demo = next(iter(self.controller.manual_demos.values()), None) if self.controller else None
        if manual_demo:
            mode = "Ручной запуск" if manual_demo.manual else "Запуск по расписанию"
            self.schedule_status.setText(
                f"Идёт показ · плейлист «{manual_demo.playlist_name}» · экран «{manual_demo.display_name}» · {mode}"
            )
            self.schedule_status.setStyleSheet("background:#E8F5EE;color:#16713A;padding:10px 12px;border-radius:8px;font-weight:600")
        elif current:
            display_id, name, playlist, display, start_time, end_time = current
            self.schedule_status.setText(
                f"Ожидание запуска · сейчас доступно расписание плейлиста «{playlist}» "
                f"на экране «{display}» ({start_time:%H:%M}–{end_time:%H:%M})"
            )
            self.schedule_status.setStyleSheet("background:#FFF5DD;color:#946200;padding:10px 12px;border-radius:8px;font-weight:600")
        elif upcoming:
            name, playlist, display, start_date, start_time = upcoming
            self.schedule_status.setText(
                f"Ожидание · плейлист «{playlist}» · экран «{display}» · "
                f"начало {start_date:%d.%m.%Y} в {start_time:%H:%M} · расписание «{name}»"
            )
            self.schedule_status.setStyleSheet("background:#FFF5DD;color:#946200;padding:10px 12px;border-radius:8px;font-weight:600")
        else:
            self.schedule_status.setText("Нет расписания · добавьте экран, плейлист и настройте время показа.")
            self.schedule_status.setStyleSheet("background:#EEF0F5;color:#555B6E;padding:10px 12px;border-radius:8px;font-weight:600")


class StatisticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tables = {}
        self.cards = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)
        card_row = QHBoxLayout()
        for key, title in (
            ("events", "Мероприятия"), ("media", "Медиаматериалы"),
            ("announcements", "Активные объявления"), ("playlists", "Активные плейлисты"),
        ):
            widget = make_card(title, "0")
            self.cards[key] = widget.value_label
            card_row.addWidget(widget, 1)
        root.addLayout(card_row)

        grid = QGridLayout()
        grid.setSpacing(12)
        for index, (key, title, headers) in enumerate((
            ("summary", "Медиаматериалы по типам", ["Тип", "Количество"]),
            ("category_events", "Мероприятия по категориям", ["Категория", "Количество"]),
            ("sources", "Использование источников", ["Источник", "Материалов"]),
            ("authors", "Материалы по авторам", ["Пользователь", "Материалов"]),
        )):
            panel = make_panel(title)
            table = QTableWidget(0, 2)
            prepare_summary_table(table, headers)
            table.setMinimumHeight(200)
            panel.content_layout.addWidget(table)
            self.tables[key] = table
            grid.addWidget(panel, index // 2, index % 2)
        root.addLayout(grid, 1)
        self.refresh()

    @staticmethod
    def _fill(table, rows):
        fill_table(table, rows)

    def refresh(self):
        from .models import Category, Source
        with SessionLocal() as session:
            metrics = {
                "events": session.scalar(select(func.count()).select_from(Event)),
                "media": session.scalar(select(func.count()).select_from(Media)),
                "announcements": session.scalar(select(func.count()).select_from(Announcement).where(
                    Announcement.is_active.is_(True), Announcement.start_date <= func.current_date(),
                    Announcement.end_date >= func.current_date())),
                "playlists": session.scalar(select(func.count()).select_from(Playlist).where(Playlist.is_active.is_(True))),
            }
            for key, value in metrics.items():
                self.cards[key].setText(str(value or 0))
            summary = session.execute(
                select(Media.media_type, func.count()).group_by(Media.media_type).order_by(Media.media_type)
            ).all()
            categories = session.execute(
                select(Category.name, func.count(Event.event_id)).outerjoin(
                    Event, Event.category_id == Category.category_id
                ).group_by(Category.category_id, Category.name)
                .order_by(func.count(Event.event_id).desc())
            ).all()
            sources = session.execute(
                select(Source.name, func.count(Media.media_id)).outerjoin(
                    Media, Media.source_id == Source.source_id
                ).group_by(Source.source_id, Source.name)
                .order_by(func.count(Media.media_id).desc()).limit(10)
            ).all()
            authors = session.execute(
                select(User.full_name, func.count(Media.media_id)).outerjoin(
                    Media, Media.added_by == User.user_id
                ).group_by(User.user_id, User.full_name)
                .order_by(func.count(Media.media_id).desc()).limit(10)
            ).all()
        self._fill(self.tables["summary"], summary)
        self._fill(self.tables["category_events"], categories)
        self._fill(self.tables["sources"], sources)
        self._fill(self.tables["authors"], authors)


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = QLabel()
        self.status.setWordWrap(True)
        panel = make_panel("Подключение к базе данных", "Состояние текущего подключения PostgreSQL")
        panel.content_layout.addWidget(self.status)
        backup_panel = make_panel("Резервное копирование", "Сохранить SQL-копию базы в папку backups проекта.")
        backup = QPushButton("Создать резервную копию")
        backup.clicked.connect(self.backup)
        backup_panel.content_layout.addWidget(backup)
        set_variant(backup, "primary")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(panel)
        layout.addWidget(backup_panel)
        layout.addStretch(1)
        self.refresh()

    def refresh(self):
        try:
            with engine.connect() as connection:
                version = connection.exec_driver_sql("SELECT version()").scalar_one()
                zone = connection.exec_driver_sql("SHOW TIME ZONE").scalar_one()
            self.status.setText(
                f"Подключение установлено\n{version}\nЧасовой пояс: {zone}\n"
                f"Сервер: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
            )
        except Exception as exc:
            self.status.setText(f"Не удалось подключиться к базе данных. Подробности: {exc}")

    def backup(self):
        local = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe"
        docker = shutil.which("docker") or (
            str(local) if local.is_file() else r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"
        )
        if not Path(docker).is_file() and not shutil.which(docker):
            QMessageBox.critical(self, "Резервная копия", "Docker CLI не найден. Установите Docker Desktop.")
            return
        directory = PROJECT_ROOT / "backups"
        directory.mkdir(exist_ok=True)
        filename = directory / f"department_events_{datetime.now():%Y%m%d_%H%M%S}.sql"
        answer = QMessageBox.question(
            self, "Создать резервную копию",
            f"Сохранить текущую базу в файл {filename.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        command = [docker, "compose", "exec", "-T", "postgres", "pg_dump", "-U",
                   os.getenv("DB_USER", "department_user"), os.getenv("DB_NAME", "department_events")]
        try:
            with filename.open("wb") as output:
                result = subprocess.run(command, cwd=PROJECT_ROOT, stdout=output,
                                        stderr=subprocess.PIPE, check=False, timeout=120)
            if result.returncode:
                filename.unlink(missing_ok=True)
                raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
            QMessageBox.information(self, "Резервная копия создана", f"Файл сохранён: {filename}")
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка резервного копирования", str(exc))


class MainWindow(QMainWindow):
    def __init__(self, user: User, role: str):
        super().__init__()
        self.user, self.role = user, role
        self.setWindowTitle("События кафедры ДонГУ")
        self.resize(1280, 740)
        self.setMinimumSize(940, 600)

        container = QWidget()
        root = QHBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFixedWidth(235)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 18, 10, 14)
        brand = QLabel("События кафедры")
        brand.setObjectName("brand")
        caption = QLabel("Управление контентом")
        caption.setObjectName("brandCaption")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(caption)
        sidebar_layout.addSpacing(16)
        sidebar_layout.addWidget(self.navigation, 1)
        account = QLabel(f"{user.full_name}\n{'Администратор' if role == 'admin' else 'Редактор'}")
        account.setObjectName("muted")
        account.setWordWrap(True)
        account.setContentsMargins(10, 10, 8, 4)
        sidebar_layout.addWidget(account)
        root.addWidget(sidebar)

        self.pages = {}
        self.descriptions = {}
        self.manual_demos = {}
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(26, 22, 26, 16)
        main_layout.setSpacing(16)
        top = QHBoxLayout()
        title_box = QVBoxLayout()
        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_description = QLabel()
        self.page_description.setObjectName("pageDescription")
        self.page_description.setWordWrap(True)
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_description)
        top.addLayout(title_box, 1)
        self.user_badge = QLabel(f"{user.full_name} · {'Администратор' if role == 'admin' else 'Редактор'}")
        self.user_badge.setObjectName("muted")
        top.addWidget(self.user_badge, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(top)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)
        root.addWidget(main_area, 1)
        self.setCentralWidget(container)

        self._add_group("ГЛАВНАЯ")
        self._add_page("Главная", "Главная панель", "Краткий обзор контента и текущего показа.", Dashboard(user, role, self))
        self._add_group("КОНТЕНТ")
        self._add_page("Мероприятия", "events", "Мероприятия кафедры: сроки, место, категория и ответственный.", CrudPage("events", user, role))
        self._add_page("Медиаматериалы", "media", "Изображения и видео, связанные с событиями и категориями.", CrudPage("media", user, role))
        self._add_page("Объявления", "announcements", "Текстовые объявления, сроки публикации и целевая аудитория.", CrudPage("announcements", user, role))
        self._add_group("ОРГАНИЗАЦИЯ")
        self._add_page("Категории", "categories", "Категории мероприятий и материалов.", CrudPage("categories", user, role))
        self._add_page("Источники", "sources", "Источники и ссылки, откуда получены материалы.", CrudPage("sources", user, role))
        self._add_page("Аудитории", "audiences", "Группы пользователей, которым адресованы объявления.", CrudPage("audiences", user, role))
        self._add_group("ДЕМОНСТРАЦИЯ")
        self._add_page("Плейлисты", "playlists", "Последовательности материалов для телевизионного показа.", CrudPage("playlists", user, role))
        self._add_page("Расписание", "schedules", "Периоды и время показа плейлистов на экранах.", CrudPage("schedules", user, role, controller=self))
        self._add_page("Экраны", "displays", "Состояние экранов, запуск показа и расписание.", DisplayManagementPage(user, role, self))
        self._add_group("АНАЛИТИКА")
        self._add_page("Статистика", "stats", "Сводные показатели по мероприятиям и медиаконтенту.", StatisticsPage())
        if role == "admin":
            self._add_group("УПРАВЛЕНИЕ")
            self._add_page("Пользователи", "users", "Учётные записи, роли и состояние доступа.", CrudPage("users", user, role))
            self._add_page("Настройки", "settings", "Подключение к PostgreSQL и резервное копирование.", SettingsPage())
        self._add_group("ПОКАЗ")
        demo_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        demo_item = QListWidgetItem(demo_icon, "Полноэкранная демонстрация")
        demo_item.setData(Qt.ItemDataRole.UserRole, "__demo__")
        self.navigation.addItem(demo_item)
        self.navigation.currentRowChanged.connect(self._navigate)
        self.navigation.setCurrentRow(1)
        self.statusBar().showMessage(f"Выполнен вход: {user.full_name}")

    def _add_group(self, title: str):
        item = QListWidgetItem(title)
        item.setData(Qt.ItemDataRole.UserRole, None)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setForeground(QColor("#858A9B"))
        font = QFont(self.font())
        font.setPointSize(9)
        font.setBold(True)
        item.setFont(font)
        self.navigation.addItem(item)

    def _add_page(self, nav_title: str, key: str, description: str, widget: QWidget):
        icon_names = {
            "Главная панель": "SP_ComputerIcon",
            "events": "SP_FileDialogDetailedView",
            "media": "SP_FileIcon",
            "announcements": "SP_MessageBoxInformation",
            "categories": "SP_DirIcon",
            "sources": "SP_DriveNetIcon",
            "audiences": "SP_DirHomeIcon",
            "playlists": "SP_MediaPlay",
            "schedules": "SP_BrowserReload",
            "displays": "SP_DesktopIcon",
            "stats": "SP_FileDialogInfoView",
            "users": "SP_DialogYesButton",
            "settings": "SP_FileDialogContentsView",
        }
        icon_name = icon_names.get(key, "SP_FileIcon")
        icon = self.style().standardIcon(getattr(QStyle.StandardPixmap, icon_name,
                                                 QStyle.StandardPixmap.SP_FileIcon))
        item = QListWidgetItem(icon, nav_title)
        item.setData(Qt.ItemDataRole.UserRole, key)
        self.navigation.addItem(item)
        self.stack.addWidget(widget)
        self.pages[key] = widget
        self.descriptions[key] = (nav_title, description)

    def _navigate(self, index: int):
        if index < 0:
            return
        item = self.navigation.item(index)
        if item is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if key == "__demo__":
            self.start_scheduled_demo()
            return
        page = self.pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        title, description = self.descriptions[key]
        self.page_title.setText(title)
        self.page_description.setText(description)
        if hasattr(page, "refresh"):
            page.refresh()

    def navigate_to(self, key: str):
        for index in range(self.navigation.count()):
            if self.navigation.item(index).data(Qt.ItemDataRole.UserRole) == key:
                self.navigation.setCurrentRow(index)
                return

    def preview_display(self, display_id: int, playlist_id: int | None, screen_index: int = 0):
        with SessionLocal() as session:
            display = session.get(Display, display_id)
            if playlist_id is None:
                scheduled = session.execute(
                    select(Schedule.playlist_id).where(
                        Schedule.display_id == display_id, Schedule.is_active.is_(True),
                        Schedule.end_date >= func.current_date()
                    ).order_by(Schedule.start_date, Schedule.start_time).limit(1)
                ).first()
                playlist_id = scheduled[0] if scheduled else None
            if playlist_id is None:
                QMessageBox.information(self, "Предпросмотр", "Для экрана пока не выбран плейлист.")
                return
            playlist = session.get(Playlist, playlist_id)
            count = session.scalar(select(func.count()).select_from(PlaylistItem).where(
                PlaylistItem.playlist_id == playlist_id
            )) or 0
            display_name = display.name if display else "Экран"
            playlist_name = playlist.name if playlist else "Плейлист"
        if not count and QMessageBox.question(
            self, "Пустой плейлист", f"Плейлист «{playlist_name}» пуст. Открыть предпросмотр?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        FullscreenDemo(self, playlist_id=playlist_id, display_name=display_name,
                       screen_index=screen_index, full_screen=False, preview=True).exec()

    def start_display(self, display_id: int, playlist_id: int | None, screen_index: int = 0):
        if playlist_id is None:
            QMessageBox.information(self, "Запуск показа", "Выберите плейлист для ручного запуска.")
            return
        from .models import PlaylistItem
        with SessionLocal() as session:
            display = session.get(Display, display_id)
            playlist = session.get(Playlist, playlist_id)
            if not display or not display.is_active:
                QMessageBox.warning(self, "Экран недоступен", "Выбранный экран отключён или удалён.")
                return
            if not playlist or not playlist.is_active:
                QMessageBox.warning(self, "Плейлист недоступен", "Выберите активный плейлист.")
                return
            count = session.scalar(select(func.count()).select_from(PlaylistItem).where(
                PlaylistItem.playlist_id == playlist_id
            )) or 0
            display_name, playlist_name = display.name, playlist.name
        if not count and QMessageBox.question(
            self, "Пустой плейлист", f"Плейлист «{playlist_name}» пуст. Запустить показ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self.stop_display(display_id)
        demo = FullscreenDemo(self, playlist_id=playlist_id, display_name=display_name,
                              screen_index=screen_index, full_screen=True)
        demo.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.manual_demos[display_id] = demo
        demo.finished.connect(lambda _result, did=display_id: self._demo_closed(did))
        demo.showFullScreen()
        page = self.pages.get("displays")
        if page:
            page.refresh()

    def start_scheduled_demo(self):
        with SessionLocal() as session:
            active = session.execute(
                select(Schedule.display_id, Display.name).join(Display, Display.display_id == Schedule.display_id)
                .join(Playlist, Playlist.playlist_id == Schedule.playlist_id)
                .where(Schedule.is_active.is_(True), Display.is_active.is_(True), Playlist.is_active.is_(True),
                       Schedule.start_date <= func.current_date(), Schedule.end_date >= func.current_date(),
                       Schedule.start_time <= func.localtime(), Schedule.end_time > func.localtime())
                .order_by(Schedule.start_time.desc()).limit(1)
            ).first()
        if active:
            display_id, display_name = active
            self.start_scheduled_display(display_id, display_name)
        else:
            FullscreenDemo(self).exec()

    def start_scheduled_display(self, display_id: int, display_name: str):
        self.stop_display(display_id)
        demo = FullscreenDemo(self, display_name=display_name, display_id=display_id, full_screen=True)
        demo.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.manual_demos[display_id] = demo
        demo.finished.connect(lambda _result, did=display_id: self._demo_closed(did))
        demo.showFullScreen()

    def stop_display(self, display_id: int):
        demo = self.manual_demos.get(display_id)
        if demo:
            demo.close()

    def _demo_closed(self, display_id: int):
        self.manual_demos.pop(display_id, None)
        page = self.pages.get("displays")
        if page:
            page.refresh()


__all__ = ["MainWindow", "apply_theme"]
