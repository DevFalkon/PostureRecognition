from PySide6.QtWidgets import QMainWindow, QTabWidget
from PySide6.QtCore import Signal

# Frontend imports
from frontend.ui.training_tab import TrainingTab
from frontend.ui.game_tab import GameTab

# Backend Service imports
from backend.pose_service import PoseService
from backend.storage_service import StorageService


class MainWindow(QMainWindow):
    # (raw_img, annotated_img, angles, file_path)
    image_processed = Signal(object, object, object, str)
    # (processed_frame, is_match, similarity_score)
    frame_processed = Signal(object, bool, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pose Matching Game")
        self.resize(1000, 750)

        # 1. State & Services Setup
        self.pose_library = []
        self.pose_service = PoseService()
        self.storage_service = StorageService(self.pose_service, self.pose_library)

        # 2. UI Tabs Initialization (Both tabs get StorageService)
        self.tabs = QTabWidget()
        self.training_tab = TrainingTab(self.storage_service, self.pose_service)
        self.game_tab = GameTab(self.storage_service, self.pose_service)

        self.tabs.addTab(self.training_tab, "1. Training (Upload Poses)")
        self.tabs.addTab(self.game_tab, "2. Game (Play)")

        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.handle_tab_change)

        self.wire_signals()

    def wire_signals(self):
        self.training_tab.request_process_image.connect(self.process_image_handler)

        self.image_processed.connect(self.training_tab.on_image_processed)
        self.frame_processed.connect(self.game_tab.on_frame_processed)

    def process_image_handler(self, file_path: str):
        """Processes static image and returns (raw_img, annotated_img, angles)."""
        raw_img, annotated_img, angles = self.pose_service.process_static_image(file_path)
        self.image_processed.emit(raw_img, annotated_img, angles, file_path)

    def process_frame_handler(self, frame, target_angles: dict):
        """Processes video frame and calculates live pose match + similarity percentage."""
        processed_frame, is_match, similarity_score = self.pose_service.process_stream_frame(
            frame, target_angles
        )
        self.frame_processed.emit(processed_frame, is_match, similarity_score)

    def handle_tab_change(self, index: int):
        if index == 1:
            self.game_tab.start_camera()
            if len(self.pose_library) > 0 and self.game_tab.current_target is None:
                self.game_tab.pick_random_pose()
        else:
            self.game_tab.stop_camera()

    def closeEvent(self, event):
        self.game_tab.stop_camera()
        self.pose_service.close()
        super().closeEvent(event)