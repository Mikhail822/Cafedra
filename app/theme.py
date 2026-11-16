from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget


PALETTE = {
    "background": "#F2F8FC",
    "surface": "#FFFFFF",
    "text": "#263746",
    "muted": "#718493",
    "accent": "#4B9ED8",
    "accent_hover": "#3788C3",
    "accent_soft": "#DDF3FC",
    "teal": "#65D6C5",
    "border": "#DCEAF1",
    "success": "#36A982",
    "warning": "#E6A64C",
    "danger": "#D96B70",
}


APP_STYLE = """
QWidget {
    color: #263746;
    background: #F2F8FC;
    font-family: "Segoe UI";
    font-size: 14px;
}
QLabel { background: transparent; }
QMainWindow, QDialog { background: #F2F8FC; }
QFrame#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #F7FCFE);
    border-right: 1px solid #DCEAF1;
}
QLabel#brand { color: #263746; font-size: 18px; font-weight: 700; }
QLabel#brandCaption, QLabel#muted, QLabel#pageDescription, QLabel#fieldHint,
QLabel#emptyDescription { color: #718493; }
QLabel#groupHeading {
    color: #8295A2;
    font-size: 10px;
    font-weight: 700;
    padding: 13px 12px 4px 12px;
    letter-spacing: 1px;
}
QListWidget#navigation {
    background: transparent;
    border: 0;
    outline: 0;
    padding: 4px 5px;
}
QListWidget#navigation::item {
    color: #526979;
    min-height: 23px;
    padding: 9px 11px;
    margin: 2px 0;
    border: 1px solid transparent;
    border-radius: 10px;
}
QListWidget#navigation::item:hover {
    color: #2E678B;
    background: #EDF8FC;
}
QListWidget#navigation::item:selected {
    color: #216D9B;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #DDF3FC, stop:1 #E8FBF7);
    border: 1px solid #C9EAF4;
    font-weight: 600;
}
QListWidget#navigation::item:disabled { color: #91A3AE; }
QLabel#pageTitle { font-size: 25px; font-weight: 700; color: #263746; }
QLabel#heroTitle { font-size: 25px; font-weight: 700; color: #263746; }
QLabel#heroSubtitle { color: #526F80; font-size: 15px; }
QFrame#panel, QFrame#statCard, QFrame#heroCard {
    background: #FFFFFF;
    border: 1px solid #DCEAF1;
    border-radius: 15px;
}
QFrame#heroCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #FFFFFF, stop:0.62 #EFFAFF, stop:1 #E9FBF7);
    border: 1px solid #D2EBF3;
}
QFrame#statCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #FFFFFF, stop:1 #F3FBFE);
    min-height: 96px;
}
QLabel#cardValue { font-size: 28px; font-weight: 700; color: #378DBD; }
QLabel#sectionHeading { font-size: 16px; font-weight: 650; color: #2B4557; }
QLineEdit, QTextEdit, QComboBox, QDateEdit, QDateTimeEdit, QTimeEdit, QSpinBox {
    color: #263746;
    background: #FFFFFF;
    border: 1px solid #CFE0E9;
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: #75C9EE;
    min-height: 20px;
}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QDateEdit:hover,
QDateTimeEdit:hover, QTimeEdit:hover, QSpinBox:hover { border-color: #A8D8E9; }
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus,
QDateTimeEdit:focus, QTimeEdit:focus, QSpinBox:focus {
    border: 2px solid #4B9ED8;
    padding: 7px 9px;
}
QComboBox::drop-down { border: 0; width: 26px; }
QPushButton {
    color: #3E5969;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:1 #F2F8FB);
    border: 1px solid #CFE0E9;
    border-radius: 9px;
    padding: 8px 14px;
    min-height: 20px;
}
QPushButton:hover { color: #216D9B; background: #EAF8FC; border-color: #A9D9E9; }
QPushButton:pressed { background: #D9F0F8; border-color: #8BCDE2; }
QPushButton:disabled { color: #9AAAB3; background: #F1F5F7; border-color: #E2EBEF; }
QPushButton[variant="primary"] {
    color: #FFFFFF;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #65BCE5, stop:1 #418FC7);
    border: 1px solid #398BC3;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #75C9EE, stop:1 #4B9ED8);
}
QPushButton[variant="primary"]:pressed { background: #3788C3; }
QPushButton[variant="danger"] { color: #B54F59; background: #FFF8F8; border-color: #F0D7D9; }
QPushButton[variant="danger"]:hover { background: #FCEDEE; border-color: #E7B7BC; }
QTableWidget {
    color: #304655;
    background: #FFFFFF;
    alternate-background-color: #F7FBFD;
    border: 1px solid #DCEAF1;
    border-radius: 10px;
    gridline-color: #EAF1F4;
    selection-background-color: #DDF3FC;
    selection-color: #245E7D;
}
QTableWidget::item { padding: 7px 8px; border: 0; }
QHeaderView::section {
    color: #587080;
    background: #F1F8FB;
    border: 0;
    border-bottom: 1px solid #DCEAF1;
    padding: 9px 8px;
    font-weight: 600;
}
QTableCornerButton::section { background: #F1F8FB; border: 0; }
QCheckBox { spacing: 7px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked { background: white; border: 1px solid #B8CDD7; border-radius: 4px; }
QCheckBox::indicator:checked { background: #58B9CF; border: 1px solid #48A8BE; border-radius: 4px; }
QStatusBar { background: #FFFFFF; color: #718493; border-top: 1px solid #DCEAF1; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #C8DFE9; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #A9D2E1; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMenu { color: #304655; background: #FFFFFF; border: 1px solid #DCEAF1; padding: 5px; }
QMenu::item { padding: 8px 24px; border-radius: 5px; }
QMenu::item:selected { color: #216D9B; background: #E7F6FB; }
QLabel#error { color: #BD5962; }
QLabel#emptyTitle { color: #304655; font-size: 17px; font-weight: 600; }
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLE)


def set_variant(widget: QWidget, variant: str) -> None:
    widget.setProperty("variant", variant)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
