import ctypes
from ctypes import c_int, c_ulong, c_void_p
from PyQt5.QtCore import QEvent, QPoint, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIntValidator
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
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
x11.XSetInputFocus.argtypes = [c_void_p, c_ulong, c_int, c_ulong]
x11.XSetInputFocus.restype = c_int

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
QPushButton#modeToggleBtn {
    background-color: #1F2430;
    border: 1px solid #00FF88;
    color: #00FF88;
    font-weight: bold;
    font-size: 10px;
    padding: 2px 8px;
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
QLineEdit {
    background-color: #191D26;
    color: #F0F6FC;
    border: 1px solid #30363D;
    border-radius: 4px;
    padding: 2px 4px;
    font-family: monospace;
    font-size: 11px;
}
QLineEdit:focus {
    border: 1px solid #00FF88;
    background-color: #222733;
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


def parse_hex_color(text: str) -> str:
    clean = text.strip()
    if not clean:
        return None
    if not clean.startswith("#"):
        clean = "#" + clean
    c = QColor(clean)
    return c.name().upper() if c.isValid() else None


class SettingsDialog(QWidget):
    settings_changed = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(390, 560)
        self.setStyleSheet(STYLE_SHEET)

        # Полная изоляция от KWin и панели задач
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

        self.input_mode = "HEX"
        self.color_widgets = {}

        self.init_ui()

        # Безопасный глобальный перехватчик фокуса X11
        QApplication.instance().installEventFilter(self)

        screen = QApplication.primaryScreen().geometry()
        pos_x = (screen.width() - self.width()) // 2
        self.move(pos_x, 20)

    def eventFilter(self, obj, event):
        """Безопасно перехватывает клик и форсирует ввод клавиатуры X11."""
        if event.type() == QEvent.MouseButtonPress and self.isVisible():
            # Защита от TypeError: проверяем isinstance(obj, QWidget) до вызова isAncestorOf
            is_our_widget = isinstance(obj, QWidget) and (obj is self or self.isAncestorOf(obj))
            is_our_window = (obj == self.windowHandle())

            if is_our_widget or is_our_window:
                self.raise_to_top()
                if isinstance(obj, QLineEdit):
                    QTimer.singleShot(0, obj.setFocus)
        return super().eventFilter(obj, event)

    def raise_to_top(self):
        """Поднимает окно и аппаратно забирает клавиатурный фокус X11."""
        self.raise_()
        wid = int(self.winId())
        if wid > 2:
            display = x11.XOpenDisplay(None)
            if display:
                x11.XRaiseWindow(display, c_ulong(wid))
                # RevertToParent (2), CurrentTime (0): X-сервер перенаправляет клавиши в наше окно
                x11.XSetInputFocus(display, c_ulong(wid), 2, 0)
                x11.XFlush(display)
                x11.XCloseDisplay(display)

    def show_settings(self):
        self.show()
        self.raise_to_top()
        QTimer.singleShot(50, self.raise_to_top)

    def hide_settings(self):
        self.hide()
        self.closed.emit()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget(self)
        container.setObjectName("container")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(7)

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

        # 4. Переключатель формата
        color_header = QHBoxLayout()
        color_header.addWidget(QLabel("Цветовая схема:"))
        color_header.addStretch()
        self.btn_mode = QPushButton("Формат: HEX")
        self.btn_mode.setObjectName("modeToggleBtn")
        self.btn_mode.clicked.connect(self.toggle_color_format)
        color_header.addWidget(self.btn_mode)
        layout.addLayout(color_header)

        # Ряды выбора цвета
        layout.addLayout(self.create_color_row("border_color", "Рамка захвата:", BORDER_PRESETS))
        layout.addLayout(self.create_color_row("overlay_bg_color", "Фон перевода:", BG_PRESETS))
        layout.addLayout(self.create_color_row("text_color", "Текст перевода:", TEXT_PRESETS))

        self.sync_all_controls()

        # 5. Контур захвата
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

    def create_color_row(self, config_key: str, label_text: str, presets: list) -> QVBoxLayout:
        vbox = QVBoxLayout()
        vbox.setSpacing(3)
        vbox.addWidget(QLabel(label_text))

        row = QHBoxLayout()
        row.setSpacing(6)

        is_custom_key = f"{config_key}_is_custom"
        custom_key = f"custom_{config_key}"

        # Пресеты
        swatches = []
        for color, name in presets:
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setToolTip(name)
            btn.clicked.connect(lambda _, k=config_key, ick=is_custom_key, c=color: self.select_preset(k, ick, c))
            row.addWidget(btn)
            swatches.append((btn, color))

        sep = QLabel("│")
        sep.setStyleSheet("color: #30363D; font-size: 13px;")
        row.addWidget(sep)

        # Кнопка «Свой цвет»
        btn_custom = QPushButton()
        btn_custom.setFixedSize(26, 20)
        btn_custom.setToolTip("Выбрать свой кастомный цвет")
        btn_custom.clicked.connect(lambda _, k=config_key, ick=is_custom_key, ck=custom_key: self.select_custom(k, ick, ck))
        row.addWidget(btn_custom)

        stacked = QStackedWidget()
        stacked.setFixedHeight(26)

        # HEX
        hex_input = QLineEdit()
        hex_input.setPlaceholderText("#HEX")
        hex_input.setAlignment(Qt.AlignCenter)
        hex_input.textEdited.connect(lambda text, k=config_key, ick=is_custom_key, ck=custom_key: self.on_hex_edited(k, ick, ck, text))
        hex_input.editingFinished.connect(lambda k=config_key, ick=is_custom_key, ck=custom_key, le=hex_input: self.on_hex_finished(k, ick, ck, le))
        stacked.addWidget(hex_input)

        # RGB
        rgb_widget = QWidget()
        rgb_layout = QHBoxLayout(rgb_widget)
        rgb_layout.setContentsMargins(0, 0, 0, 0)
        rgb_layout.setSpacing(3)

        validator = QIntValidator(0, 255)
        r_edit, g_edit, b_edit = QLineEdit(), QLineEdit(), QLineEdit()

        for edit, tag in [(r_edit, "R"), (g_edit, "G"), (b_edit, "B")]:
            edit.setValidator(validator)
            edit.setPlaceholderText(tag)
            edit.setAlignment(Qt.AlignCenter)
            edit.setFixedWidth(36)
            edit.textEdited.connect(lambda _, k=config_key, ick=is_custom_key, ck=custom_key: self.on_rgb_edited(k, ick, ck))
            rgb_layout.addWidget(edit)

        stacked.addWidget(rgb_widget)
        row.addWidget(stacked)

        vbox.addLayout(row)

        self.color_widgets[config_key] = {
            "custom_key": custom_key,
            "is_custom_key": is_custom_key,
            "btn_custom": btn_custom,
            "stack": stacked,
            "hex": hex_input,
            "rgb": (r_edit, g_edit, b_edit),
            "swatches": swatches
        }
        return vbox

    def toggle_color_format(self):
        self.input_mode = "RGB" if self.input_mode == "HEX" else "HEX"
        self.btn_mode.setText(f"Формат: {self.input_mode}")
        for w in self.color_widgets.values():
            w["stack"].setCurrentIndex(0 if self.input_mode == "HEX" else 1)
        self.sync_all_controls()

    def select_preset(self, active_key: str, is_custom_key: str, color_hex: str):
        """Активирует пресет, не затирая сохранённый пользователем кастомный цвет."""
        self.styles[active_key] = color_hex
        self.styles[is_custom_key] = False
        self.save()
        self.sync_all_controls()

    def select_custom(self, active_key: str, is_custom_key: str, custom_key: str):
        """Активирует ранее введённый кастомный цвет."""
        c_val = self.styles.get(custom_key, "#FFFFFF")
        self.styles[active_key] = c_val
        self.styles[is_custom_key] = True
        self.save()
        self.sync_all_controls()

    def on_hex_edited(self, active_key: str, is_custom_key: str, custom_key: str, text: str):
        parsed = parse_hex_color(text)
        if parsed and len(text.strip().lstrip("#")) == 6:
            self.styles[custom_key] = parsed
            self.styles[active_key] = parsed
            self.styles[is_custom_key] = True
            self.save()
            self.sync_all_controls()

    def on_hex_finished(self, active_key: str, is_custom_key: str, custom_key: str, line_edit: QLineEdit):
        parsed = parse_hex_color(line_edit.text())
        if parsed:
            self.styles[custom_key] = parsed
            self.styles[active_key] = parsed
            self.styles[is_custom_key] = True
            self.save()
        self.sync_all_controls()

    def on_rgb_edited(self, active_key: str, is_custom_key: str, custom_key: str):
        w = self.color_widgets[active_key]
        r_text, g_text, b_text = [e.text().strip() for e in w["rgb"]]
        if r_text and g_text and b_text:
            try:
                r = max(0, min(255, int(r_text)))
                g = max(0, min(255, int(g_text)))
                b = max(0, min(255, int(b_text)))
                new_hex = f"#{r:02X}{g:02X}{b:02X}"
                self.styles[custom_key] = new_hex
                self.styles[active_key] = new_hex
                self.styles[is_custom_key] = True
                self.save()
                self.sync_all_controls()
            except ValueError:
                pass

    def sync_all_controls(self):
        for active_key, w in self.color_widgets.items():
            is_custom = self.styles.get(w["is_custom_key"], False)
            curr_active = self.styles.get(active_key, "#FFFFFF").lower()
            custom_key = w["custom_key"]

            if custom_key not in self.styles:
                self.styles[custom_key] = self.styles.get(active_key, "#FFFFFF")
            custom_val = self.styles[custom_key].upper()

            qcolor = QColor(custom_val)
            if not qcolor.isValid():
                qcolor = QColor("#FFFFFF")

            # 1. Подсветка пресетов (белая рамка)
            for btn, color in w["swatches"]:
                is_active = (not is_custom) and (curr_active == color.lower())
                border = "2px solid #FFFFFF" if is_active else "1px solid #3A3F4B"
                btn.setStyleSheet(f"background-color: {color}; border-radius: 10px; border: {border};")

            # 2. Кнопка «Свой цвет» (неоновая зеленая рамка, когда активна)
            custom_border = "2px solid #00FF88" if is_custom else "1px solid #555555"
            w["btn_custom"].setStyleSheet(
                f"background-color: {custom_val}; border-radius: 4px; border: {custom_border};"
            )

            # 3. Поля ввода (отображают custom_val, не сбивая курсор при наборе)
            if not w["hex"].hasFocus():
                w["hex"].setText(custom_val)

            r_edit, g_edit, b_edit = w["rgb"]
            if not (r_edit.hasFocus() or g_edit.hasFocus() or b_edit.hasFocus()):
                r_edit.setText(str(qcolor.red()))
                g_edit.setText(str(qcolor.green()))
                b_edit.setText(str(qcolor.blue()))

    def mousePressEvent(self, event):
        self.raise_to_top()
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and not self.drag_start_pos.isNull():
            self.move(event.globalPos() - self.drag_start_pos)
            event.accept()

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

    def save(self):
        self.cfg["styles"] = self.styles
        save_config(self.cfg)
        self.settings_changed.emit()
