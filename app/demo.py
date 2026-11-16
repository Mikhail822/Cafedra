from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QUrl, QSize
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QSizePolicy
from sqlalchemy import func, select

from .database import PROJECT_ROOT, SessionLocal
from .models import Announcement, Audience, Category, Display, Event, Media, Playlist, PlaylistItem, Schedule


class FitImageLabel(QLabel):
    """Keep the entire source image visible and scale it with the available stage size."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def minimumSizeHint(self):
        return QSize(1, 1)

    def set_source_pixmap(self, pixmap: QPixmap):
        self.source_pixmap = pixmap
        self._scale_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale_pixmap()

    def _scale_pixmap(self):
        if not self.source_pixmap.isNull() and self.width() > 0 and self.height() > 0:
            fitted = self.source_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            super().setPixmap(fitted)


class FullscreenDemo(QDialog):
    def __init__(self, parent=None, playlist_id=None, display_name=None, screen_index=0,
                 full_screen=True, preview=False, display_id=None, standby=True):
        super().__init__(parent)
        self.preview = preview
        self.full_screen = full_screen
        self.manual = playlist_id is not None
        self.standby = standby and playlist_id is None and not preview
        self.display_name = display_name or "Экран"
        self.display_id = display_id
        self.requested_display_id = display_id
        self.active_schedule_id = None
        self.schedule_error = False
        self.setWindowTitle("Предпросмотр плейлиста" if preview else "Демонстрация контента")
        self.setStyleSheet("""
            QDialog { background:#EAF6FB; }
            QWidget#demoCanvas {
                border:1px solid rgba(255,255,255,210);
                border-radius:22px;
                background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #DDF3FC, stop:0.48 #9EDCF0, stop:1 #A9EBDD);
            }
            QWidget#glassCard {
                background:rgba(255,255,255,224);
                border:1px solid rgba(255,255,255,245);
                border-radius:22px;
            }
            QWidget#photoSlide { background:transparent; }
            QLabel#photoFrame {
                background:rgba(255,255,255,110);
                border:2px solid rgba(255,255,255,220);
                border-radius:18px;
            }
            QLabel#demoStatus { color:#365B70; font-size:14px; font-weight:600; }
            QLabel#demoHint { color:#668393; font-size:13px; }
            QLabel#slideEyebrow { color:#3784A7; font-size:16px; font-weight:700; letter-spacing:2px; }
            QLabel#slideTitle { color:#263F50; font-size:42px; font-weight:700; }
            QLabel#slideBody { color:#3F5969; font-size:25px; }
            QLabel#slideMeta { color:#43728A; font-size:19px; font-weight:600; }
        """)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(16, 14, 16, 10)
        self.root.setSpacing(8)
        self.canvas = QWidget()
        self.canvas.setObjectName("demoCanvas")
        self.stage = QVBoxLayout(self.canvas)
        self.stage.setContentsMargins(28, 24, 28, 20)
        self.stage.setSpacing(12)
        self.root.addWidget(self.canvas, 1)
        footer = QHBoxLayout()
        self.status = QLabel("Поиск активного расписания…")
        self.status.setObjectName("demoStatus")
        self.status.setWordWrap(True)
        self.status.setMinimumWidth(0)
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        hint = QLabel("Esc — завершить показ")
        hint.setObjectName("demoHint")
        hint.setWordWrap(True)
        hint.setMinimumWidth(0)
        hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        footer.setSpacing(8)
        footer.addWidget(self.status, 1)
        footer.addWidget(hint)
        self.root.addLayout(footer)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_item)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.mediaStatusChanged.connect(self._media_status_changed)
        self.player.errorOccurred.connect(self._media_error)
        self.items = []
        self.index = 0
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.setInterval(5_000)
        self.scheduler_timer.timeout.connect(self._check_schedule)
        self.idle_refresh_timer = QTimer(self)
        self.idle_refresh_timer.setInterval(60_000)
        self.idle_refresh_timer.timeout.connect(self._refresh_idle)
        self._load_initial(playlist_id)
        if self.standby:
            self.scheduler_timer.start()
        screens = QGuiApplication.screens()
        target = screens[screen_index] if 0 <= screen_index < len(screens) else QGuiApplication.primaryScreen()
        if target:
            self.setGeometry(target.geometry())
        if full_screen:
            self.showFullScreen()
            self.setCursor(Qt.CursorShape.BlankCursor)
        else:
            self.resize(1000, 650)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _active_schedule(self):
        with SessionLocal() as session:
            query = (
                select(Schedule.schedule_id, Schedule.name, Schedule.playlist_id, Playlist.name,
                       Schedule.display_id, Display.name, Schedule.end_time)
                .join(Playlist, Playlist.playlist_id == Schedule.playlist_id)
                .join(Display, Display.display_id == Schedule.display_id)
                .where(Schedule.is_active.is_(True), Playlist.is_active.is_(True), Display.is_active.is_(True),
                       Schedule.start_date <= func.current_date(), Schedule.end_date >= func.current_date(),
                       Schedule.start_time <= func.localtime(), Schedule.end_time > func.localtime())
            )
            if self.requested_display_id is not None:
                query = query.where(Schedule.display_id == self.requested_display_id)
            return session.execute(query.order_by(Schedule.start_time.desc()).limit(1)).first()

    def _playlist_items(self, playlist_id: int):
        items_out = []
        with SessionLocal() as session:
            playlist_items = session.scalars(
                select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id)
                .order_by(PlaylistItem.position)
            ).all()
            today = session.scalar(select(func.current_date()))
            for item in playlist_items:
                if item.media_id:
                    media = session.get(Media, item.media_id)
                    if media and media.is_active:
                        items_out.append((item.display_duration, "media", media.title,
                                          media.media_type, media.file_path, media.description or ""))
                elif item.announcement_id:
                    announcement = session.get(Announcement, item.announcement_id)
                    if (announcement and announcement.is_active and announcement.start_date <= today
                            and announcement.end_date >= today):
                        audience = session.get(Audience, announcement.audience_id)
                        announcement_meta = f"Действует до {announcement.end_date:%d.%m.%Y}"
                        if audience:
                            announcement_meta += f"  •  {audience.name}"
                        items_out.append((item.display_duration, "text", announcement.title,
                                          "Объявление", announcement.content, announcement_meta))
                elif item.event_id:
                    event = session.get(Event, item.event_id)
                    if event and event.status != "cancelled":
                        attached_media = session.scalar(
                            select(Media).where(Media.event_id == event.event_id, Media.is_active.is_(True))
                            .order_by(Media.media_id.desc()).limit(1)
                        )
                        category = session.get(Category, event.category_id)
                        event_meta = f"{event.event_date:%d.%m.%Y · %H:%M}  •  {event.location}"
                        if category:
                            event_meta += f"  •  {category.name}"
                        if attached_media:
                            items_out.append((item.display_duration, "media", attached_media.title,
                                              attached_media.media_type, attached_media.file_path,
                                              event_meta))
                        else:
                            items_out.append((item.display_duration, "text", event.title,
                                              "Мероприятие", event.description or "",
                                              event_meta))
        return items_out

    def _load_initial(self, requested_playlist_id=None):
        if requested_playlist_id is not None:
            with SessionLocal() as session:
                playlist = session.get(Playlist, requested_playlist_id)
                playlist_name = playlist.name if playlist else "Плейлист"
            self.playlist_name = playlist_name
            self.status.setText(f"{'Предпросмотр' if self.preview else 'Ручной запуск'}: {playlist_name} · {self.display_name}")
            self.items = self._playlist_items(requested_playlist_id)
            self.index = 0
            if self.items:
                self.next_item()
            else:
                self._show_message("Плейлист пуст", "Добавьте медиаматериалы, объявления или мероприятия, затем запустите предпросмотр.")
            return
        self._check_schedule(initial=True)

    def _activate_schedule(self, active):
        schedule_id, schedule_name, playlist_id, playlist_name, display_id, display_name, end_time = active
        self.schedule_error = False
        self.active_schedule_id = schedule_id
        self.display_name = display_name
        self.playlist_name = playlist_name
        self.items = self._playlist_items(playlist_id)
        self.index = 0
        self.idle_refresh_timer.stop()
        self.status.setText(f"Идёт показ: {playlist_name} · {display_name} · до {end_time:%H:%M}")
        if self.items:
            self.next_item()
        else:
            self._show_message("Плейлист пуст", f"Расписание «{schedule_name}» активно, но в плейлисте нет доступных материалов.")

    def _check_schedule(self, initial=False):
        if not self.standby:
            return
        try:
            active = self._active_schedule()
        except Exception:
            self.schedule_error = True
            self.status.setText("Расписание временно недоступно")
            self._show_message("Информация кафедры",
                               "Не удалось обновить расписание. Проверьте подключение к сети кафедры.")
            return
        if active:
            if active[0] != self.active_schedule_id:
                self._activate_schedule(active)
            return
        if self.active_schedule_id is not None or initial or self.schedule_error:
            self.schedule_error = False
            self.active_schedule_id = None
            self.items = []
            self.index = 0
            self._show_idle()

    def _next_schedule(self):
        now = datetime.now()
        candidates = []
        with SessionLocal() as session:
            query = (
                select(Schedule.name, Playlist.name, Display.name, Schedule.start_date,
                       Schedule.end_date, Schedule.start_time, Schedule.end_time)
                .join(Playlist, Playlist.playlist_id == Schedule.playlist_id)
                .join(Display, Display.display_id == Schedule.display_id)
                .where(Schedule.is_active.is_(True), Playlist.is_active.is_(True), Display.is_active.is_(True),
                       Schedule.end_date >= now.date())
            )
            if self.requested_display_id is not None:
                query = query.where(Schedule.display_id == self.requested_display_id)
            for row in session.execute(query):
                name, playlist, display, start_date, end_date, start_time, end_time = row
                if start_date > now.date():
                    occurrence = start_date
                elif now.time() < start_time:
                    occurrence = now.date()
                elif now.time() >= end_time and end_date > now.date():
                    from datetime import timedelta
                    occurrence = now.date() + timedelta(days=1)
                else:
                    continue
                candidates.append((occurrence, start_time, name, playlist, display))
        return min(candidates, default=None, key=lambda value: (value[0], value[1]))

    def _idle_information(self):
        now = datetime.now().date()
        with SessionLocal() as session:
            announcement = session.scalar(
                select(Announcement).where(
                    Announcement.is_active.is_(True), Announcement.start_date <= now,
                    Announcement.end_date >= now,
                ).order_by(Announcement.start_date.desc(), Announcement.announcement_id.desc()).limit(1)
            )
            if announcement:
                return ("Новости кафедры", announcement.title, announcement.content)
            event = session.scalar(
                select(Event).where(Event.event_date >= func.now(), Event.status != "cancelled")
                .order_by(Event.event_date).limit(1)
            )
            if event:
                return ("Ближайшее мероприятие", event.title,
                        f"{event.event_date:%d.%m.%Y %H:%M} · {event.location}")
        return ("Информация кафедры", "Следите за обновлениями",
                "Новые объявления и расписание демонстрации появятся на этом экране.")

    def _show_idle(self):
        self._clear_stage()
        self.idle_refresh_timer.start()
        content = QWidget()
        content.setStyleSheet("background:transparent")
        layout = QVBoxLayout(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(48, 28, 48, 28)
        layout.setSpacing(18)
        label = QLabel("ЭКРАН КАФЕДРЫ  ·  РЕЖИМ ОЖИДАНИЯ")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName("slideEyebrow")
        layout.addWidget(label)
        next_schedule = self._next_schedule()
        if next_schedule:
            day, start_time, schedule_name, playlist_name, display_name = next_schedule
            self.status.setText(f"Ожидание · следующий показ {day:%d.%m.%Y} в {start_time:%H:%M} · {display_name}")
            heading = QLabel("Следующий показ")
            heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
            heading.setObjectName("slideTitle")
            details = QLabel(f"{day:%d.%m.%Y} · {start_time:%H:%M}\n{playlist_name} · {display_name}")
            details.setAlignment(Qt.AlignmentFlag.AlignCenter)
            details.setObjectName("slideMeta")
            details.setWordWrap(True)
        else:
            self.status.setText(f"Ожидание · {self.display_name} · расписание пока не опубликовано")
            heading = QLabel("Расписание пока не опубликовано")
            heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
            heading.setObjectName("slideTitle")
            details = QLabel("На экране появятся новые мероприятия и объявления кафедры.")
            details.setAlignment(Qt.AlignmentFlag.AlignCenter)
            details.setObjectName("slideBody")
            details.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(details)
        info_heading, info_title, info_body = self._idle_information()
        card = QWidget()
        card.setObjectName("glassCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 20, 28, 20)
        card_layout.setSpacing(8)
        topic = QLabel(info_heading)
        topic.setObjectName("slideEyebrow")
        title = QLabel(info_title)
        title.setWordWrap(True)
        title.setObjectName("slideTitle")
        body = QLabel(info_body[:700] + ("…" if len(info_body) > 700 else ""))
        body.setWordWrap(True)
        body.setObjectName("slideBody")
        card_layout.addWidget(topic)
        card_layout.addWidget(title)
        card_layout.addWidget(body)
        layout.addWidget(card)
        note = QLabel("Показ начнётся автоматически по расписанию")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet("font-size:16px;color:#668393")
        layout.addWidget(note)
        self.stage.addWidget(content, 1)

    def _refresh_idle(self):
        if self.standby and self.active_schedule_id is None:
            self._show_idle()

    def _clear_stage(self):
        self.timer.stop()
        self.player.stop()
        self.player.setSource(QUrl())
        while self.stage.count():
            child = self.stage.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _show_message(self, title: str, body: str):
        self._clear_stage()
        card = QWidget()
        card.setObjectName("glassCard")
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(42, 36, 42, 36)
        layout.setSpacing(16)
        heading = QLabel(title)
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setObjectName("slideTitle")
        text = QLabel(body)
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setObjectName("slideBody")
        layout.addWidget(heading)
        layout.addWidget(text)
        self.stage.addWidget(card)

    def next_item(self):
        if not self.items:
            return
        self._clear_stage()
        duration, kind, title, media_type, payload, extra = self.items[self.index % len(self.items)]
        self.index += 1
        path = PROJECT_ROOT / payload if kind == "media" else None
        if kind == "media" and path and path.is_file() and media_type == "image":
            slide = QWidget()
            slide.setObjectName("photoSlide")
            layout = QVBoxLayout(slide)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(10)
            image = FitImageLabel()
            image.setObjectName("photoFrame")
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self._show_message("Изображение недоступно",
                                   "Этот материал временно недоступен. Переходим к следующему слайду.")
            else:
                image.set_source_pixmap(pixmap)
                layout.addWidget(image, 1)
                caption = QWidget()
                caption.setObjectName("glassCard")
                caption_layout = QVBoxLayout(caption)
                caption_layout.setContentsMargins(22, 12, 22, 12)
                caption_layout.setSpacing(3)
                caption_title = QLabel(title)
                caption_title.setObjectName("slideTitle")
                caption_title.setStyleSheet("font-size:24px")
                caption_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                caption_layout.addWidget(caption_title)
                if extra:
                    caption_meta = QLabel(extra)
                    caption_meta.setObjectName("slideMeta")
                    caption_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    caption_meta.setWordWrap(True)
                    caption_layout.addWidget(caption_meta)
                layout.addWidget(caption, 0)
                self.stage.addWidget(slide, 1)
        elif kind == "media" and path and path.is_file() and media_type == "video":
            slide = QWidget()
            slide.setObjectName("photoSlide")
            layout = QVBoxLayout(slide)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(10)
            video = QVideoWidget()
            self.player.setVideoOutput(video)
            self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))
            self.timer.stop()
            self.player.play()
            layout.addWidget(video, 1)
            caption = QLabel(title)
            caption.setObjectName("slideMeta")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(caption)
            self.stage.addWidget(slide, 1)
        elif kind == "text":
            card = QWidget()
            card.setObjectName("glassCard")
            layout = QVBoxLayout(card)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(52, 42, 52, 42)
            layout.setSpacing(18)
            eyebrow = QLabel(media_type.upper())
            eyebrow.setObjectName("slideEyebrow")
            eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            heading = QLabel(title)
            heading.setObjectName("slideTitle")
            heading.setWordWrap(True)
            heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text = QLabel(payload[:800] + ("…" if len(payload) > 800 else ""))
            text.setObjectName("slideBody")
            text.setWordWrap(True)
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            extra_label = QLabel(extra)
            extra_label.setObjectName("slideMeta")
            extra_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            extra_label.setWordWrap(True)
            layout.addWidget(eyebrow)
            layout.addWidget(heading)
            layout.addWidget(text)
            layout.addWidget(extra_label)
            self.stage.addWidget(card, 1)
        else:
            self._show_message("Материал временно недоступен",
                               "Продолжаем показ и переходим к следующему слайду.")
        if kind != "media" or media_type != "video" or not path or not path.is_file():
            self.timer.start(max(1, duration) * 1000)

    def _media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next_item()

    def _media_error(self, error, message):
        if error == QMediaPlayer.Error.NoError:
            return
        self._show_message("Видео временно недоступно",
                           "Продолжаем показ и переходим к следующему слайду.")
        self.timer.start(3000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.unsetCursor()
        self.player.stop()
        super().closeEvent(event)
