

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from .auth import role_name
from .database import check_connection
from .dialogs import LoginDialog
from .main_window import MainWindow, apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("События кафедры ДонГУ")
    apply_theme(app)
    try:
        check_connection()
    except Exception as exc:
        QMessageBox.critical(
            None, "Нет соединения с базой данных",
            "Не удалось подключиться к PostgreSQL. Проверьте, что Docker Desktop запущен "
            "и контейнер department_events_db имеет состояние healthy.\n\n"
            f"Подробности: {exc}",
        )
        return 1

    login = LoginDialog()
    if login.exec() != LoginDialog.DialogCode.Accepted or login.user is None:
        return 0
    role = role_name(login.user)
    window = MainWindow(login.user, role)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
