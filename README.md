# Pose Matching Game & Trainer

An interactive Desktop Application built with PySide6, OpenCV, and MediaPipe. The app captures pose keypoints via your webcam, compares your body posture in real-time against target pose images using vector angle matching, and scores your accuracy.

## Getting Started

- PrerequisitesPython 3.9+ installed on your system.
- A working webcam.

### Installation & Setup

#### Windows

1. Clone or download this repository and open a terminal in the project directory.
2. Create a virtual environment:

```bash
python -m venv env
```

3. Activate the virtual environment:

```bash
env\Scripts\activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run the application:

```bash
python app.py
```

## Key Features

- **Real-time Pose Matching:** Live feedback with progress bar similarity scoring ($0–100\%$).<br><br>
- **Pose Training Mode:** Upload custom target pose images to extract and store landmark joint angles.<br><br>
- **Non-Blocking Multi-threaded UI:** Dedicated background camera worker ensuring $60\text{ FPS}$ UI responsiveness.<br><br>
- **Smart Landmark Filtering:** Excludes facial keypoints to focus purely on full-body posture accuracy.<br><br>
- **8-Joint Positional Vector Matching:** Evaluates both limb bend angles and limb orientation relative to the torso.<br><br>

## Architecture & Project Structure

The application follows a modular, decoupled architecture separating the GUI presentation layer, multi-threaded worker pipeline, data storage, and core pose computer-vision engine.

```
├── app.py                # Entry point & MainWindow controller
├── requirements.txt      # Python dependency list
├── frontend/             # UI Presentation Layer (PySide6)
│ ├── ui/
│ │ ├── game_tab.py       # Live gameplay interface & QThread worker
│ │ ├── training_tab.py   # Image upload & pose creation UI
│ │ └── helpers.py        # OpenCV frame -> QPixmap utility converters
│ ├── widgets/            # Custom Qt components (splitters, containers)
│ └── theme/              # Common theme manager for all ui components
└── backend/              # Core Business Logic Layer
  ├── pose_service.py     # MediaPipe pipeline & vector angle math
  └── storage_service.py  # Pose library storage & persistence
```

## Core Components Explained

### 1. Background Video Pipeline (CameraWorker & QThread)

To prevent the main Qt GUI thread from freezing during heavy ML inference:

- OpenCV image capture (cv2.VideoCapture) and MediaPipe inference run inside a background thread (QThread).
- Processed frames and calculated metrics are sent back to the main UI thread safely using Qt Signals and Slots (frame_processed).

### 2. Pose Inference & Angle Engine (PoseService)

- **Landmark Detection:** Leverages mediapipe.solutions.pose to detect 33 3D body keypoints.
- **Face Filtering:** Maps facial keypoints (indices $0–10$) to zero radius, suppressing clutter so visual focus remains on body alignment.
- **Angle Calculation:** Calculates 2D spatial angles using inverse tangent vector math:

  $$\theta = \vert{}\arctan2(C_y - B_y, C_x - B_x) - \arctan2(A_y - B_y, A_x - B_x)\vert{}$$

- **8-Joint Comparison Matrix:** Measures both joint flex and body-relative position across 8 key angles:
  1. **Elbows (L/R):** Shoulder → Elbow → Wrist
  2. **Knees (L/R):** Hip → Knee → Ankle
  3. **Shoulders (L/R):** Hip → Shoulder → Elbow (distinguishes raised vs. lowered arms)
  4. **Hips (L/R):** Shoulder → Hip → Knee (distinguishes standing vs. crouching/bending)

## Dependencies

- **PySide6** — Modern Qt GUI Framework
- **OpenCV (opencv-python)** — Real-time computer vision & video streaming
- **MediaPipe** — On-device ML body posture keypoint tracking
- **NumPy** — High-performance vector geometry calculation
