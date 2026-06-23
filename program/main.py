import sys
import json
import numpy as np
import os
from pathlib import Path
from PySide6.QtCore import QTimer, Qt, QRectF
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QFileDialog)
from PySide6.QtGui import QPainter, QColor, QPen, QMouseEvent, QPalette, QIcon, QPixmap

# Включение поддержки HiDPI (для современных экранов)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class GameOfLife:
    def __init__(self, rows=40, cols=60):
        self.rows = rows
        self.cols = cols
        self.grid = np.zeros((rows, cols), dtype=int)
        self.generation = 0

    def step(self):
        neighbors = np.zeros_like(self.grid)
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                neighbors += np.roll(np.roll(self.grid, dr, 0), dc, 1)
        birth = (neighbors == 3) & (self.grid == 0)
        survive = ((neighbors == 2) | (neighbors == 3)) & (self.grid == 1)
        self.grid = (birth | survive).astype(int)
        self.generation += 1

    def count_alive(self):
        return int(np.sum(self.grid))

    def clear(self):
        self.grid.fill(0)
        self.generation = 0

    def random_fill(self, density=0.3):
        self.grid = (np.random.random((self.rows, self.cols)) < density).astype(int)
        self.generation = 0


class FieldWidget(QWidget):
    def __init__(self, game, update_stats_callback):
        super().__init__()
        self.game = game
        self.update_stats_callback = update_stats_callback
        self.cell_size = 15
        self.setFixedSize(game.cols * self.cell_size, game.rows * self.cell_size)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        for r in range(self.game.rows):
            for c in range(self.game.cols):
                rect = QRectF(c * self.cell_size, r * self.cell_size,
                              self.cell_size, self.cell_size)
                if self.game.grid[r, c] == 1:
                    painter.setBrush(QColor("#2ecc71"))
                else:
                    painter.setBrush(QColor("#2c3e50"))
                painter.setPen(QPen(QColor("#34495e"), 0.5))
                painter.drawRect(rect)

    def handle_mouse_event(self, event):
        x = event.position().x()
        y = event.position().y()
        c = int(x // self.cell_size)
        r = int(y // self.cell_size)
        if 0 <= r < self.game.rows and 0 <= c < self.game.cols:
            if event.buttons() == Qt.LeftButton:
                self.game.grid[r, c] = 1
                self.update()
                self.update_stats_callback()
            elif event.buttons() == Qt.RightButton:
                self.game.grid[r, c] = 0
                self.update()
                self.update_stats_callback()

    def mousePressEvent(self, event: QMouseEvent):
        self.handle_mouse_event(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self.handle_mouse_event(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Игра Жизнь Конвея (B3/S23)")
        self.game = GameOfLife(50, 70)
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_step)
        self.init_ui()
        
        # Устанавливаем иконку для окна
        self.set_window_icon()

    def set_window_icon(self):
        """Устанавливает иконку для окна и панели задач"""
        
        # Для скомпилированного EXE - иконка уже вшита, но нужно принудительно загрузить
        try:
            # Пытаемся загрузить иконку из ресурсов EXE
            # Используем ID 1 - стандартный ID для главной иконки
            icon = QIcon()
            # Добавляем иконку с разных размеров для лучшего отображения
            icon.addFile("icon.ico")
            self.setWindowIcon(icon)
            QApplication.setWindowIcon(icon)
            print("✅ Иконка загружена из файла")
            return
        except:
            pass
        
        # Если не получилось, ищем файл иконки
        icon_paths = [
            "icon.ico",
            "icon.png",
            "icon.icns",
            "icon.jpg",
            "icon.jpeg",
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                icon = QIcon(path)
                if not icon.isNull():
                    self.setWindowIcon(icon)
                    QApplication.setWindowIcon(icon)
                    print(f"✅ Иконка загружена: {path}")
                    return
        
        # Создаём иконку-заглушку
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#2ecc71"))
        icon = QIcon(pixmap)
        self.setWindowIcon(icon)
        QApplication.setWindowIcon(icon)
        print("✅ Создана иконка-заглушка")

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        control_layout = QHBoxLayout()

        self.btn_start = QPushButton("Старт")
        self.btn_start.clicked.connect(self.toggle_game)
        control_layout.addWidget(self.btn_start)

        btn_step = QPushButton("Шаг")
        btn_step.clicked.connect(self.step_once)
        control_layout.addWidget(btn_step)

        btn_clear = QPushButton("Очистить")
        btn_clear.clicked.connect(self.clear_game)
        control_layout.addWidget(btn_clear)

        btn_random = QPushButton("Случайно")
        btn_random.clicked.connect(self.random_game)
        control_layout.addWidget(btn_random)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_state)
        control_layout.addWidget(btn_save)

        btn_load = QPushButton("Загрузить")
        btn_load.clicked.connect(self.load_state)
        control_layout.addWidget(btn_load)

        control_layout.addWidget(QLabel("Скорость:"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(10)
        self.slider.setMaximum(500)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self.change_speed)
        control_layout.addWidget(self.slider)
        control_layout.addWidget(QLabel("мс/шаг"))

        main_layout.addLayout(control_layout)

        self.field = FieldWidget(self.game, self.update_status)
        main_layout.addWidget(self.field, alignment=Qt.AlignCenter)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        self.update_status()

        self.setCentralWidget(main_widget)

    def toggle_game(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_start.setText("Старт")
        else:
            self.timer.start(self.slider.value())
            self.btn_start.setText("Пауза")
        self.update_status()

    def step_once(self):
        was_running = self.timer.isActive()
        if was_running:
            self.toggle_game()
        self.game_step()
        if was_running:
            self.toggle_game()

    def game_step(self):
        old_grid = self.game.grid.copy()
        self.game.step()
        changed = not np.array_equal(old_grid, self.game.grid)

        self.field.update()
        self.update_status()

        if not changed and self.timer.isActive():
            self.timer.stop()
            self.btn_start.setText("Старт")
            self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
            self.status_label.setText(
                f"Поколение: {self.game.generation}  |  Живых клеток: {self.game.count_alive()}  |  СТАБИЛЬНО"
            )

    def change_speed(self):
        if self.timer.isActive():
            self.timer.start(self.slider.value())

    def clear_game(self):
        was_running = self.timer.isActive()
        if was_running:
            self.toggle_game()
        self.game.clear()
        self.field.update()
        self.update_status()
        if was_running:
            self.toggle_game()

    def random_game(self):
        was_running = self.timer.isActive()
        if was_running:
            self.toggle_game()
        self.game.random_fill()
        self.field.update()
        self.update_status()
        if was_running:
            self.toggle_game()

    def update_status(self):
        alive = self.game.count_alive()
        if self.timer.isActive():
            self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: #ecf0f1;")
        self.status_label.setText(f"Поколение: {self.game.generation}  |  Живых клеток: {alive}")

    def save_state(self):
        default_dir = str(Path.home() / "Documents" / "GameOfLife")
        os.makedirs(default_dir, exist_ok=True)
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить состояние", 
            default_dir, "JSON Files (*.json)"
        )
        if path:
            data = {
                "generation": self.game.generation,
                "grid": self.game.grid.tolist(),
                "rows": self.game.rows,
                "cols": self.game.cols
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Сохранено в {path}")

    def load_state(self):
        default_dir = str(Path.home() / "Documents" / "GameOfLife")
        os.makedirs(default_dir, exist_ok=True)
        
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить состояние", 
            default_dir, "JSON Files (*.json)"
        )
        if path:
            was_running = self.timer.isActive()
            if was_running:
                self.toggle_game()
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.game.generation = data["generation"]
            self.game.grid = np.array(data["grid"], dtype=int)
            self.field.update()
            self.update_status()
            print(f"Загружено из {path}")
            if was_running:
                self.toggle_game()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Тёмная тема
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())