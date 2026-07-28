from PySide6.QtWidgets import QMainWindow, QTabWidget
from PySide6.QtCore import Signal

# Updated separate imports
from frontend.ui.training_tab import TrainingTab
from frontend.ui.game_tab import GameTab

from backend.pose_service import PoseService
from backend.storage_service import StorageService

class MainWindow(QMainWindow):
    image_processed = Signal(object, object, str)
    frame_processed = Signal(object, bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pose Matching Game")
        self.resize(1000, 750)

        self.pose_library = []
        self.processor = PoseService()

        self.storage_service = StorageService(self.pose_library)

        self.tabs = QTabWidget()
        self.training_tab = TrainingTab(self.storage_service)
        self.game_tab = GameTab(self.storage_service)

        self.tabs.addTab(self.training_tab, "1. Training (Upload Poses)")
        self.tabs.addTab(self.game_tab, "2. Game (Play)")

        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.handle_tab_change)

        self.wire_signals()

    def wire_signals(self):
        self.training_tab.request_process_image.connect(self.process_image_handler)
        self.game_tab.request_frame_process.connect(self.process_frame_handler)

        self.image_processed.connect(self.training_tab.on_image_processed)
        self.frame_processed.connect(self.game_tab.on_frame_processed)

    def process_image_handler(self, file_path):
        annotated_img, angles = self.processor.process_static_image(file_path)
        self.image_processed.emit(annotated_img, angles, file_path)

    def process_frame_handler(self, frame, target_angles):
        processed_frame, is_match = self.processor.process_stream_frame(frame, target_angles)
        self.frame_processed.emit(processed_frame, is_match)

    def handle_tab_change(self, index):
        if index == 1:
            self.game_tab.start_camera()
            if len(self.pose_library) > 0 and self.game_tab.current_target is None:
                self.game_tab.pick_random_pose()
        else:
            self.game_tab.stop_camera()

    def closeEvent(self, event):
        self.game_tab.stop_camera()
        self.processor.close()