import ctypes
from ctypes import c_void_p, c_ulong, c_int
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton, QColorDialog, QComboBox, QCheckBox, QApplication
)
from src.config import load_config, save_config

x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XOpenDisplay.restype = c_void_p
x11.XCloseDisplay.argtypes = [c_void_p]
x11.XCloseDisplay.restype = c_int
x11.XFlush.argtypes = [c_void_p]
x11.XFlush.restype = c_int
x11.XRaiseWindow.argtypes = [c_void_p, c_ulong]
x11.XRaiseWindow.restype = c_int

STYLE_SHEET = """
QWidget#container {
    background-color: #12161F;
    border: 1.5px solid #00FF88;
    border-radius: 10px;
}
QLabel {
    color: #F0F6FC;
    font-family: sans-serif;
    font-size: 12px;
}
QComboBox, QPushButton {
    background-color: #1F2430;
    color: #F0F6FC;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}
QComboBox:hover, QPushButton:hover {
    background-color: #2D3342;
    border-color: #8B949E;
}
QPushButton#accentBtn {
    background-color: #238636;
    border: 1px solid #2EA043;
    font-weight: bold;
    padding: 7px;
}
QPushButton#accentBtn:hover {
    background-color: #2EA043;
}
QPushButton#closeHeaderBtn {
    background: transparent;
    border: none;
    color: #8B949E;
    font-size: 15px;
    font-weight: bold;
    padding: 0 4px;
}
QPushButton#closeHeaderBtn:hover {
    color: #FF5555;
}
QSlider::groove:horizontal {
    height: 5px;
    background: #2D3342;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #00FF88;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
"""


class SettingsDialog(QWidget):
    settings_changed = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(360, 370)
        self.setStyleSheet(STYLE_SHEET)

        # Тот же самый системный уровень, что и у рамок оверлея
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        self.cfg = load_config()
        self.styles = self.cfg.get("styles", {})
        self.drag_start_pos = QPoint()

        self.init_ui()

        # Размещение по центру в верхней трети экрана
        screen = QApplication.primaryScreen().geometry()
        pos_x = (screen.width() - self.width()) // 2
        self.move(pos_x, 40)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # Фоновый контейнер с собственной рамкой
        container = QWidget(self)
        container.setObjectName("container")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)

        # Шапка с заголовком и кнопкой закрытия
        header = QHBoxLayout()
        title = QLabel("⚙ Параметры оверлея")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #00FF88;")
        header.addWidget(title)
        header.addStretch()

        btn_x = QPushButton("✕")
        btn_x.setObjectName("closeHeaderBtn")
        btn_x.clicked.connect(self.hide_settings)
        header.addWidget(btn_x)
        layout.addLayout(header)

        # 1. Прозрачность
        layout.addWidget(QLabel("Прозрачность плашки перевода:"))
        op_layout = QHBoxLayout()
        self.op_slider = QSlider(Qt.Horizontal)
        self.op_slider.setRange(10, 100)
        op_val = self.styles.get("overlay_opacity", 85)
        self.op_slider.setValue(op_val)
        self.op_lbl = QLabel(f"{op_val}%")
        self.op_slider.valueChanged.connect(self.on_opacity_change)
        op_layout.addWidget(self.op_slider)
        op_layout.addWidget(self.op_lbl)
        layout.addLayout(op_layout)

        # 2. Размер шрифта
        layout.addWidget(QLabel("Размер шрифта субтитров:"))
        font_layout = QHBoxLayout()
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setRange(11, 26)
        f_val = self.styles.get("font_size", 15)
        self.font_slider.setValue(f_val)
        self.font_lbl = QLabel(f"{f_val} pt")
        self.font_slider.valueChanged.connect(self.on_font_change)
        font_layout.addWidget(self.font_slider)
        font_layout.addWidget(self.font_lbl)
        layout.addLayout(font_layout)

        # 3. Выбор языков
        lang_layout = QHBoxLayout()
        vbox_src = QVBoxLayout()
        vbox_src.addWidget(QLabel("Оригинал:"))
        self.src_combo = QComboBox()
        self.src_combo.addItems(["eng", "jpn", "rus"])
        vbox_src.addWidget(self.src_combo)
        lang_layout.addLayout(vbox_src)

        vbox_dst = QVBoxLayout()
        vbox_dst.addWidget(QLabel("Перевод:"))
        self.dst_combo = QComboBox()
        self.dst_combo.addItems(["ru", "en"])
        vbox_dst.addWidget(self.dst_combo)
        lang_layout.addLayout(vbox_dst)
        layout.addLayout(lang_layout)

        # 4. Цвета
        colors_layout = QHBoxLayout()
        btn_bg = QPushButton("🎨 Цвет фона")
        btn_bg.clicked.connect(self.choose_bg)
        colors_layout.addWidget(btn_bg)

        btn_border = QPushButton("🎯 Цвет рамки")
        btn_border.clicked.connect(self.choose_border)
        colors_layout.addWidget(btn_border)
        layout.addLayout(colors_layout)

        # 5. Чекбокс контура
        self.chk_border = QCheckBox("Показывать рамку захвата во время игры")
        self.chk_border.setChecked(self.cfg.get("show_capture_border", False))
        self.chk_border.toggled.connect(self.on_border_toggle)
        layout.addWidget(self.chk_border)

        layout.addStretch()

        btn_save = QPushButton("Сохранить и закрыть")
        btn_save.setObjectName("accentBtn")
        btn_save.clicked.connect(self.hide_settings)
        layout.addWidget(btn_save)

        root_layout.addWidget(container)

    # Перетаскивание панели мышью за любое свободное место
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.raise_to_top()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self.drag_start_pos.isNull():
            self.move(event.globalPos() - self.drag_start_pos)
            event.accept()

    def show_settings(self):
        """Отображает карточку и форсирует её положение на вершине стека X11."""
        self.show()
        self.raise_to_top()

    def hide_settings(self):
        self.hide()
        self.closed.emit()

    def raise_to_top(self):
        self.raise_()
        wid = int(self.winId())
        if wid > 2:
            display = x11.XOpenDisplay(None)
            if display:
                x11.XRaiseWindow(display, c_ulong(wid))
                x11.XFlush(display)
                x11.XCloseDisplay(display)

    def on_opacity_change(self, val):
        self.op_lbl.setText(f"{val}%")
        self.styles["overlay_opacity"] = val
        self.save()

    def on_font_change(self, val):
        self.font_lbl.setText(f"{val} pt")
        self.styles["font_size"] = val
        self.save()

    def on_border_toggle(self, checked):
        self.cfg["show_capture_border"] = checked
        self.save()

    def choose_bg(self):
        c = QColorDialog.getColor(QColor(self.styles.get("overlay_bg_color", "#0F1219")), self)
        if c.isValid():
            self.styles["overlay_bg_color"] = c.name()
            self.save()
            self.raise_to_top()

    def choose_border(self):
        c = QColorDialog.getColor(QColor(self.styles.get("border_color", "#00FF88")), self)
        if c.isValid():
            self.styles["border_color"] = c.name()
            self.save()
            self.raise_to_top()

    def save(self):
        self.cfg["styles"] = self.styles
        save_config(self.cfg)
        self.settings_changed.emit()
