import os
import sys
from src.platform.hotkey import GlobalHotkeyThread

# Гарантируем изоляцию плагинов PyQt5 от сторонних библиотек
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_IM_MODULE"] = "simple"
os.environ["XMODIFIERS"] = "@im=none"

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from src.frames import CaptureFrame, TranslationFrame
from src.settings_dialog import SettingsDialog
from src.ocr_worker import OcrWorker


def create_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(0, 255, 136))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, 32, 32, 6, 6)
    painter.setPen(QColor(10, 15, 20))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "TR")
    painter.end()
    return QIcon(pixmap)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    capture_frame = CaptureFrame()
    translation_frame = TranslationFrame()

    # Глобальный хоткей X11 (F8) для скрытия/показа оверлея
    hotkey_thread = GlobalHotkeyThread(key_name="F8")
    hotkey_thread.activated.connect(translation_frame.toggle_hidden)
    hotkey_thread.start()

    settings_dialog = SettingsDialog()

    def on_settings_changed():
        capture_frame.reload_style()
        translation_frame.reload_style()

    settings_dialog.settings_changed.connect(on_settings_changed)

    def open_settings():
        ocr_worker.set_paused(True)
        capture_frame.set_edit_mode(True)
        translation_frame.set_edit_mode(True)
        settings_dialog.show_settings()

    def close_settings():
        capture_frame.set_edit_mode(False)
        translation_frame.set_edit_mode(False)
        ocr_worker.set_paused(False)

    # При закрытии окна настроек рамки автоматически блокируются в сквозной режим
    settings_dialog.closed.connect(close_settings)

    tray = QSystemTrayIcon(create_tray_icon(), app)
    ocr_worker = OcrWorker()
    ocr_worker.text_captured.connect(translation_frame.set_translation)
    tray.setToolTip("Overlay Translator")
    menu = QMenu()

    def toggle_visibility(visible: bool):
        if visible:
            capture_frame.show()
            translation_frame.show()
        else:
            capture_frame.hide()
            translation_frame.hide()

    action_toggle = QAction("Показывать оверлей", menu, checkable=True)
    action_toggle.setChecked(True)
    action_toggle.toggled.connect(toggle_visibility)
    menu.addAction(action_toggle)

    menu.addSeparator()

    action_settings = QAction("Параметры и позиция...", menu)
    action_settings.triggered.connect(open_settings)
    menu.addAction(action_settings)

    def quit_application():
        hotkey_thread.stop()
        ocr_worker.stop()
        capture_frame._allow_close = True
        translation_frame._allow_close = True
        settings_dialog.close()
        app.quit()

    action_quit = QAction("Выход", menu)
    action_quit.triggered.connect(quit_application)
    menu.addAction(action_quit)

    tray.setContextMenu(menu)
    tray.show()

    capture_frame.show()
    translation_frame.show()

    ocr_worker.start()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
