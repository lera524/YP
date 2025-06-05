import sys
import os
import json
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
    QPointF, QRectF, QObject
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QTimer

class MusicPlayer:
    def __init__(self):
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.current_track = 0
        self.is_playing = False
        self.playlist = []
        self.load_playlist()
        
        # Подключаем сигнал окончания воспроизведения
        self.player.mediaStatusChanged.connect(self.handle_media_status_changed)
        
    def load_playlist(self):
        # Загружаем все музыкальные файлы из папки songs
        if not os.path.exists('songs'):
            os.makedirs('songs')
        
        self.playlist = [os.path.join('songs', f) for f in os.listdir('songs')
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
            
    def handle_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Переходим к следующему треку
            self.current_track = (self.current_track + 1) % len(self.playlist)
            self.play_current_track()
            
    def stop(self):
        self.is_playing = False
        self.player.stop()
        
    def toggle(self):
        if self.is_playing:
            self.stop()
        else:
            self.play()
            
    def set_volume(self, volume):
        self.audio_output.setVolume(volume / 100.0)

# Глобальный объект для управления музыкой
music_player = MusicPlayer()

class MusicButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(45, 45)
        self.setIcon(QIcon('icons/music_note.png'))
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
        music_player.toggle()
        # Синхронизируем состояние всех кнопок музыки
        for window in QApplication.topLevelWidgets():
            for button in window.findChildren(MusicButton):
                button.setChecked(music_player.is_playing)

class PuzzlePiece(QGraphicsPixmapItem):
    def __init__(self, pixmap, correct_pos, piece_id, game_window, parent=None):
        # Инициализация базового класса QGraphicsPixmapItem
        super().__init__(pixmap, parent)
        
        # Сохраняем исходное изображение фрагмента
        self.original_pixmap = pixmap
        self.piece_pixmap = pixmap
        
        # Сохраняем правильную позицию фрагмента на игровом поле
        self.correct_pos = correct_pos
        
        # Уникальный идентификатор фрагмента
        self.piece_id = piece_id
        
        # Ссылка на главное окно игры
        self.game_window = game_window
        
        # Флаги состояния фрагмента
        self.dragging = False  # Перетаскивается ли фрагмент
        self.is_placed = False  # Находится ли фрагмент на своем месте
        
        # Смещение курсора при перетаскивании
        self.offset = QPointF()
        
        # Множество связанных фрагментов (соединенных с текущим)
        self.connected_pieces = set()
        
        # Масштаб фрагмента (используется для эффекта при наведении)
        self._scale = 1.0
        
        # Настройка взаимодействия с фрагментом
        self.setAcceptHoverEvents(True)  # Разрешаем события наведения мыши
        self.setCursor(Qt.CursorShape.OpenHandCursor)  # Устанавливаем курсор
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable)  # Разрешаем перемещение
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)  # Разрешаем выделение
        
        # Установка начальной позиции и слоя
        self.setPos(correct_pos)
        self.setZValue(1)  # Z-индекс определяет, какой фрагмент будет отображаться поверх других

    def hoverEnterEvent(self, event):
        """Обработка события наведения курсора на фрагмент"""
        if not self.is_placed:
            self.setScale(1.05)  # Увеличиваем размер фрагмента
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.setZValue(2)  # Поднимаем фрагмент над остальными

    def hoverLeaveEvent(self, event):
        """Обработка события ухода курсора с фрагмента"""
        if not self.is_placed:
            self.setScale(1.0)  # Возвращаем исходный размер
            self.setZValue(1)

    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши"""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_placed:
            self.dragging = True
            self.offset = event.pos()  # Запоминаем позицию курсора относительно фрагмента
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.setZValue(3)  # Поднимаем фрагмент над всеми при перетаскивании
            
            # Поднимаем все связанные фрагменты
            for piece in self.connected_pieces:
                piece.setZValue(3)

    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши"""
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.setZValue(1)
            
            # Проверяем, можно ли соединить фрагмент с другими
            self.check_connection()

    def mouseMoveEvent(self, event):
        """Обработка перемещения мыши при перетаскивании"""
        if self.dragging and not self.is_placed:
            # Вычисляем новую позицию с учетом смещения курсора
            new_pos = self.mapToScene(event.pos() - self.offset)
            
            # Ограничиваем движение пределами сцены
            scene_rect = self.scene().sceneRect()
            new_pos.setX(max(0, min(new_pos.x(), scene_rect.width() - self.pixmap().width())))
            new_pos.setY(max(0, min(new_pos.y(), scene_rect.height() - self.pixmap().height())))
            
            # Перемещаем текущий фрагмент
            self.setPos(new_pos)
            
            # Перемещаем все связанные фрагменты
            delta = new_pos - self.pos()
            for piece in self.connected_pieces:
                new_piece_pos = piece.pos() + delta
                new_piece_pos.setX(max(0, min(new_piece_pos.x(), scene_rect.width() - piece.pixmap().width())))
                new_piece_pos.setY(max(0, min(new_piece_pos.y(), scene_rect.height() - piece.pixmap().height())))
                piece.setPos(new_piece_pos)
            
            # Проверяем близость к другим фрагментам
            self.check_nearby_pieces()

    def check_connection(self):
        """Проверка возможности соединения с другими фрагментами"""
        # Проверяем, находится ли фрагмент близко к своей правильной позиции
        current_pos = self.pos()
        distance_to_correct = (current_pos - self.correct_pos).manhattanLength()
        
        if distance_to_correct < 30:
            # Устанавливаем фрагмент точно на его место
            self.setPos(self.correct_pos)
            self.is_placed = True
            self.game_window.play_snap_sound()
            
            # Проверяем и соединяем с соседними фрагментами
            self.check_and_connect_neighbors()
            
            # Проверяем завершение пазла
            self.game_window.check_completion()
            return True
            
        # Если фрагмент не на своем месте, пробуем соединить с другими размещенными фрагментами
        return self.try_connect_to_placed_neighbors()

    def try_connect_to_placed_neighbors(self):
        """Попытка соединения с уже размещенными соседними фрагментами"""
        for piece in self.game_window.pieces:
            if piece != self and piece.is_placed and piece not in self.connected_pieces:
                if self.are_neighbors(piece):  # Если фрагменты должны быть соседями
                    distance = (self.pos() - piece.pos()).manhattanLength()
                    if distance < 30:  # Если фрагменты достаточно близко
                        # Определяем правильную позицию относительно соседнего фрагмента
                        if self.correct_pos.x() < piece.correct_pos.x():
                            target_pos = piece.pos() - QPointF(self.pixmap().width(), 0)
                        elif self.correct_pos.x() > piece.correct_pos.x():
                            target_pos = piece.pos() + QPointF(piece.pixmap().width(), 0)
                        elif self.correct_pos.y() < piece.correct_pos.y():
                            target_pos = piece.pos() - QPointF(0, self.pixmap().height())
                        else:
                            target_pos = piece.pos() + QPointF(0, piece.pixmap().height())

                        # Перемещаем фрагмент на позицию и соединяем
                        self.setPos(target_pos)
                        self.connect_with(piece)
                        self.game_window.play_snap_sound()
                        return True
        return False

    def check_nearby_pieces(self):
        """Проверка близости к другим фрагментам во время перетаскивания"""
        if self.is_placed:
            return
            
        for piece in self.game_window.pieces:
            if piece != self and piece not in self.connected_pieces:
                if self.are_neighbors(piece):
                    distance = (self.pos() - piece.pos()).manhattanLength()
                    if distance < 30:
                        self.snap_to_piece(piece)
                        return

    def snap_to_piece(self, other_piece):
        """Прикрепление фрагмента к другому фрагменту"""
        # Определяем правильную позицию относительно другого фрагмента
        if self.correct_pos.x() < other_piece.correct_pos.x():
            target_pos = other_piece.pos() - QPointF(self.pixmap().width(), 0)
        elif self.correct_pos.x() > other_piece.correct_pos.x():
            target_pos = other_piece.pos() + QPointF(other_piece.pixmap().width(), 0)
        elif self.correct_pos.y() < other_piece.correct_pos.y():
            target_pos = other_piece.pos() - QPointF(0, self.pixmap().height())
        else:
            target_pos = other_piece.pos() + QPointF(0, other_piece.pixmap().height())

        # Перемещаем фрагмент и соединяем
        self.setPos(target_pos)
        self.connect_with(other_piece)
        self.game_window.play_snap_sound()

    def check_and_connect_neighbors(self):
        """Проверка и соединение с соседними фрагментами"""
        for piece in self.game_window.pieces:
            if piece != self and piece.is_placed and piece not in self.connected_pieces:
                if self.are_neighbors(piece):
                    distance = (self.pos() - piece.pos()).manhattanLength()
                    if distance < 30:
                        self.connect_with(piece)
                        piece.check_and_connect_neighbors()

    def connect_with(self, other_piece):
        """Соединение фрагмента с другим фрагментом"""
        if other_piece not in self.connected_pieces:
            # Объединяем все связанные фрагменты из обеих групп
            all_connected = self.connected_pieces | other_piece.connected_pieces | {self, other_piece}
            # Обновляем связи для всех фрагментов
            for piece in all_connected:
                piece.connected_pieces = all_connected - {piece}
                piece.is_placed = True
                piece.setZValue(1)
            
            # Проверяем завершение пазла
            self.game_window.check_completion()

    def are_neighbors(self, other_piece):
        """Проверка, должны ли фрагменты быть соседями в собранном пазле"""
        dx = abs(self.correct_pos.x() - other_piece.correct_pos.x())
        dy = abs(self.correct_pos.y() - other_piece.correct_pos.y())
        piece_size = self.pixmap().width()
        # Фрагменты соседние, если находятся рядом по горизонтали или вертикали
        return (dx == piece_size and dy == 0) or (dx == 0 and dy == piece_size)

class PuzzleGroup:
    def __init__(self, pieces):
        self.pieces = pieces
        for p in pieces:
            p.group = self

    def move_group(self, moved_piece, delta):
        for p in self.pieces:
            if p != moved_piece:
                new_pos = p.pos() + delta
                # Ограничиваем движение группы в пределах окна
                parent_rect = moved_piece.parent().rect()
                new_pos.setX(max(0, min(new_pos.x(), parent_rect.width() - p.width())))
                new_pos.setY(max(0, min(new_pos.y(), parent_rect.height() - p.height())))
                p.move(new_pos)

    def merge_with(self, other_group):
        if other_group != self:
            self.pieces.extend(other_group.pieces)
            for piece in other_group.pieces:
                piece.group = self

class GameField(QFrame):
    def __init__(self, width, height, grid_size, is_puzzle_field=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.grid_size = grid_size
        self.cell_width = width // grid_size
        self.cell_height = height // grid_size
        self.is_puzzle_field = is_puzzle_field
        
        # Устанавливаем стиль в зависимости от типа поля
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
            
            # Рисуем фоновое изображение с низкой непрозрачностью
            if hasattr(self, 'background_image'):
                painter.setOpacity(0.2)
                painter.drawPixmap(self.rect(), self.background_image)
                painter.setOpacity(1.0)

            # Рисуем сетку
            pen = QPen(QColor("#CCCCCC"))
            pen.setWidth(1)
            painter.setPen(pen)

            # Рисуем горизонтальные линии сетки
            for i in range(1, self.grid_size):
                y = i * self.cell_height
                painter.drawLine(0, y, self.width(), y)

            # Рисуем вертикальные линии сетки
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
        
        # Initialize timer variables
        self.elapsed_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        # Scale image
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
        
        # Загружаем сохраненное состояние после создания scaled_image
        self.load_saved_state()
        self.initUI()
        
        # Load snap sound
        self.snap_player = QMediaPlayer()
        self.snap_audio = QAudioOutput()
        self.snap_player.setAudioOutput(self.snap_audio)
        if os.path.exists('sounds/snap.mp3'):
            self.snap_player.setSource(QUrl.fromLocalFile(os.path.abspath('sounds/snap.mp3')))
            
        # Start the timer when the game begins
        self.timer.start(1000)  # Update every second

    def update_timer(self):
        """Update the timer display"""
        if not self.is_completed:
            self.elapsed_time += 1
            minutes = self.elapsed_time // 60
            seconds = self.elapsed_time % 60
            self.timer_label.setText(f"Время: {minutes:02d}:{seconds:02d}")

    def initUI(self):
        self.setWindowTitle('Собери пазл')
        
        # Устанавливаем минимальный размер окна
        self.setMinimumSize(800, 600)
        
        # Set window size with ability to resize
        window_width = max(800, self.scaled_image.width() + 300)
        window_height = max(600, self.scaled_image.height() + 200)
        self.resize(window_width, window_height)
        self.setStyleSheet('background-color: LightSlateGray;')

        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        self.setLayout(main_layout)

        # Left panel for preview and controls
        left_panel = QVBoxLayout()
        
        # Add timer label
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
        
        # Preview image
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

        # Control buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_in_btn = QPushButton('+')
        zoom_out_btn = QPushButton('-')
        reset_zoom_btn = QPushButton('⟲')
        
        for btn in [zoom_in_btn, zoom_out_btn, reset_zoom_btn]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2F4F4F;
                    color: white;
                    border: 2px solid black;
                    border-radius: 20px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #008080;
                }
            """)
            zoom_layout.addWidget(btn)
        
        zoom_in_btn.clicked.connect(lambda: self.zoom(1.2))
        zoom_out_btn.clicked.connect(lambda: self.zoom(0.8))
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        
        buttons_layout.addLayout(zoom_layout)

        # Add existing buttons
        music_btn = MusicButton()
        buttons_layout.addWidget(music_btn)

        # Reset progress button
        reset_btn = QPushButton("Начать сначала")
        reset_btn.setFixedSize(150, 40)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F4F4F;
                color: #FFE4E1;
                border: 3px solid black;
                border-radius: 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #CD5C5C;
            }
        """)
        reset_btn.clicked.connect(self.confirm_reset)
        buttons_layout.addWidget(reset_btn)

        back_btn = QPushButton()
        back_btn.setFixedSize(45, 45)
        back_btn.setIcon(QIcon('icons/back.png'))
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
        back_btn.clicked.connect(self.handle_back)
        buttons_layout.addWidget(back_btn)

        hint_btn = QPushButton('Подсказка')
        hint_btn.setStyleSheet(back_btn.styleSheet())
        hint_btn.setFixedSize(100, 40)
        hint_btn.setCheckable(True)
        hint_btn.clicked.connect(self.toggle_hint)
        buttons_layout.addWidget(hint_btn)

        # Add help text
        help_text = QLabel(
            "Управление:\n"
            "• Левая кнопка мыши - перетаскивание\n"
            "• + / - - масштабирование\n"
            "• ⟲ - сброс масштаба\n"
            "• Фрагменты автоматически\n  соединяются при сближении"
        )
        help_text.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                padding: 10px;
                background-color: #2F4F4F;
                border-radius: 10px;
            }
        """)
        help_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        buttons_layout.addWidget(help_text)

        left_panel.addLayout(buttons_layout)
        left_panel.addStretch()
        main_layout.addLayout(left_panel)

        # Create graphics view for puzzle area
        self.view = QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setMinimumSize(500, 400)
        
        # Разрешаем изменение размера QGraphicsView
        size_policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.setSizePolicy(size_policy)
        
        self.view.setStyleSheet("""
            QGraphicsView {
                background-color: white;
                border: 4px solid #2F4F4F;
                border-radius: 10px;
            }
        """)
        
        # Set scene size
        self.scene.setSceneRect(QRectF(0, 0, self.scaled_image.width(), self.scaled_image.height()))
        
        # Add view to layout
        main_layout.addWidget(self.view)
        
        # Initialize puzzle pieces
        self.initialize_puzzle()

    def zoom(self, factor):
        """Масштабирование игрового поля"""
        self.zoom_factor *= factor
        self.view.scale(factor, factor)

    def reset_zoom(self):
        """Сброс масштаба к исходному значению"""
        self.view.resetTransform()
        self.zoom_factor = 1.0

    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
        # Обновляем размер сцены при изменении размера окна
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        # Восстанавливаем текущий масштаб
        self.view.scale(self.zoom_factor, self.zoom_factor)

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
        if not self.load_saved_state():
            # Если нет сохраненного состояния, создаем новую игру
            self.create_new_puzzle()

    def create_new_puzzle(self):
        # Piece dimensions
        piece_width = self.scaled_image.width() // self.grid_size
        piece_height = self.scaled_image.height() // self.grid_size

        # Calculate margins for piece distribution
        margin_x = 50
        margin_y = 50
        available_width = self.width() - self.scaled_image.width() - margin_x * 2
        available_height = self.height() - margin_y * 2

        # Create list of possible positions for pieces
        field_positions = []
        rows = (available_height // piece_height) + 1
        cols = (available_width // piece_width) + 1
        
        for row in range(rows):
            for col in range(cols):
                x = margin_x + col * (piece_width + 10)  # Add 10px spacing between pieces
                y = margin_y + row * (piece_height + 10)
                if x + piece_width < self.width() and y + piece_height < self.height():
                    field_positions.append(QPointF(x, y))

        # Shuffle positions
        random.shuffle(field_positions)

        # Create puzzle pieces
        for row in range(self.grid_size):
            for col in range(self.grid_size):
                # Cut out piece from image
                piece_rect = QRect(
                    col * piece_width,
                    row * piece_height,
                    piece_width,
                    piece_height
                )
                piece_pixmap = self.scaled_image.copy(piece_rect)
                
                # Correct position on game field
                correct_pos = QPointF(
                    col * piece_width,
                    row * piece_height
                )
                
                # Create piece
                piece = PuzzlePiece(
                    piece_pixmap,
                    correct_pos,
                    len(self.pieces),
                    self
                )
                
                # Add piece to scene
                self.scene.addItem(piece)
                
                # Place at random position
                pos_index = row * self.grid_size + col
                if pos_index < len(field_positions):
                    piece.setPos(field_positions[pos_index])
                
                self.pieces.append(piece)

    def check_completion(self):
        """Проверка завершения сборки пазла"""
        # Проверяем, все ли фрагменты на своих местах
        if not self.is_completed and all(piece.is_placed and 
            (piece.pos() - piece.correct_pos).manhattanLength() < 1 for piece in self.pieces):
            self.is_completed = True
            # Stop the timer when puzzle is completed
            self.timer.stop()
            self.save_state()  # Сохраняем состояние
            self.show_completion_message()

    def show_completion_message(self):
        """Показ сообщения о завершении сборки пазла"""
        # Создаем диалоговое окно
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Поздравляю!")
        minutes = self.elapsed_time // 60
        seconds = self.elapsed_time % 60
        dialog.setText(f"Пазл собран!\nВремя сборки: {minutes:02d}:{seconds:02d}")
        dialog.setIcon(QMessageBox.Icon.Information)
        
        # Устанавливаем стиль для диалогового окна
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

        # Добавляем кнопки
        restart_button = dialog.addButton("Собрать заново", QMessageBox.ButtonRole.ActionRole)
        back_button = dialog.addButton("Назад", QMessageBox.ButtonRole.RejectRole)
        
        # Показываем диалог и обрабатываем ответ
        dialog.exec()
        
        # Обрабатываем нажатие кнопок
        if dialog.clickedButton() == restart_button:
            self.restart_game()
        elif dialog.clickedButton() == back_button:
            self.close()

    def restart_game(self):
        """Перезапуск игры"""
        # Удаляем все фрагменты
        for piece in self.pieces:
            self.scene.removeItem(piece)
        self.pieces.clear()
        
        # Сбрасываем флаг завершения
        self.is_completed = False
        
        # Сбрасываем масштаб
        self.reset_zoom()
        
        # Создаем новую игру
        self.create_new_puzzle()

    def save_state(self):
        # Сохраняем состояние игры
        state = {
            'grid_size': self.grid_size,
            'image_path': self.image_path,
            'pieces': [
                {
                    'id': piece.piece_id,
                    'pos': (piece.pos().x(), piece.pos().y()),
                    'is_placed': piece.is_placed,
                    'connected_pieces': [p.piece_id for p in piece.connected_pieces]
                }
                for piece in self.pieces
            ]
        }
        
        with open('puzzle_state.json', 'w') as f:
            json.dump(state, f)

    def load_saved_state(self):
        try:
            with open('puzzle_state.json', 'r') as f:
                state = json.load(f)
                
            # Проверяем, соответствует ли сохранение текущей игре
            if state['grid_size'] != self.grid_size or \
               state['image_path'] != self.image_path:
                return False
                
            # Создаем фрагменты и восстанавливаем их состояние
            piece_width = self.scaled_image.width() // self.grid_size
            piece_height = self.scaled_image.height() // self.grid_size

            # Создаем словарь для хранения состояний фрагментов
            piece_states = {ps['id']: ps for ps in state['pieces']}
            
            # Создаем все фрагменты в правильном порядке
            for piece_id in range(len(state['pieces'])):
                row = piece_id // self.grid_size
                col = piece_id % self.grid_size
                
                # Вырезаем фрагмент изображения
                piece_rect = QRect(
                    col * piece_width,
                    row * piece_height,
                    piece_width,
                    piece_height
                )
                piece_pixmap = self.scaled_image.copy(piece_rect)
                
                # Правильная позиция на игровом поле
                correct_pos = QPointF(
                    col * piece_width,
                    row * piece_height
                )
                
                # Создаем фрагмент
                piece = PuzzlePiece(
                    piece_pixmap,
                    correct_pos,
                    piece_id,
                    self
                )
                
                # Устанавливаем позицию и состояние из сохранения
                piece_state = piece_states[piece_id]
                piece.setPos(QPointF(piece_state['pos'][0], piece_state['pos'][1]))
                piece.is_placed = piece_state['is_placed']
                
                # Добавляем фрагмент на сцену и в список
                self.scene.addItem(piece)
                self.pieces.append(piece)
            
            # После создания всех фрагментов восстанавливаем связи между ними
            for piece_id, piece_state in piece_states.items():
                piece = self.pieces[piece_id]
                piece.connected_pieces = {
                    self.pieces[pid] for pid in piece_state['connected_pieces']
                }
                
            return True
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return False

    def play_snap_sound(self):
        if self.snap_player.source().isValid():
            self.snap_player.setPosition(0)
            self.snap_player.play()
            
    def update_timer(self):
        """Update the timer display"""
        if not self.is_completed:
            self.elapsed_time += 1
            minutes = self.elapsed_time // 60
            seconds = self.elapsed_time % 60
            self.timer_label.setText(f"Время: {minutes:02d}:{seconds:02d}")

    def handle_back(self):
        """Автоматически сохраняем прогресс перед возвратом"""
        if not self.is_completed:
            self.save_state()
        self.close()

    def confirm_reset(self):
        """Показываем диалог подтверждения сброса прогресса"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Подтверждение")
        dialog.setText("Вы уверены, что хотите начать сначала?\nТекущий прогресс будет потерян.")
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Устанавливаем стиль для диалогового окна
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: LightSlateGray;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
                min-width: 200px;
            }
            QPushButton {
                background-color: #2F4F4F;
                color: white;
                border: 2px solid black;
                border-radius: 10px;
                padding: 5px 15px;
                font-size: 14px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #008080;
            }
        """)
        
        if dialog.exec() == QMessageBox.StandardButton.Yes:
            self.reset_progress()

    def reset_progress(self):
        """Сбрасываем прогресс и начинаем игру заново"""
        # Останавливаем и сбрасываем таймер
        self.timer.stop()
        self.elapsed_time = 0
        self.timer_label.setText("Время: 00:00")
        
        # Удаляем сохраненное состояние
        if os.path.exists('puzzle_state.json'):
            os.remove('puzzle_state.json')
        
        # Удаляем все фрагменты
        for piece in self.pieces:
            self.scene.removeItem(piece)
        self.pieces.clear()
        
        # Сбрасываем флаг завершения
        self.is_completed = False
        
        # Сбрасываем масштаб
        self.reset_zoom()
        
        # Создаем новую игру
        self.create_new_puzzle()
        
        # Запускаем таймер заново
        self.timer.start(1000)

class DifficultyWindow(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Выберите сложность')
        self.setFixedSize(1000, 500)
        self.setStyleSheet('background-color: LightSlateGray;')

        # Создаем главный layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Создаем верхний layout для заголовка и кнопок
        top_layout = QHBoxLayout()

        # Заголовок
        title = QLabel('Выберите сложность')
        title.setFont(QFont('Georgia', 32, QFont.Weight.Bold))
        title.setStyleSheet('color: #2F4F4F; border-radius: 20px; padding: 20px 40px; background-color: Silver;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_layout.addWidget(title)

        # Добавляем растяжку между заголовком и кнопками
        top_layout.addStretch()

        # Добавляем кнопку музыки
        music_btn = MusicButton()
        top_layout.addWidget(music_btn)

        # Кнопка "назад"
        back_btn = QPushButton()
        back_btn.setFixedSize(45, 45)
        back_btn.setIcon(QIcon('icons/back.png'))
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

        # Добавляем отступы для верхнего layout
        top_layout.setContentsMargins(20, 20, 20, 0)
        
        # Добавляем верхний layout в главный
        main_layout.addLayout(top_layout)

        # Добавляем отступ
        main_layout.addSpacing(30)

        # Создаем layout для кнопок сложности
        difficulties_layout = QHBoxLayout()
        difficulties_layout.setSpacing(20)

        # Кнопки сложности
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

        # Добавляем растяжку слева
        difficulties_layout.addStretch()

        for text, size in difficulties.items():
            btn = QPushButton(text)
            btn.setStyleSheet(button_style)
            btn.clicked.connect(lambda checked, s=size: self.start_game(s))
            difficulties_layout.addWidget(btn)

        # Добавляем растяжку справа
        difficulties_layout.addStretch()

        # Добавляем layout с кнопками в главный layout
        main_layout.addLayout(difficulties_layout)
        main_layout.addStretch()

    def start_game(self, grid_size):
        self.game_window = GameWindow(self.image_path, grid_size)
        self.game_window.show()
        self.close()

class BaseThemeWindow(QWidget):
    def __init__(self, title, folder_name):
        super().__init__()
        self.title = title
        self.folder_name = folder_name
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setFixedSize(1000, 500)
        self.setStyleSheet('background-color: LightSlateGray;')

        # Создаем главный layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Создаем верхний layout для заголовка и кнопок
        top_layout = QHBoxLayout()
        
        # Добавляем заголовок
        title = QLabel(self.title)
        title.setFont(QFont('Georgia', 32, QFont.Weight.Bold))
        title.setStyleSheet('color: #2F4F4F; border-radius: 20px; padding: 40px 60px; background-color: Silver;')
        title.setContentsMargins(20, 10, 20, 10)
        top_layout.addWidget(title)

        # Добавляем растяжку между заголовком и кнопками
        top_layout.addStretch()

        # Добавляем кнопку музыки
        music_btn = MusicButton()
        top_layout.addWidget(music_btn)

        # Добавляем кнопку "назад"
        back_btn = QPushButton()
        back_btn.setFixedSize(45, 45)
        back_btn.setIcon(QIcon('icons/back.png'))
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
        
        # Добавляем отступы для верхнего layout
        top_layout.setContentsMargins(20, 20, 20, 0)
        
        # Добавляем верхний layout в главный
        main_layout.addLayout(top_layout)

        # Добавляем сетку с изображениями
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        
        # Загружаем изображения из соответствующей папки
        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)

        image_files = [f for f in os.listdir(self.folder_name) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

        # Создаем кнопки с изображениями
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
                img_path = os.path.join(self.folder_name, image_files[i])
                pixmap = QPixmap(img_path)
                scaled_pixmap = pixmap.scaled(
                    190, 140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                btn.setIcon(QIcon(scaled_pixmap))
                btn.setIconSize(QSize(190, 140))
                # Сохраняем путь к изображению и привязываем обработчик
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

        # Добавляем сетку в главный layout
        main_layout.addLayout(grid_layout)
        main_layout.addStretch()

    def show_difficulty_window(self, image_path):
        self.difficulty_window = DifficultyWindow(image_path)
        self.difficulty_window.show()

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

    def initUI(self):
        # Создаем верхний layout для кнопок
        top_layout = QHBoxLayout()
        top_layout.addStretch()

        # Добавляем кнопку музыки
        music_btn = MusicButton()
        top_layout.addWidget(music_btn)

        # Добавляем кнопку выхода
        exit_btn = QPushButton()
        exit_btn.setFixedSize(45, 45)
        exit_btn.setIcon(QIcon('icons/exit.png'))
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

        # Настройка основного окна
        self.setWindowTitle('Пазлы')
        self.setFixedSize(1000, 500)
        self.setStyleSheet('background-color: LightSlateGray;')

        # Создаем главный вертикальный layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Добавляем layout с кнопкой музыки
        main_layout.addLayout(top_layout)

        # Добавляем отступ сверху
        main_layout.addSpacing(30)

        # Добавляем заголовок
        title = QLabel('СОБЕРИ ПАЗЛ')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont('Georgia', 36, QFont.Weight.Bold))
        title.setStyleSheet('color: #2F4F4F; margin: 20px;border-radius: 20px;padding: 20px 20px;min-width: 1px;background-color: Silver;')
        main_layout.addWidget(title)

        # Добавляем отступ между заголовком и кнопками
        main_layout.addSpacing(70)

        # Создаем горизонтальный layout для кнопок
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(25)  # Расстояние между кнопками
        
        # Стиль для кнопок
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

        # Создаем кнопки
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

        # Добавляем отступы по краям для кнопок
        buttons_layout.addStretch()
        buttons_layout.insertStretch(0)

        # Добавляем layout с кнопками в главный layout
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

