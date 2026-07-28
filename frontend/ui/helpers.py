import cv2
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QMediaDevices

def bgr_to_pixmap(bgr_img, max_w, max_h):
    h, w, ch = bgr_img.shape
    bytes_per_line = ch * w
    q_img = QImage(bgr_img.data, w, h, bytes_per_line, QImage.Format_BGR888)
    return QPixmap.fromImage(q_img).scaled(
        max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )

def get_available_cameras():
    cameras = []
    try:
        devices = QMediaDevices.videoInputs()
        for i, dev in enumerate(devices):
            name = dev.description() if dev.description() else f"Camera {i}"
            cameras.append((i, name))
    except Exception:
        pass
    if not cameras:
        cameras.append((0, "Camera 0"))
    return cameras