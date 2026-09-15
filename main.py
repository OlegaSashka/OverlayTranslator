import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from src.canvas import OverlayCanvas

def create_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(0, 255, 136))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, 32, 32, 6, 6)
    painter.setPen(QColor(0, 0, 0))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "TR")
    painter.end()
    return QIcon(pixmap)

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    canvas = OverlayCanvas()
    canvas.fit_screen()
    canvas.show()

    tray = QSystemTrayIcon(create_tray_icon(), app)
    tray.setToolTip("Steam Deck Overlay Translator")

    menu = QMenu()

    # Единственный тумблер: включение/выключение режима настройки
    action_edit = QAction("Режим настройки (показать рамки)", menu, checkable=True)
    action_edit.setChecked(True)
    action_edit.toggled.connect(canvas.set_edit_mode)
    menu.addAction(action_edit)

    # Синхронизация галочки в трее, если нажали «Готово» прямо на экране
    def on_mode_changed(enabled):
        if action_edit.isChecked() != enabled:
            action_edit.blockSignals(True)
            action_edit.setChecked(enabled)
            action_edit.blockSignals(False)

    canvas.mode_changed.connect(on_mode_changed)

    menu.addSeparator()

    action_quit = QAction("Выход", menu)
    action_quit.triggered.connect(app.quit)
    menu.addAction(action_quit)

    tray.setContextMenu(menu)
    tray.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
