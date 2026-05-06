#!/usr/bin/env python3
"""
LOCK IN — Phone Guard  (multi-camera + escalating lockdown edition)

Each time the camera catches your phone the lockdown doubles.
Lockdown state persists across restarts via lockdown_state.json.
"""

# ╔══════════════════════════════════════════════════════════╗
#  EDIT THESE TO CUSTOMIZE
# ╚══════════════════════════════════════════════════════════╝
CONFIDENCE_MIN      = 0.55    # detection confidence threshold (0.0–1.0)
FRAMES_TO_WARN      = 18      # consecutive frames before countdown starts
COUNTDOWN_SECS      = 4       # seconds to put phone down before lock fires
SHOW_WINDOW         = True    # False = headless / silent

# Escalation settings
BASE_LOCKDOWN_SECS  = 300     # first offence: 5 minutes
LOCKDOWN_MULTIPLIER = 2.0     # each offence doubles the duration
MAX_LOCKDOWN_SECS   = 7200    # never longer than 2 hours (7200 s)

# Cameras to watch
#   'auto'     → scan and use every camera found (recommended)
#   [0, 1, 2]  → only these specific indices
CAMERA_INDICES  = 'auto'
MAX_SCAN        = 8

MODEL           = 'yolov8n.pt'   # yolov8n = fastest  |  yolov8s = more accurate
# ════════════════════════════════════════════════════════════

import sys
import os
import json
import time
import ctypes
import ctypes.wintypes
import threading
import math
import subprocess
import tkinter as tk

# Paths resolved after imports so os is available
_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
STATE_FILE = os.path.join(_ROOT, 'python', 'lockdown_state.json')

# ── AUTO-INSTALL DEPENDENCIES ────────────────────────────────
def _ensure():
    missing = []
    try:    import cv2             # noqa: F401
    except ImportError: missing.append('opencv-python')
    try:    from ultralytics import YOLO  # noqa: F401
    except ImportError: missing.append('ultralytics')
    if missing:
        print(f'[*] Installing: {", ".join(missing)} ...')
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install'] + missing,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('[+] Done.\n')

_ensure()

import cv2
import numpy as np
from ultralytics import YOLO

PHONE_CLASS_ID = 67   # COCO: "cell phone"
LINE = 64             # terminal line width


# ══════════════════════════════════════════════════════════════
#  LOCKDOWN STATE  (persists to disk between runs)
# ══════════════════════════════════════════════════════════════

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'offense_count': 0, 'lockdown_end_time': 0.0}

def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def offense_duration(offense_number: int) -> int:
    raw = BASE_LOCKDOWN_SECS * (LOCKDOWN_MULTIPLIER ** (offense_number - 1))
    return min(int(raw), MAX_LOCKDOWN_SECS)

def fmt_duration(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h:
        return f'{h}h {m}m' if m else f'{h}h'
    if m:
        return f'{m}m {s}s' if s else f'{m}m'
    return f'{s}s'


# ══════════════════════════════════════════════════════════════
#  KEYBOARD HOOK  (blocks Win key, Alt+F4, Alt+Tab during lockdown)
# ══════════════════════════════════════════════════════════════

class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode',      ctypes.c_ulong),
        ('scanCode',    ctypes.c_ulong),
        ('flags',       ctypes.c_ulong),
        ('time',        ctypes.c_ulong),
        ('dwExtraInfo', ctypes.c_void_p),
    ]

# Use pointer-width ints for WPARAM/LPARAM — c_ssize_t is always 64-bit on
# 64-bit Windows, preventing the OverflowError from wintypes.LPARAM (c_long).
_HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_int,
    ctypes.c_size_t,    # WPARAM
    ctypes.c_ssize_t    # LPARAM
)

_WH_KEYBOARD_LL = 13
_WM_SYSKEYDOWN  = 0x0104

_VK_LWIN = 0x5B; _VK_RWIN = 0x5C   # Windows keys
_VK_F4   = 0x73; _VK_TAB  = 0x09   # Alt+F4 / Alt+Tab

_hook_id = None
_hook_fn = None  # Must keep reference — GC would break the hook

_u32 = ctypes.windll.user32
_u32.CallNextHookEx.restype  = ctypes.c_ssize_t
_u32.CallNextHookEx.argtypes = [
    ctypes.c_void_p, ctypes.c_int,
    ctypes.c_size_t, ctypes.c_ssize_t,
]

def _install_hook():
    global _hook_id, _hook_fn

    def _cb(nCode, wParam, lParam):
        if nCode >= 0:
            # lParam arrives as a Python int (64-bit address); wrap via c_void_p
            vk = ctypes.cast(ctypes.c_void_p(lParam),
                             ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents.vkCode
            if vk in (_VK_LWIN, _VK_RWIN):
                return 1
            if wParam == _WM_SYSKEYDOWN and vk in (_VK_F4, _VK_TAB):
                return 1
        return _u32.CallNextHookEx(_hook_id, nCode, wParam, lParam)

    _hook_fn = _HOOKPROC(_cb)
    _hook_id = _u32.SetWindowsHookExW(_WH_KEYBOARD_LL, _hook_fn, None, 0)

def _remove_hook():
    global _hook_id
    if _hook_id:
        ctypes.windll.user32.UnhookWindowsHookEx(_hook_id)
        _hook_id = None


# ══════════════════════════════════════════════════════════════
#  LOCKDOWN OVERLAY  (fullscreen tkinter — blocks the whole screen)
# ══════════════════════════════════════════════════════════════

_OVERLAY_QUOTES = [
    "EVERY SCROLL YOU MAKE IS SOMEONE ELSE'S COME UP.",
    "YOU SAID YOU WOULD. PROVE IT.",
    "PAIN FROM DISCIPLINE WEIGHS OUNCES. REGRET WEIGHS TONS.",
    "WHO YOU ARE RIGHT NOW IS WHO YOU CHOSE TO BECOME.",
    "WHILE YOU'RE OVERTHINKING, THEY'RE OUTWORKING.",
    "THE DREAM DOESN'T DIE. YOU DO — ONE EXCUSE AT A TIME.",
    "POTENTIAL WITHOUT ACTION IS JUST A STORY YOU TELL YOURSELF.",
    "YOU'RE NOT TIRED. YOU'RE UNINSPIRED.",
    "STOP WATCHING. START DOING. THE CLOCK DOESN'T WAIT.",
]

def run_overlay(duration_secs: int, offense_n: int, next_dur_secs: int):
    """
    Show a blocking fullscreen lockdown overlay.
    - Installs keyboard hook: blocks Win key, Alt+F4, Alt+Tab.
    - Returns only when the countdown reaches zero.
    """
    _install_hook()

    root = tk.Tk()
    root.overrideredirect(True)        # removes title bar / window chrome
    root.attributes('-topmost', True)  # always in front of other windows
    root.configure(bg='#000000')
    root.protocol('WM_DELETE_WINDOW', lambda: None)
    root.bind('<Alt-F4>',   lambda e: 'break')
    root.bind('<Button-3>', lambda e: 'break')

    # Can't use -fullscreen with overrideredirect — manually fill the screen
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f'{sw}x{sh}+0+0')
    end_time = time.time() + duration_secs

    # ── Subtle grid background ────────────────────────────────
    bg = tk.Canvas(root, bg='#000000', highlightthickness=0)
    bg.place(x=0, y=0, width=sw, height=sh)
    GRID = 60
    for gx in range(0, sw, GRID):
        bg.create_line(gx, 0, gx, sh, fill='#0a0a0a', width=1)
    for gy in range(0, sh, GRID):
        bg.create_line(0, gy, sw, gy, fill='#0a0a0a', width=1)

    # ── Center frame ─────────────────────────────────────────
    frame = tk.Frame(root, bg='#000000')
    frame.place(relx=0.5, rely=0.5, anchor='center')

    fs_badge = max(13, sh // 55)
    fs_big   = max(48, sh // 9)
    fs_huge  = max(64, sh // 7)
    fs_sub   = max(11, sh // 70)
    fs_next  = max(12, sh // 62)

    # Offence badge
    tk.Label(
        frame,
        text=f'  OFFENCE  #{offense_n}  ',
        bg='#FF6B00', fg='#000000',
        font=('Consolas', fs_badge, 'bold'),
        padx=14, pady=5,
    ).pack(pady=(0, max(18, sh // 35)))

    # Headline
    tk.Label(frame, text='YOU WERE',
             bg='#000000', fg='#ffffff',
             font=('Impact', fs_big)).pack()
    tk.Label(frame, text='CAUGHT.',
             bg='#000000', fg='#FF6B00',
             font=('Impact', fs_huge)).pack()

    # Timer label
    tk.Label(frame, text='LOCKDOWN ENDS IN',
             bg='#000000', fg='#FF6B00',
             font=('Consolas', fs_sub)).pack(pady=(max(16, sh // 40), 2))

    timer_var = tk.StringVar(value='–:––')
    timer_lbl = tk.Label(frame, textvariable=timer_var,
                          bg='#000000', fg='#ffffff',
                          font=('Consolas', fs_huge, 'bold'))
    timer_lbl.pack()

    # Progress bar
    bar_w  = min(560, int(sw * 0.5))
    bar_bg = tk.Frame(frame, bg='#111111', width=bar_w, height=10)
    bar_bg.pack(pady=(8, 0))
    bar_bg.pack_propagate(False)
    bar_fill = tk.Frame(bar_bg, bg='#FF6B00', height=10)
    bar_fill.place(x=0, y=0, height=10, width=0)

    # Next offence warning
    tk.Label(frame,
             text=f'NEXT OFFENCE: {fmt_duration(next_dur_secs).upper()}',
             bg='#000000', fg='#FF6B00',
             font=('Consolas', fs_next)).pack(pady=(max(14, sh // 45), 0))

    # Rotating quote
    quote_var = tk.StringVar(value=_OVERLAY_QUOTES[0])
    tk.Label(frame, textvariable=quote_var,
             bg='#000000', fg='#282828',
             font=('Consolas', fs_sub),
             wraplength=int(sw * 0.62)).pack(pady=(max(20, sh // 30), 0))

    qi = [0]

    def _rotate():
        qi[0] = (qi[0] + 1) % len(_OVERLAY_QUOTES)
        quote_var.set(_OVERLAY_QUOTES[qi[0]])
        root.after(5000, _rotate)

    root.after(5000, _rotate)

    def _tick():
        remaining = max(0.0, end_time - time.time())
        if remaining <= 0:
            _remove_hook()
            root.destroy()
            return
        m, s = int(remaining) // 60, int(remaining) % 60
        timer_var.set(f'{m}:{s:02d}')
        if remaining < 60:
            timer_lbl.config(fg='#FF2222')
        elif remaining < 120:
            timer_lbl.config(fg='#FF6B00')
        else:
            timer_lbl.config(fg='#ffffff')
        elapsed  = duration_secs - remaining
        fraction = elapsed / duration_secs if duration_secs else 0
        bar_fill.place(x=0, y=0, height=10, width=int(bar_w * fraction))
        root.after(1000, _tick)

    _tick()

    def _keep_top():
        try:
            root.lift()
            root.focus_force()
            root.after(400, _keep_top)
        except tk.TclError:
            pass

    _keep_top()
    root.mainloop()


# ══════════════════════════════════════════════════════════════
#  LOCKDOWN TRIGGER
# ══════════════════════════════════════════════════════════════

def trigger_lockdown(state: dict):
    """
    Execute a lockdown:
      1. Increment offense count, compute duration
      2. Save state to disk (survives being killed)
      3. Show fullscreen blocking overlay (returns when timer ends)
    """
    state['offense_count'] += 1
    n        = state['offense_count']
    duration = offense_duration(n)
    end_time = time.time() + duration
    next_dur = offense_duration(n + 1)

    state['lockdown_end_time'] = end_time
    save_state(state)

    print(f'\n\n  {"!" * (LINE - 2)}')
    print(f'  LOCKDOWN #{n}  —  {fmt_duration(duration)}'.center(LINE))
    print(f'  Next offence: {fmt_duration(next_dur)}'.center(LINE))
    print(f'  {"!" * (LINE - 2)}\n')

    try:
        ctypes.windll.kernel32.Beep(450, 130); time.sleep(0.14)
        ctypes.windll.kernel32.Beep(370, 130); time.sleep(0.14)
        ctypes.windll.kernel32.Beep(290, 420)
    except Exception:
        pass

    cv2.destroyAllWindows()             # close camera preview first
    run_overlay(duration, n, next_dur)  # blocking — returns when done

    state['lockdown_end_time'] = 0.0
    save_state(state)
    print(f'\n\n  [+] Lockdown #{n} ended. Back to watching.\n')


# ══════════════════════════════════════════════════════════════
#  CAMERA HELPERS
# ══════════════════════════════════════════════════════════════

def find_cameras(max_index: int = MAX_SCAN) -> list[int]:
    print(f'[*] Scanning camera indices 0–{max_index - 1} ...')
    found = []
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f'    [+] Camera {i}  ({w}×{h})')
                found.append(i)
        cap.release()
    return found


class CameraCapture(threading.Thread):
    """Grabs frames from one camera continuously in the background."""
    def __init__(self, index: int):
        super().__init__(daemon=True)
        self.index   = index
        self._frame  = None
        self._lock   = threading.Lock()
        self.running = True
        self.ok      = False

    def run(self):
        cap = cv2.VideoCapture(self.index)
        if not cap.isOpened():
            return
        fail = 0
        while self.running:
            try:
                ret, frame = cap.read()
            except Exception:
                ret, frame = False, None
            if ret:
                with self._lock:
                    self._frame = frame
                    self.ok = True
                fail = 0
            else:
                fail += 1
                if fail > 15:
                    self.ok = False   # signal thread is unhealthy
                time.sleep(0.03)     # don't busy-spin on a dead camera
        cap.release()

    def get_frame(self):
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def stop(self):
        self.running = False


def build_grid(panels: list, target_w: int = 960) -> np.ndarray | None:
    if not panels:
        return None
    n    = len(panels)
    cols = 1 if n == 1 else 2
    rows = math.ceil(n / cols)
    cw   = target_w // cols
    ch   = cw * 3 // 4
    canvas = np.zeros((rows * ch, cols * cw, 3), dtype=np.uint8)
    for i, (frame, label, color) in enumerate(panels):
        r, c   = divmod(i, cols)
        y0, x0 = r * ch, c * cw
        thumb  = cv2.resize(frame, (cw, ch))
        canvas[y0:y0 + ch, x0:x0 + cw] = thumb
        cv2.rectangle(canvas, (x0, y0), (x0 + cw, y0 + 36), (8, 8, 8), -1)
        cv2.putText(canvas, label, (x0 + 8, y0 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        cv2.rectangle(canvas, (x0 + 1, y0 + 1),
                      (x0 + cw - 2, y0 + ch - 2), color, 2)
    return canvas


# ══════════════════════════════════════════════════════════════
#  TERMINAL HELPERS
# ══════════════════════════════════════════════════════════════

def status(msg: str):
    print(f'\r  {msg:<{LINE}}', end='', flush=True)

def banner(state: dict):
    n        = state['offense_count']
    next_dur = fmt_duration(offense_duration(n + 1))
    print('=' * LINE)
    print('  LOCK IN — Phone Guard  (escalating)'.center(LINE))
    print('=' * LINE)
    print(f'  Offences so far  : {n}')
    print(f'  Next lockdown    : {next_dur}')
    print(f'  Confidence       : {CONFIDENCE_MIN:.0%}')
    print(f'  Frames to warn   : {FRAMES_TO_WARN}')
    print(f'  Countdown        : {COUNTDOWN_SECS}s to put phone down')
    print(f'  Preview          : {"on" if SHOW_WINDOW else "off (headless)"}')
    print('=' * LINE)
    print()


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    state = load_state()
    banner(state)

    # ── Restore interrupted lockdown ──────────────────────────
    lockdown_end = state.get('lockdown_end_time', 0.0)
    if lockdown_end > time.time():
        remaining = int(lockdown_end - time.time())
        n         = state['offense_count']
        print(f'[!] Resuming lockdown #{n} — {fmt_duration(remaining)} remaining.\n')
        run_overlay(remaining, n, offense_duration(n + 1))
        state['lockdown_end_time'] = 0.0
        save_state(state)
    else:
        state['lockdown_end_time'] = 0.0

    # ── Find cameras ──────────────────────────────────────────
    if CAMERA_INDICES == 'auto':
        indices = find_cameras()
    else:
        indices = list(CAMERA_INDICES)

    if not indices:
        print('[!] No cameras found. Check connections.')
        sys.exit(1)
    print(f'\n[+] {len(indices)} camera(s) found: {indices}\n')

    # ── Load model ────────────────────────────────────────────
    print('[*] Loading YOLOv8 model (first run downloads ~6 MB) ...')
    model = YOLO(MODEL, verbose=False)
    print(f'[+] Model ready: {MODEL}\n')

    # ── Start capture threads ─────────────────────────────────
    caps = [CameraCapture(i) for i in indices]
    for c in caps:
        c.start()
    print('[*] Warming up cameras ...')
    time.sleep(1.2)
    caps = [c for c in caps if c.ok]
    if not caps:
        print('[!] No cameras produced frames. Exiting.')
        sys.exit(1)

    print(f'[+] {len(caps)} camera(s) active.\n')
    print('  Watching... Ctrl+C or Q to stop.\n')

    # ── Detection state ───────────────────────────────────────
    consecutive    = 0
    per_cam_consec = {c.index: 0 for c in caps}
    countdown_at   = None
    BAR            = 18

    try:
        while True:
            now       = time.time()
            any_phone = False
            best_conf = 0.0
            panels    = []

            for cap in caps:
                frame = cap.get_frame()
                if frame is None:
                    continue

                results = model(frame, verbose=False, classes=[PHONE_CLASS_ID])

                phone_here = False
                cam_conf   = 0.0
                boxes      = []

                for r in results:
                    for box in r.boxes:
                        conf = float(box.conf[0])
                        if int(box.cls[0]) == PHONE_CLASS_ID and conf >= CONFIDENCE_MIN:
                            phone_here = True
                            cam_conf   = max(cam_conf, conf)
                            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                            boxes.append((x1, y1, x2, y2, conf))

                if phone_here:
                    per_cam_consec[cap.index] = per_cam_consec.get(cap.index, 0) + 1
                    any_phone = True
                    best_conf = max(best_conf, cam_conf)
                else:
                    per_cam_consec[cap.index] = max(
                        0, per_cam_consec.get(cap.index, 0) - 2)

                if SHOW_WINDOW:
                    disp   = cv2.flip(frame, 1)
                    dh, dw = disp.shape[:2]
                    for (x1, y1, x2, y2, conf) in boxes:
                        mx1 = dw - x2
                        mx2 = dw - x1
                        cv2.rectangle(disp, (mx1, y1), (mx2, y2), (0, 80, 255), 2)
                        cv2.putText(disp, f'{conf:.0%}',
                                    (mx1, max(y1 - 6, 14)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 80, 255), 2)
                    cc = per_cam_consec.get(cap.index, 0)
                    if phone_here:
                        lbl  = f'CAM {cap.index}  PHONE {cam_conf:.0%} {cc}/{FRAMES_TO_WARN}'
                        lcol = (0, 80, 255)
                    else:
                        lbl, lcol = f'CAM {cap.index}  Watching', (0, 160, 60)
                    panels.append((disp, lbl, lcol))

            # ── Aggregate consecutive ─────────────────────────
            if any_phone:
                consecutive += 1
            else:
                consecutive = max(0, consecutive - 2)

            # ── State machine ─────────────────────────────────
            if countdown_at is not None:
                elapsed   = now - countdown_at
                remaining = COUNTDOWN_SECS - elapsed

                if not any_phone:
                    countdown_at = None
                    consecutive  = 0
                    print(f'\n\n  [✓] Phone down — lock cancelled. Stay focused.\n')
                    try: ctypes.windll.kernel32.Beep(880, 180)
                    except Exception: pass

                elif remaining <= 0:
                    trigger_lockdown(state)     # blocking — screen is locked until done
                    countdown_at   = None
                    consecutive    = 0
                    per_cam_consec = {c.index: 0 for c in caps}

                else:
                    filled = int((elapsed / COUNTDOWN_SECS) * BAR)
                    bar    = ('█' * filled).ljust(BAR, '░')
                    status(f'!!! PUT IT DOWN  [{bar}]  {remaining:.1f}s  !!!')
                    try: ctypes.windll.kernel32.Beep(900, 80)
                    except Exception: pass

            elif consecutive >= FRAMES_TO_WARN:
                countdown_at = time.time()
                n_next = state['offense_count'] + 1
                print(f'\n\n  [!] Phone confirmed — {COUNTDOWN_SECS}s to put it down!'
                      f'  (would be lockdown #{n_next}: '
                      f'{fmt_duration(offense_duration(n_next))})\n')
                try: ctypes.windll.kernel32.Beep(1000, 280)
                except Exception: pass

            elif any_phone:
                filled  = int((consecutive / FRAMES_TO_WARN) * BAR)
                bar     = ('█' * filled).ljust(BAR, '░')
                n_next  = state['offense_count'] + 1
                status(f'PHONE  [{bar}]  {consecutive}/{FRAMES_TO_WARN}'
                       f'  ({best_conf:.0%})  → lockdown #{n_next}'
                       f' = {fmt_duration(offense_duration(n_next))}')
            else:
                n_next = state['offense_count'] + 1
                status(f'Watching {len(caps)} cam(s) ...  '
                       f'next lockdown #{n_next} = {fmt_duration(offense_duration(n_next))}')

            # ── Render grid ───────────────────────────────────
            if SHOW_WINDOW and panels:
                grid = build_grid(panels,
                                  target_w=960 if len(panels) > 1 else 640)
                if grid is not None:
                    sh_b = 42
                    sbar = np.zeros((sh_b, grid.shape[1], 3), dtype=np.uint8)
                    if countdown_at is not None:
                        elapsed   = now - countdown_at
                        remaining = max(0, COUNTDOWN_SECS - elapsed)
                        gtxt = f'!!! LOCKING IN {remaining:.1f}s — PUT PHONE DOWN !!!'
                        gcol = (0, 0, 220)
                    elif any_phone:
                        gtxt = f'PHONE  {consecutive}/{FRAMES_TO_WARN}  ({best_conf:.0%})'
                        gcol = (0, 80, 255)
                    else:
                        n_next = state['offense_count'] + 1
                        gtxt = (f'WATCHING {len(caps)} cam(s)  |  '
                                f'next lockdown #{n_next} = '
                                f'{fmt_duration(offense_duration(n_next))}')
                        gcol = (0, 160, 60)
                    cv2.putText(sbar, gtxt, (12, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, gcol, 2)
                    cv2.imshow('LOCK IN — Phone Guard',
                               np.vstack([grid, sbar]))

                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):
                    break

    except KeyboardInterrupt:
        print('\n\n  [*] Stopped by user.')
    finally:
        for c in caps:
            c.stop()
        cv2.destroyAllWindows()
        print('  [*] Cameras released. Goodbye.\n')


if __name__ == '__main__':
    main()
