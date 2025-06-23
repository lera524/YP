import sys
import os
import time
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QFrame,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget,
    QListWidget, QListWidgetItem, QMessageBox, QGraphicsOpacityEffect,
    QScrollArea, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem,
    QSizePolicy
)
from PyQt6.QtGui import QPixmap, QPainter, QMouseEvent, QColor, QCursor, QIcon, QPalette, QFont, QPen
from PyQt6.QtCore import (
    Qt, QPoint, QRect, QSize, QUrl, QPropertyAnimation,
    QPointF, QRectF, QObject, QTimer
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)

class MusicPlayer:
    def __init__(self):
        self.audio_output = QAudioOutput() 
        self.player.setAudioOutput(self.audio_output)
        self.current_track = 0 
        self.is_playing = False 
        self.playlist = [] 
        self.load_playlist() 
        self.player.mediaStatusChanged.connect(self.handle_media_status_changed)
    def load_playlist(self):
        songs_dir = resource_path('songs')
        if not os.path.exists(songs_dir):
            os.makedirs(songs_dir)
        self.playlist = [os.path.join(songs_dir, f) for f in os.listdir(songs_dir)
                        if f.endswith(('.mp3', '.wav'))]
    def play(self):
        if not self.playlist:
            return    
        if not self.is_playing:
            self.is_playing = True
            self.play_current_track()
    def play_current_track(self):
        if 0 <= self.current_track < len(self.playlist):
            self.player.setSource(QUrl.fromLocalFile(os.path.abspath(self.playlist[self.current_track])))
            self.player.play()
         #setSource - фокус на файле; QUrl - интерфейс для работы с Url-адресами            
    def handle_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Переходим к следующему треку
            self.current_track = (self.current_track + 1) % len(self.playlist)
            self.play_current_track()            
    def stop(self):#остановка воспроизведения трека
        self.is_playing = False
        self.player.stop()        
    def toggle(self):#вкл/выкл
        if self.is_playing:
            self.stop()
        else:
            self.play()            
    def set_volume(self, volume):#громкость
        self.audio_output.setVolume(volume / 100.0)
music_player = MusicPlayer()

class MusicButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(45, 45)
        self.setIcon(QIcon(resource_path('icons/music_note.png')))
        self.setIconSize(QSize(25, 25))
        self.setCheckable(True)
        self.setChecked(music_player.is_playing)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                border: 3px solid black;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
            QPushButton:checked {
                background-color: #008080;
            }
        """)
        self.clicked.connect(self.toggle_music)
    def toggle_music(self):
        music_player.toggle()# Синхронизируем состояние всех кнопок музыки
        for window in QApplication.topLevelWidgets():
            for button in window.findChildren(MusicButton):
                button.setChecked(music_player.is_playing)

class PuzzlePiece(QGraphicsPixmapItem):
    def __init__(self, pixmap, correct_pos, piece_id, game_window, parent=None):
        super().__init__(pixmap, parent)
        self.original_pixmap = pixmap
        self.piece_pixmap = pixmap
        self.correct_pos = correct_pos
        self.piece_id = piece_id
        self.game_window = game_window
        self.dragging = False
        self.is_placed = False
        self.offset = QPointF()
        self._scale = 1.0        
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)        
        self.setPos(correct_pos)
        self.setZValue(0)
    def hoverEnterEvent(self, event):
        if not self.is_placed:
            self.setScale(1)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.setZValue(2)
    def hoverLeaveEvent(self, event):
        if not self.is_placed:
            self.setScale(1.0)
            self.setZValue(1)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_placed:
            self.dragging = True
            self.offset = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.setZValue(3)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.setZValue(1)
            self.check_position()
    def mouseMoveEvent(self, event):
        if self.dragging and not self.is_placed:
            new_pos = self.mapToScene(event.pos() - self.offset)
            scene_rect = self.scene().sceneRect()
            new_pos.setX(max(0, min(new_pos.x(), scene_rect.width() - self.pixmap().width())))
            new_pos.setY(max(0, min(new_pos.y(), scene_rect.height() - self.pixmap().height())))            
            self.setPos(new_pos)
    def check_position(self):#проверка положения пазла
        current_pos = self.pos()
        distance_to_correct = (current_pos - self.correct_pos).manhattanLength()
        if distance_to_correct < 25:
            self.setPos(QPointF(
                round(self.correct_pos.x()),
                round(self.correct_pos.y())
            ))
            self.is_placed = True
            self.game_window.play_snap_sound()
            self.game_window.check_completion()

class GameField(QFrame):
    def __init__(self, width, height, grid_size, is_puzzle_field=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.grid_size = grid_size
        self.cell_width = width // grid_size
        self.cell_height = height // grid_size
        self.is_puzzle_field = is_puzzle_field
        if is_puzzle_field:
            self.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 4px solid #2F4F4F;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #E8E8E8;
                    border: 2px dashed #2F4F4F;
                }
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_puzzle_field:
            painter = QPainter(self)
            if hasattr(self, 'background_image'):
                painter.setOpacity(0.2)
                painter.drawPixmap(self.rect(), self.background_image)
                painter.setOpacity(1.0)
            pen = QPen(QColor("#CCCCCC"))
            pen.setWidth(1)
            painter.setPen(pen)
            for i in range(1, self.grid_size):
                y = i * self.cell_height
                painter.drawLine(0, y, self.width(), y)
            for i in range(1, self.grid_size):
                x = i * self.cell_width
                painter.drawLine(x, 0, x, self.height())

    def set_background_image(self, pixmap):
        if self.is_puzzle_field:
            self.background_image = pixmap
            self.update()

class GameWindow(QWidget):
    def __init__(self, image_path, grid_size):
        super().__init__()
        self.image_path = image_path
        self.grid_size = grid_size
        self.pieces = []
        self.original_image = QPixmap(image_path)
        # таймер
        self.elapsed_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        # масштабирование изображения
        max_size = 700
        self.scaled_image = self.original_image.scaled(
            max_size, max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.is_completed = False
        self.hint_visible = False
        self.scene = QGraphicsScene()
        self.zoom_factor = 1.0
        self.initUI()   
        # Настройка звука "щелчка" при соединении
        self.snap_player = QMediaPlayer()
        self.snap_audio = QAudioOutput()
        self.snap_player.setAudioOutput(self.snap_audio)
        snap_sound_path = resource_path('snap.mp3')
        if os.path.exists(snap_sound_path):
            self.snap_player.setSource(QUrl.fromLocalFile(snap_sound_path))
    
        self.timer.start(1000)  
        self.center_window()

    def update_timer(self):
        if not self.is_completed:
            self.elapsed_time += 1
            minutes = self.elapsed_time // 60
            seconds = self.elapsed_time % 60
            self.timer_label.setText(f"Время: {minutes:02d}:{seconds:02d}")

    def initUI(self):
        self.setWindowTitle('Собери пазл')
        self.setMinimumSize(800, 600)
        window_width = max(800, self.scaled_image.width() + 300)
        window_height = max(600, self.scaled_image.height() + 200)
        self.resize(window_width, window_height)
        self.setStyleSheet('background-color: LightSlateGray;')
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        self.setLayout(main_layout)
        left_panel = QVBoxLayout()
        self.timer_label = QLabel("Время: 00:00")
        self.timer_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
                padding: 10px;
                background-color: #2F4F4F;
                border-radius: 10px;
                margin-bottom: 10px;
            }
        """)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(self.timer_label)
        preview_label = QLabel()
        preview_pixmap = self.original_image.scaled(
            250, 250,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        preview_label.setPixmap(preview_pixmap)
        preview_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 4px solid #2F4F4F;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_panel.addWidget(preview_label)
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        zoom_layout = QHBoxLayout()
        self.zoom_in_btn = QPushButton('+')
        self.zoom_out_btn = QPushButton('-')
        for btn in [self.zoom_in_btn, self.zoom_out_btn]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2F4F4F;
                    color: white;
                    border: 2px solid black;
                    border-radius: 20px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: #008080;
                }
                QPushButton:disabled {
                    background-color: #808080;
                    color: #A9A9A9;
                }
            """)
            zoom_layout.addWidget(btn)
        
        self.zoom_in_btn.clicked.connect(lambda: self.zoom(1.2))
        self.zoom_out_btn.clicked.connect(lambda: self.zoom(0.8))
        self.update_zoom_buttons()
        buttons_layout.addLayout(zoom_layout)
        buttons_layout.addSpacing(10)
        top_buttons = QHBoxLayout()
        top_buttons.setSpacing(10)
        music_btn = MusicButton()
        top_buttons.addWidget(music_btn)
        back_btn = QPushButton()
        back_btn.setFixedSize(45, 45)
        back_btn.setIcon(QIcon(resource_path('icons/back.png')))
        back_btn.setIconSize(QSize(25, 25))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                border: 2px solid black;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
        """)
        back_btn.clicked.connect(self.handle_back)
        top_buttons.addWidget(back_btn)
        buttons_layout.addLayout(top_buttons)
        bottom_buttons = QHBoxLayout()
        bottom_buttons.setSpacing(10)
        reset_btn = QPushButton("Начать сначала")
        reset_btn.setFixedSize(150, 40)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                font-family: 'Georgia';
                color: #FFE4E1;
                border: 2px solid black;
                border-radius: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #CD5C5C;
            }
        """)
        reset_btn.clicked.connect(self.reset_progress)
        bottom_buttons.addWidget(reset_btn)
        hint_btn = QPushButton('Подсказка')
        hint_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                font-family: 'Georgia';
                color: #FFE4E1;
                border: 2px solid black;
                border-radius: 20px;
                font-size: 14px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
            QPushButton:checked {
                background-color: #008080;
            }
        """)
        hint_btn.setFixedSize(100, 40)
        hint_btn.setCheckable(True)
        hint_btn.clicked.connect(self.toggle_hint)
        bottom_buttons.addWidget(hint_btn)
        buttons_layout.addLayout(bottom_buttons)

        help_text = QLabel(
            "Управление:\n"
            "• Левая кнопка мыши - перетаскивание\n"
            "• + / - - масштабирование\n"
        )
        help_text.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-family: 'Georgia';
                padding: 10px;
                background-color: #2F4F4F;
                border-radius: 10px;
                border: 2px solid black;
            }
        """)
        help_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        buttons_layout.addWidget(help_text)

        left_panel.addLayout(buttons_layout)
        left_panel.addStretch()
        main_layout.addLayout(left_panel)

        # поле для пазла
        self.view = QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setMinimumSize(500, 400)
        
        # изменение размера
        size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.setSizePolicy(size_policy)
        self.view.setStyleSheet("""
            QGraphicsView {
                background-color: white;
                border: 4px solid #2F4F4F;
                border-radius: 10px;
            }
        """)
        
        scene_width = self.scaled_image.width() * 2
        scene_height = self.scaled_image.height() * 1.5
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
        
        # прямоугольник для области сборки пазла
        assembly_rect = self.scene.addRect(
            0, 0,
            self.scaled_image.width(),
            self.scaled_image.height(),
            QPen(QColor("#2F4F4F"), 2), 
            QColor(240, 240, 240)  
        )
        
        main_layout.addWidget(self.view)
        
        self.initialize_puzzle()
        self.adjust_view()

    def zoom(self, factor):
        #проверка, не выйдет ли новый масштаб за пределы допустимых значений
        new_zoom = self.zoom_factor * factor
        if 0.5 <= new_zoom <= 2.0:
            self.zoom_factor = new_zoom
            self.view.scale(factor, factor)
            self.update_zoom_buttons()

    def update_zoom_buttons(self):
        self.zoom_in_btn.setEnabled(self.zoom_factor < 2.0)
        self.zoom_out_btn.setEnabled(self.zoom_factor > 0.5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_view()
    def toggle_hint(self, checked):
        self.hint_visible = checked
        if checked:
            if not hasattr(self, 'hint_pixmap'):
                self.hint_pixmap = self.scene.addPixmap(self.scaled_image)
                effect = QGraphicsOpacityEffect()
                effect.setOpacity(0.3)
                self.hint_pixmap.setGraphicsEffect(effect)
            self.hint_pixmap.show()
        else:
            if hasattr(self, 'hint_pixmap'):
                self.hint_pixmap.hide()

    def initialize_puzzle(self):
        self.create_new_puzzle()

    def create_new_puzzle(self):
        piece_width = self.scaled_image.width() // self.grid_size
        piece_height = self.scaled_image.height() // self.grid_size
  
        scene_width = self.scene.width()
        scene_height = self.scene.height()
        placement_x_start = self.scaled_image.width() + piece_width
        placement_width = scene_width - placement_x_start - piece_width
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                # вырезаем фрагмент из изображения с точными размерами
                piece_rect = QRect(
                    col * piece_width,
                    row * piece_height,
                    piece_width,
                    piece_height
                )
                piece_pixmap = self.scaled_image.copy(piece_rect)
                
                # точная позицию на игровом поле
                correct_pos = QPointF(
                    col * piece_width,
                    row * piece_height
                )
                # создание фрагмента
                piece = PuzzlePiece(
                    piece_pixmap,
                    correct_pos,
                    len(self.pieces),
                    self
                )
                # добавление фрагмента на сцену
                self.scene.addItem(piece)
                # поиск свободного места
                max_attempts = 50
                placed = False
                for _ in range(max_attempts):
                    random_x = random.randint(int(placement_x_start), int(scene_width - piece_width))
                    random_y = random.randint(0, int(scene_height - piece_height))
                    new_pos = QPointF(random_x, random_y)
                    overlap = False
                    for existing_piece in self.pieces:
                        if (abs(existing_piece.pos().x() - random_x) < piece_width and
                            abs(existing_piece.pos().y() - random_y) < piece_height):
                            overlap = True
                            break
                    
                    if not overlap:
                        piece.setPos(new_pos)
                        placed = True
                        break
                if not placed:
                    random_x = random.randint(int(placement_x_start), int(scene_width - piece_width))
                    random_y = random.randint(0, int(scene_height - piece_height))
                    piece.setPos(QPointF(random_x, random_y))
                self.pieces.append(piece)

    def check_completion(self):
        #проверка завершения сборки пазла
        if not self.is_completed and all(piece.is_placed and 
            (piece.pos() - piece.correct_pos).manhattanLength() < 1 for piece in self.pieces):
            self.is_completed = True
            self.timer.stop()
            self.show_completion_message()

    def show_completion_message(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Поздравляю!")
        minutes = self.elapsed_time // 60
        seconds = self.elapsed_time % 60
        dialog.setText(f"Пазл собран!\nВремя сборки: {minutes:02d}:{seconds:02d}")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: LightSlateGray;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 16px;
                font-family: 'Georgia';
                min-width: 200px;
                min-height: 50px;
            }
            QPushButton {
                background-color: #2F4F4F;
                color: white;
                border: 2px solid black;
                border-radius: 10px;
                padding: 5px 15px;
                font-size: 14px;
                min-width: 100px;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
        """)

        restart_button = dialog.addButton("Собрать заново", QMessageBox.ButtonRole.ActionRole)
        back_button = dialog.addButton("Назад", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        if dialog.clickedButton() == restart_button:
            self.reset_progress()
        elif dialog.clickedButton() == back_button:
            self.close()

    def reset_progress(self):
        # останавливаем и сбрасываем таймер
        self.timer.stop()
        self.elapsed_time = 0
        self.timer_label.setText("Время: 00:00")
        # удаляем все фрагменты
        for piece in self.pieces:
            self.scene.removeItem(piece)
        self.pieces.clear()
        self.is_completed = False        
        self.create_new_puzzle()        
        self.adjust_view()        
        self.timer.start(1000)
    def play_snap_sound(self):
        if self.snap_player.source().isValid():
            self.snap_player.setPosition(0)
            self.snap_player.play()
    def handle_back(self):
        self.close()
    def adjust_view(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = 1.0
        self.update_zoom_buttons()
    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)
class DifficultyWindow(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.initUI()
        self.center_window()
    def initUI(self):
        self.setWindowTitle('Выберите сложность')
        self.setFixedSize(1000, 500)
        self.setStyleSheet('background-color: LightSlateGray;')
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        top_layout = QHBoxLayout()
        title = QLabel('Выберите сложность')
        title.setFont(QFont('Georgia', 32, QFont.Weight.Bold))
        title.setStyleSheet('color: #2F4F4F; border-radius: 20px; padding: 20px 40px; background-color: Silver;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(title)
        top_layout.addStretch()
        music_btn = MusicButton()
        top_layout.addWidget(music_btn)
        back_btn = QPushButton()
        back_btn.setFixedSize(45, 45)
        back_btn.setIcon(QIcon(resource_path('icons/back.png')))
        back_btn.setIconSize(QSize(25, 25))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                border: 3px solid black;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
        """)
        back_btn.clicked.connect(self.close)
        top_layout.addWidget(back_btn)
        top_layout.setContentsMargins(20, 20, 20, 0)
        main_layout.addLayout(top_layout)
        main_layout.addSpacing(30)
        difficulties_layout = QHBoxLayout()
        difficulties_layout.setSpacing(20)
        
        difficulties = {'3x3': 3, '4x4': 4, '6x6': 6}
        button_style = """
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                font-family: 'Georgia';
                font-size: 26px;
                border: 4px solid black;
                border-radius: 20px;
                padding: 15px 30px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
        """
        difficulties_layout.addStretch()
        for text, size in difficulties.items():
            btn = QPushButton(text)
            btn.setStyleSheet(button_style)
            btn.clicked.connect(lambda checked, s=size: self.start_game(s))
            difficulties_layout.addWidget(btn)
        difficulties_layout.addStretch()
        main_layout.addLayout(difficulties_layout)
        main_layout.addStretch()
    def start_game(self, grid_size):
        self.game_window = GameWindow(self.image_path, grid_size)
        self.game_window.show()
        self.close()
    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)
class BaseThemeWindow(QWidget):
    def __init__(self, title, folder_name):
        super().__init__()
        self.title = title
        self.folder_name = folder_name
        self.initUI()
        self.center_window()
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setFixedSize(1000, 500)
        self.setStyleSheet('background-color: LightSlateGray;')
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        top_layout = QHBoxLayout()
        title = QLabel(self.title)
        title.setFont(QFont('Georgia', 32, QFont.Weight.Bold))
        title.setStyleSheet('color: #2F4F4F; border-radius: 20px; padding: 40px 60px; background-color: Silver;')
        title.setContentsMargins(20, 10, 20, 10)
        top_layout.addWidget(title)
        top_layout.addStretch()
        music_btn = MusicButton()
        top_layout.addWidget(music_btn)
        back_btn = QPushButton()
        back_btn.setFixedSize(45, 45)
        back_btn.setIcon(QIcon(resource_path('icons/back.png')))
        back_btn.setIconSize(QSize(25, 25))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                border: 3px solid black;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
        """)
        back_btn.clicked.connect(self.close)
        top_layout.addWidget(back_btn)
        top_layout.setContentsMargins(20, 20, 20, 0)
        main_layout.addLayout(top_layout)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        folder_path = resource_path(self.folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        image_files = [f for f in os.listdir(folder_path) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        button_style = """
            QPushButton {
                background-color: Silver;
                border: 3px solid #2F4F4F;
                border-radius: 15px;
            }
            QPushButton:hover {
                border: 4px solid #008080;
            }
        """

        for i in range(6):
            btn = QPushButton()
            btn.setFixedSize(200, 150)
            btn.setStyleSheet(button_style)

            if i < len(image_files):
                img_path = os.path.join(folder_path, image_files[i])
                pixmap = QPixmap(img_path)
                scaled_pixmap = pixmap.scaled(
                    190, 140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                btn.setIcon(QIcon(scaled_pixmap))
                btn.setIconSize(QSize(190, 140))
                btn.clicked.connect(lambda checked, path=img_path: self.show_difficulty_window(path))
            else:
                btn.setText("Нет изображения")
                btn.setStyleSheet(button_style + """
                    QPushButton {
                        color: #2F4F4F;
                        font-family: 'Georgia';
                        font-size: 16px;
                    }
                """)
            row = i // 3
            col = i % 3
            grid_layout.addWidget(btn, row, col)
        main_layout.addLayout(grid_layout)
        main_layout.addStretch()

    def show_difficulty_window(self, image_path):
        self.difficulty_window = DifficultyWindow(image_path)
        self.difficulty_window.show()

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

class LandscapeWindow(BaseThemeWindow):
    def __init__(self):
        super().__init__('ПЕЙЗАЖ', 'landscape')

class ArchitectureWindow(BaseThemeWindow):
    def __init__(self):
        super().__init__('АРХИТЕКТУРА', 'architecture')

class AnimalsWindow(BaseThemeWindow):
    def __init__(self):
        super().__init__('ЖИВОТНЫЕ', 'animals')

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        # Запускаем музыку при старте приложения
        music_player.play()
        self.center_window()

    def initUI(self):
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        music_btn = MusicButton()
        top_layout.addWidget(music_btn)
        exit_btn = QPushButton()
        exit_btn.setFixedSize(45, 45)
        exit_btn.setIcon(QIcon(resource_path('icons/exit.png')))
        exit_btn.setIconSize(QSize(25, 25))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                border: 3px solid black;
                border-radius: 22px;
            }
            QPushButton:hover {
                background-color:rgb(175, 62, 62);
            }
        """)
        exit_btn.clicked.connect(QApplication.quit)
        top_layout.addWidget(exit_btn)
        self.setWindowTitle('Пазлы')
        self.setFixedSize(1000, 500)
        self.setStyleSheet('background-color: LightSlateGray;')
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.addLayout(top_layout)
        main_layout.addSpacing(30)
        title = QLabel('СОБЕРИ ПАЗЛ')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Georgia', 36, QFont.Weight.Bold))
        title.setStyleSheet('color: #2F4F4F; margin: 20px;border-radius: 20px;padding: 20px 20px;min-width: 1px;background-color: Silver;')
        main_layout.addWidget(title)
        main_layout.addSpacing(70)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(25)
        button_style = """
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                font-family: 'Georgia';
                font-size: 28px;
                border: 4px solid black;
                border-radius: 20px;
                padding: 30px 60px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
        """
        self.landscape_btn = QPushButton('пейзаж')
        self.landscape_btn.setStyleSheet(button_style)
        self.landscape_btn.clicked.connect(self.show_landscape_window)
        buttons_layout.addWidget(self.landscape_btn)
        self.architecture_btn = QPushButton('архитектура')
        self.architecture_btn.setStyleSheet(button_style)
        self.architecture_btn.clicked.connect(self.show_architecture_window)
        buttons_layout.addWidget(self.architecture_btn)
        self.animals_btn = QPushButton('животные')
        self.animals_btn.setStyleSheet(button_style)
        self.animals_btn.clicked.connect(self.show_animals_window)
        buttons_layout.addWidget(self.animals_btn)
        buttons_layout.addStretch()
        buttons_layout.insertStretch(0)
        main_layout.addLayout(buttons_layout)
        main_layout.addStretch()
    def show_landscape_window(self):
        self.landscape_window = LandscapeWindow()
        self.landscape_window.show()
    def show_architecture_window(self):
        self.architecture_window = ArchitectureWindow()
        self.architecture_window.show()
    def show_animals_window(self):
        self.animals_window = AnimalsWindow()
        self.animals_window.show()
    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
