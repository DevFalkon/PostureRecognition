import random
import cv2
from PySide6.QtCore import QThread, QObject, Signal, Slot, Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QProgressBar,
    QSplitter,
)
from frontend.ui.helpers import bgr_to_pixmap, get_available_cameras
from frontend.widgets.widget_formatter import create_bordered_section


class CameraWorker(QObject):
    """Runs video capture and pose inference in a background thread."""

    frame_processed = Signal(object, bool, float)

    def __init__(self, pose_service):
        super().__init__()
        self.pose_service = pose_service
        self.cap = None
        self.running = False
        self.camera_index = 0
        self.target_angles = None

    @Slot()
    def start_stream(self):
        self.running = True
        backend = cv2.CAP_DSHOW if cv2.os.name == "nt" else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(self.camera_index, backend)
        
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)

        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                continue

            # Heavy MediaPipe processing runs here in the background thread
            processed_frame, is_match, similarity_score = (
                self.pose_service.process_stream_frame(
                    frame, self.target_angles
                )
            )

            # Cast NumPy types to Python primitives for PySide signal safety
            is_match = bool(is_match)
            similarity_score = float(similarity_score)

            # Draw match overlay on frame if matched
            if is_match:
                cv2.putText(
                    processed_frame,
                    "MATCH DETECTED!",
                    (40, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0, 255, 0),
                    3,
                )

            # Safely emit results to GUI thread
            self.frame_processed.emit(
                processed_frame, is_match, similarity_score
            )

    def set_camera_index(self, index: int):
        self.camera_index = index

    def set_target_angles(self, angles: dict):
        self.target_angles = angles

    def stop_stream(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None


class GameTab(QWidget):
    def __init__(self, storage_service: object, pose_service: object):
        super().__init__()
        self.storage_service = storage_service
        self.pose_service = pose_service
        self.pose_library = storage_service.pose_library

        self.score = 0
        self.current_target = None
        self.match_cooldown = False
        self.current_camera_index = 0
        self.cameras_populated = False
        self._image_cache = {}  # Cache loaded target images

        # Threading Setup
        self.worker_thread = None
        self.worker = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top Bar
        top_bar = QHBoxLayout()
        self.score_label = QLabel("Score: 0")
        self.score_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2e7d32;")

        self.target_name_label = QLabel("Target: Load poses in Training tab!")
        self.target_name_label.setStyleSheet("font-size: 14px;")

        self.camera_selector = QComboBox()
        self.camera_selector.addItem("📷 Default Camera (0)", userData=0)
        self.camera_selector.currentIndexChanged.connect(self.change_camera)

        self.next_btn = QPushButton("Next Pose / Start")
        self.next_btn.clicked.connect(self.pick_random_pose)

        top_bar.addWidget(self.score_label)
        top_bar.addWidget(self.target_name_label)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Camera:"))
        top_bar.addWidget(self.camera_selector)
        top_bar.addWidget(self.next_btn)

        # Progress Bar
        similarity_layout = QHBoxLayout()
        similarity_layout.addWidget(QLabel("Pose Match Similarity:"))
        self.similarity_bar = QProgressBar()
        self.similarity_bar.setRange(0, 100)
        self.similarity_bar.setValue(0)
        self.similarity_bar.setTextVisible(True)
        self.similarity_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #444;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #f44336;
                border-radius: 4px;
            }
            """
        )
        similarity_layout.addWidget(self.similarity_bar)

        # Splitter Section
        self.splitter = QSplitter(Qt.Horizontal)

        self.target_image_label = QLabel("No pose selected")
        self.target_image_label.setAlignment(Qt.AlignCenter)
        self.target_image_label.setStyleSheet(
            "background-color: #1e1e1e; color: #888; border-radius: 4px;"
        )
        self.target_image_label.setMinimumSize(320, 240)
        left_section = create_bordered_section("Target Pose to Match:", self.target_image_label)

        self.camera_label = QLabel("Camera Offline")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet(
            "background-color: #1e1e1e; color: #888; border-radius: 4px;"
        )
        self.camera_label.setMinimumSize(320, 240)
        right_section = create_bordered_section("Live Camera Stream:", self.camera_label)

        self.splitter.addWidget(left_section)
        self.splitter.addWidget(right_section)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        layout.addLayout(top_bar)
        layout.addLayout(similarity_layout)
        layout.addWidget(self.splitter, stretch=1)
        self.setLayout(layout)

    def start_camera(self):
        if self.worker_thread is not None and self.worker_thread.isRunning():
            return

        self.worker_thread = QThread()
        self.worker = CameraWorker(self.pose_service)
        self.worker.set_camera_index(self.current_camera_index)

        if self.current_target:
            self.worker.set_target_angles(self.current_target.get("angles"))

        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.start_stream)
        self.worker.frame_processed.connect(self.on_frame_processed)

        self.worker_thread.start()

        if self.current_target is None and len(self.pose_library) > 0:
            self.pick_random_pose()

    def stop_camera(self):
        if self.worker:
            self.worker.stop_stream()
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None

    def change_camera(self, combo_index: int):
        idx = self.camera_selector.itemData(combo_index)
        if idx is not None and idx != self.current_camera_index:
            self.current_camera_index = idx
            is_running = self.worker_thread and self.worker_thread.isRunning()
            if is_running:
                self.stop_camera()
                self.start_camera()

    def pick_random_pose(self):
        if not self.pose_library:
            self.target_name_label.setText("Target: Add poses in Training tab first!")
            return

        self.current_target = random.choice(self.pose_library)
        self.target_name_label.setText(f"Target: {self.current_target['name']}")
        self.match_cooldown = False

        if self.worker:
            self.worker.set_target_angles(self.current_target.get("angles"))

        target_path = self.current_target.get("path")
        if target_path:
            # Cache image reads to avoid blocking disk I/O
            if target_path not in self._image_cache:
                self._image_cache[target_path] = cv2.imread(target_path)

            img = self._image_cache.get(target_path)
            if img is not None:
                pixmap = bgr_to_pixmap(
                    img,
                    self.target_image_label.width(),
                    self.target_image_label.height(),
                )
                self.target_image_label.setPixmap(pixmap)

    @Slot(object, bool, float)
    def on_frame_processed(
        self, processed_frame, is_match: bool, similarity_score: float = 0.0
    ):
        # Update progress bar style only when color threshold changes
        color = "#4caf50" if similarity_score >= 80 else ("#ff9800" if similarity_score >= 50 else "#f44336")
        if getattr(self, "_last_bar_color", None) != color:
            self._last_bar_color = color
            self.similarity_bar.setStyleSheet(
                f"""
                QProgressBar {{
                    border: 1px solid #444;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #1e1e1e;
                    color: white;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 4px;
                }}
                """
            )

        self.similarity_bar.setValue(int(similarity_score))

        # Handle match scoring — increment score, but DO NOT auto-advance
        if is_match and not self.match_cooldown:
            self.score += 1
            self.score_label.setText(f"Score: {self.score}")
            self.match_cooldown = True
            # Removed: QTimer.singleShot(1500, self.pick_random_pose)

        # Render frame on GUI thread
        pixmap = bgr_to_pixmap(
            processed_frame,
            self.camera_label.width(),
            self.camera_label.height(),
        )
        self.camera_label.setPixmap(pixmap)