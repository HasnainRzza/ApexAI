# ApexAI: AI-Powered Exam Proctoring System

ApexAI is an advanced, lightweight, and real-time AI proctoring system designed to detect and prevent cheating during online exams. It runs entirely on the local machine (CPU-optimized) using a modular architecture to monitor visual, audio, and browser-based activities.

The system calculates a dynamic **Anomaly Score** in real-time, penalizing suspicious behavior. If the user repeatedly violates the rules, the system permanently flags the session as **CHEATING** and captures definitive photographic proof.

---

## Features & Modules

ApexAI consists of several independent monitoring modules that feed into a central scoring engine.

### 1. Face Tracking
* **Missing Face:** Detects if the student leaves the camera frame.
* **Multiple Faces:** Detects if a second person enters the frame to help the student.

### 2. Head Pose Estimation
* Tracks the user's head direction (`HEAD_CENTER`, `HEAD_LEFT`, `HEAD_RIGHT`, `HEAD_UP`, `HEAD_DOWN`).
* Instantly triggers a penalty if the user turns their head away from the screen.

### 3. Gaze Estimation (Eye Tracking)
* Precisely tracks iris movements to determine where the user is looking.
* **Smart 5-Second Rule:** To prevent false positives from natural eye darting, the system allows the user to look around briefly. However, if the eyes remain off-center for **more than 5 continuous seconds**, a heavy penalty is applied.

### 4. Object Detection (YOLOv8)
* Actively scans the environment for unauthorized items.
* Flags suspicious objects such as **Cell Phones, Books, Laptops, and Remotes**.

### 5. Audio Anomaly Detection (WebRTC VAD)
* Uses Voice Activity Detection to listen specifically for **human speech** (talking, whispering, humming).
* Highly sensitive to voices but intelligently ignores background noise like fans or keyboard typing.

### 6. Browser Monitoring
* Communicates with the exam frontend via WebSockets.
* Detects if the user switches tabs, minimizes the browser, or opens another application during the test.

### 7. Proof Capture (Screenshots)
* Features a 10-second startup grace period to allow the user to get settled.
* Automatically captures **one definitive screenshot** per severe violation type (e.g., pulling out a phone, leaving the tab, someone else entering the room).
* Screenshots are saved automatically in the `screenshots/` directory for review.

---

## The Scoring System (Temporal Engine)

ApexAI uses a stateful scoring engine to determine if a user is cheating. 

* **Scoring Weights:** Every anomaly carries a different weight (e.g., Head Pose = 25, Browser Violation = 25, Object Detected = 15).
* **Decay:** The score slowly decays back to 0 over time if the user behaves normally.
* **The "Two Strikes" Rule:** If the user's Anomaly Score spikes above **35.0**, it counts as a major infraction. If the score crosses above 35.0 **two times** during the session, the system officially locks the severity to **CHEATING DETECTED** and takes a final proof screenshot.

---

##  Configuration

All system parameters, thresholds, and penalty weights can be easily tuned in the `config.yaml` file without altering the codebase.

```yaml
# Example Configuration Snippet
temporal_engine:
  weights:
    face_missing: 10
    multiple_faces: 20
    head_pose_anomaly: 25
    gaze_anomaly: 5
    object_detected: 15
    audio_anomaly: 5
    browser_violation: 25
```

---

##  Installation & Usage

### 1. Requirements
* Python 3.8+
* A working webcam
* A microphone

### 2. Install Dependencies
Install the required Python packages (it is recommended to use a virtual environment):

```bash
pip install opencv-python numpy mediapipe ultralytics webrtcvad pyaudio websockets pyyaml
```

*(Note: Depending on your OS, installing `pyaudio` might require additional system dependencies like PyAudio wheels or PortAudio).*

### 3. Run the System
Start the main application to launch the webcam dashboard and background monitoring threads.

```bash
python main.py
```

### 4. Test the Browser Integration
To test the browser monitoring module, open the provided `frontend/index.html` file in your web browser while the Python script is running. Try minimizing the browser or switching tabs to see the penalty applied in real-time on your dashboard!

---

**Press `q` at any time to exit the ApexAI Dashboard.**
