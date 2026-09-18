from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton, QComboBox, QCheckBox, QApplication
)
from src.config import load_config, save_config

STYLE_SHEET = """
QWidget#container {
    background-color: #12161F;
    border: 1.5px solid #00FF88;
    border-radius: 10px;
}
QLabel {
    color: #F0F6FC;
    font-family: sans-serif;
    font-size: 11px;
}
QComboBox, QPushButton {
    background-color: #1F2430;
    color: #F0F6FC;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
}
QComboBox:hover, QPushButton:hover {
    background-color: #2D3342;
    border-color: #8B949E;
}
QPushButton#accentBtn {
    background-color: #238636;
    border: 1px solid #2EA043;
    font-weight: bold;
    padding: 6px;
    font-size: 12px;
}
QPushButton#accentBtn:hover {
    background-color: #2EA043;
}
QPushButton#zeroBtn {
    background-color: #1F2430;
    border: 1px dashed #8B949E;
    font-size: 10px;
    padding: 2px 6px;
}
QPushButton#zeroBtn:hover {
    border-color: #00FF88;
    color: #00FF88;
}
QPushButton#closeHeaderBtn {
    background: transparent;
    border: none;
    color: #8B949E;
    font-size: 14px;
    font-weight: bold;
    padding: 0 4px;
}
QPushButton#closeHeaderBtn:hover {
    color: #FF5555;
}
QSlider::groove:horizontal {
    height: 4px;
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

BORDER_PRESETS = [("#00FF88", "Неон"), ("#00E5FF", "Циан"), ("#FFD700", "Янтарь")]
BG_PRESETS = [("#0F1219", "Тёмно-серый"), ("#000000", "AMOLED"), ("#0B132B", "Синий")]
TEXT_PRESETS = [("#000000", "Чёрный"), ("#FFE600", "Жёлтый"), ("#FFFFFF", "Белый")]


class SettingsDialog(QWidget):
    settings_changed = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(360, 430)
        self.setStyleSheet(STYLE_SHEET)

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
        self.swatch_registry = {}

        self.init_ui()

        screen = QApplication.primaryScreen().geometry()
        pos_x = (screen.width() - self.width()) // 2
        self.move(pos_x, 30)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setObjectName("container")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)

        # Шапка
        header = QHBoxLayout()
        title = QLabel("⚙ Параметры оверлея")
        title.setStyleSheet("font-weight: bold; font-size: 12px; color: #00FF88;")
        header.addWidget(title)
        header.addStretch()

        btn_x = QPushButton("✕")
        btn_x.setObjectName("closeHeaderBtn")
        btn_x.clicked.connect(self.hide_settings)
        header.addWidget(btn_x)
        layout.addLayout(header)

        # 1. Прозрачность фона
        op_title_layout = QHBoxLayout()
        op_title_layout.addWidget(QLabel("Прозрачность фона:"))
        btn_zero = QPushButton("0% (Без фона)")
        btn_zero.setObjectName("zeroBtn")
        btn_zero.clicked.connect(lambda: self.op_slider.setValue(0))
        op_title_layout.addWidget(btn_zero)
        layout.addLayout(op_title_layout)

        op_layout = QHBoxLayout()
        self.op_slider = QSlider(Qt.Horizontal)
        self.op_slider.setRange(0, 100)
        op_val = self.styles.get("overlay_opacity", 85)
        self.op_slider.setValue(op_val)
        self.op_lbl = QLabel(f"{op_val}%")
        self.op_lbl.setFixedWidth(34)
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
        self.font_lbl.setFixedWidth(34)
        self.font_slider.valueChanged.connect(self.on_font_change)
        font_layout.addWidget(self.font_slider)
        font_layout.addWidget(self.font_lbl)
        layout.addLayout(font_layout)

        # 3. Выбор языков
        lang_layout = QHBoxLayout()
        vbox_src = QVBoxLayout()
        vbox_src.addWidget(QLabel("Оригинал:"))
        self.src_combo = QComboBox()
        self.src_combo.addItems(["eng", "jpn", "rus", "rus+eng"])
        self.src_combo.setCurrentText(self.cfg.get("source_lang", "eng"))
        self.src_combo.currentTextChanged.connect(self.on_lang_change)
        vbox_src.addWidget(self.src_combo)
        lang_layout.addLayout(vbox_src)

        vbox_dst = QVBoxLayout()
        vbox_dst.addWidget(QLabel("Перевод:"))
        self.dst_combo = QComboBox()
        self.dst_combo.addItems(["ru", "en"])
        self.dst_combo.setCurrentText(self.cfg.get("target_lang", "ru"))
        self.dst_combo.currentTextChanged.connect(self.on_lang_change)
        vbox_dst.addWidget(self.dst_combo)
        lang_layout.addLayout(vbox_dst)
        layout.addLayout(lang_layout)

        # 4. Пресеты цветов
        layout.addLayout(self.create_preset_row("border_color", "Цвет рамки:", BORDER_PRESETS))
        layout.addLayout(self.create_preset_row("overlay_bg_color", "Цвет фона:", BG_PRESETS))
        layout.addLayout(self.create_preset_row("text_color", "Цвет текста:", TEXT_PRESETS))

        # TODO: Вернуться к ручному вводу HEX/RGB после релиза OCR-пайплайна

        self.update_swatches()

        # 5. Контур захвата
        self.chk_border = QCheckBox("Показывать рамку захвата во время игры")
        self.chk_border.setChecked(self.cfg.get("show_capture_border", False))
        self.chk_border.toggled.connect(self.on_border_toggle)
        layout.addWidget(self.chk_border)

        hotkey_info = QLabel("Глобальный хоткей: <b>F8</b> — скрыть / показать перевод")
        hotkey_info.setStyleSheet("color: #8B949E; font-size: 11px; margin-top: 4px;")
        layout.addWidget(hotkey_info)

        layout.addStretch()

        btn_save = QPushButton("Сохранить и закрыть")
        btn_save.setObjectName("accentBtn")
        btn_save.clicked.connect(self.hide_settings)
        layout.addWidget(btn_save)

        root_layout.addWidget(container)

    def create_preset_row(self, config_key: str, label_text: str, presets: list) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        row.addStretch()

        self.swatch_registry[config_key] = []
        for color, name in presets:
            btn = QPushButton()
            btn.setFixedSize(22, 22)
            btn.setToolTip(name)
            btn.clicked.connect(lambda _, k=config_key, c=color: self.apply_preset(k, c))
            row.addWidget(btn)
            self.swatch_registry[config_key].append((btn, color))

        return row

    def apply_preset(self, config_key: str, color_hex: str):
        self.styles[config_key] = color_hex
        self.update_swatches()
        self.save()

    def update_swatches(self):
        for config_key, swatches in self.swatch_registry.items():
            current = self.styles.get(config_key, "").lower()
            for btn, color in swatches:
                is_active = (current == color.lower())
                border = "2px solid #FFFFFF" if is_active else "1px solid #3A3F4B"
                btn.setStyleSheet(f"background-color: {color}; border-radius: 11px; border: {border};")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.raise_()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self.drag_start_pos.isNull():
            screen = QApplication.primaryScreen().geometry()
            SNAP = 20
            w, h = self.width(), self.height()

            target_pos = event.globalPos() - self.drag_start_pos
            x, y = target_pos.x(), target_pos.y()

            # Прилипание по X
            if abs(x - screen.left()) <= SNAP:
                x = screen.left()
            elif abs((x + w) - screen.right()) <= SNAP:
                x = screen.right() - w + 1

            # Прилипание по Y
            if abs(y - screen.top()) <= SNAP:
                y = screen.top()
            elif abs((y + h) - screen.bottom()) <= SNAP:
                y = screen.bottom() - h + 1

            # Жесткое ограничение внутри экрана
            x = max(screen.left(), min(x, screen.right() - w + 1))
            y = max(screen.top(), min(y, screen.bottom() - h + 1))

            self.move(x, y)
            event.accept()

    def show_settings(self):
        self.show()
        self.raise_()

    def hide_settings(self):
        self.hide()
        self.closed.emit()

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

    def on_lang_change(self):
        self.cfg["source_lang"] = self.src_combo.currentText()
        self.cfg["target_lang"] = self.dst_combo.currentText()
        self.save()

    def save(self):
        self.cfg["styles"] = self.styles
        save_config(self.cfg)
        self.settings_changed.emit()
