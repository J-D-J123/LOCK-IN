# LOCK IN

> *Your phone is the enemy. This is the weapon.*

Most productivity tools ask nicely. LOCK IN does not ask. It watches your camera with a YOLOv8 AI model, and the moment it catches your phone in frame, the clock starts. Put it down in time and you are free. Hold it too long and your entire screen gets locked behind a fullscreen wall you cannot close, skip, or alt-F4 out of. Every single offence doubles the next lockdown. There is no reset button you can reach in time.

This is not an app that helps you be more mindful. It is a system that punishes you until the habit breaks.

Three components work together: a Python script that watches your webcam around the clock, a Chrome extension that kills distracting sites the instant a phone is spotted, and a motivational website that reminds you exactly what is at stake. Use one. Use all three. Either way, the phone goes down.

Contributions are welcome. If you want to improve detection accuracy, add new platforms, or build something on top of this, open an issue or send a pull request.

## What It Does

| Component | Description |
|---|---|
| **Python Phone Guard** | Runs your webcam through YOLOv8 AI. Detects your phone across multiple cameras simultaneously. Throws up a fullscreen lockdown overlay that blocks your entire screen. Every offence doubles the next lockdown. |
| **Chrome Extension** | Browser native phone detection using TensorFlow.js. Blocks YouTube, Instagram, Reddit, TikTok, Netflix and more the moment a phone is spotted. |
| **Motivational Website** | A fullscreen Three.js site with brutal quotes and a live seconds wasted counter. Open it and leave it running. |

## Folder Structure

```
LOCK-IN/
│
├── README.md
│
├── web/
│   ├── index.html              # Motivational site (Three.js galaxy + quotes)
│   ├── detector.html           # Standalone browser phone detector
│   └── locked.html             # Fullscreen lockdown page
│
├── python/
│   ├── phone_guard.py          # Main script (multi-camera, escalating lockdown)
│   ├── requirements.txt        # pip dependencies
│   ├── setup_and_run.bat       # First time setup and launch (Windows)
│   └── run.bat                 # Quick launch after first setup
│
└── extension/
    ├── manifest.json
    ├── background.js           # Blocks sites, manages lockdown timer
    ├── detector.html           # Camera detection page
    └── blocked.html            # Page shown when a blocked site is visited
```

## Setup

### Python Phone Guard

**Requirements:** Python 3.10 or higher with Add to PATH checked during install.

**First time:**
```
double-click  python/setup_and_run.bat
```
This installs `ultralytics` and `opencv-python`, downloads the YOLOv8 model (~6 MB), and starts watching.

**After that:**
```
double-click  python/run.bat
```

**What happens when your phone is spotted:**
1. A progress bar fills as the AI confirms the detection across multiple frames
2. A countdown starts. Put the phone down and the lock cancels.
3. Hold it past the countdown and a fullscreen overlay takes over your entire screen
4. The timer counts down and you cannot close or skip it
5. Every offence doubles the next lockdown duration

| Offence | Lockdown |
|---|---|
| #1 | 5 min |
| #2 | 10 min |
| #3 | 20 min |
| #4 | 40 min |
| #5 | 80 min |
| #6+ | 2 hours (max) |

To reset your offence count, delete `python/lockdown_state.json`.

**Key settings** (top of `phone_guard.py`):
```python
CONFIDENCE_MIN      = 0.62    # how sure the AI must be (lower = more sensitive)
FRAMES_TO_WARN      = 28      # consecutive frames before countdown starts
COUNTDOWN_SECS      = 4       # seconds to put phone down before lock fires
BASE_LOCKDOWN_SECS  = 300     # first offence duration (300 = 5 min)
LOCKDOWN_MULTIPLIER = 2.0     # multiplier per offence (2.0 = doubles)
MAX_LOCKDOWN_SECS   = 7200    # hard cap (7200 = 2 hours)
SHOW_WINDOW         = True    # False = fully silent / headless
CAMERA_INDICES      = 'auto'  # 'auto' scans all cameras, or set a list like [0, 1]
MODEL               = 'yolov8n.pt'  # swap to yolov8s.pt for better accuracy
```

### Chrome Extension

**Install:**
1. Open Chrome or Edge and go to `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select the `extension/` folder
5. The LOCK IN icon will appear in your toolbar

**Use:**
* Click the toolbar icon to open the camera detector tab
* Allow camera access once and leave the tab open in the background

**Blocked sites during lockdown:**
YouTube, Instagram, X/Twitter, TikTok, Reddit, Facebook, Netflix, Twitch, Snapchat, Pinterest

### Motivational Website

No setup needed. Open `web/index.html` in any browser.

## Tech Stack

| Layer | Technology |
|---|---|
| 3D visuals | [Three.js](https://threejs.org) r128 |
| Phone detection (Python) | [YOLOv8](https://github.com/ultralytics/ultralytics) via Ultralytics |
| Phone detection (browser) | [TensorFlow.js](https://www.tensorflow.org/js) + COCO-SSD |
| Camera capture | OpenCV (`cv2`) |
| Lockdown overlay | Python `tkinter` fullscreen window |
| Browser blocking | Chrome MV3 `declarativeNetRequest` |
| Fonts | Anton, Oswald, Space Mono (Google Fonts) |

## Which Should I Use?

| Situation | Best option |
|---|---|
| You want the harshest punishment | **Python script** — fullscreen overlay blocks your entire computer |
| You want always on background detection | **Python script** — runs silently with `SHOW_WINDOW = False` |
| You only want to block distracting websites | **Chrome Extension** |
| You do not want to install Python | **Browser detector** (`web/detector.html`) |
| Multiple cameras | **Python script** — detects across all cameras simultaneously with hot plug support |

## Tips

* Set `python/run.bat` to run on Windows startup via Task Scheduler for zero effort enforcement
* Use `SHOW_WINDOW = False` to hide the camera window so you forget it is watching
* The lockdown state persists across reboots. You cannot outrun it by restarting.
* Swap `MODEL = 'yolov8s.pt'` if you are getting missed detections in poor lighting

## Contributing

All contributions are welcome whether that is fixing a bug, improving detection accuracy, adding macOS or Linux support, or anything else that makes this more ruthless. Open an issue to discuss ideas or submit a pull request directly. The goal is simple: make it impossible to slack off.

*Stop watching. Start doing. The clock does not wait for anyone.*
