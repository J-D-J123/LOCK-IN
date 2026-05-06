#!/usr/bin/env python3
"""Generate README screenshot mockups using Pillow."""
import os, random, subprocess, sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'Pillow'])
    from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, 'screenshots')
os.makedirs(OUT, exist_ok=True)

W, H = 1280, 720
BG     = (0, 0, 0)
ORANGE = (255, 107, 0)
WHITE  = (255, 255, 255)
GRAY   = (160, 160, 160)
DIM    = (60,  60,  60)
DIMBG  = (14,  14,  14)

FONT_DIR = r'C:\Windows\Fonts'

def _font(name, size):
    """Load a Windows system font, fall back gracefully."""
    candidates = {
        'impact':   ['impact.ttf'],
        'consolas': ['consolab.ttf', 'consola.ttf'],
        'mono':     ['cour.ttf', 'lucon.ttf'],
        'bold':     ['arialbd.ttf', 'arial.ttf'],
        'regular':  ['arial.ttf'],
    }
    for fname in candidates.get(name, [name + '.ttf']):
        path = os.path.join(FONT_DIR, fname)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def center_x(draw, text, font, y, fill, img_w=W):
    bb = draw.textbbox((0, 0), text, font=font)
    x  = (img_w - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, fill=fill, font=font)
    return bb[3] - bb[1]   # return text height

def grid_lines(draw, w=W, h=H, step=60, color=(10, 10, 10)):
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=color, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=color, width=1)

def add_particles(draw, n=220, w=W, h=H):
    for _ in range(n):
        x  = random.randint(0, w)
        y  = random.randint(0, h)
        br = random.randint(60, 180)
        r  = random.choice([0, 0, 0, 1, 1, 2])
        c  = (br, br, br)
        if r == 0:
            draw.point((x, y), fill=c)
        else:
            draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=c)

# ─────────────────────────────────────────────────────────────
#  1. MOTIVATIONAL WEBSITE
# ─────────────────────────────────────────────────────────────
def make_website():
    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    add_particles(draw)

    # Vignette (dark edges)
    for i in range(120):
        alpha = int(180 * (1 - i / 120))
        c = (0, 0, 0, alpha)
        draw.rectangle([(i, i), (W-i, H-i)], outline=(0, 0, 0, 0))

    # Title
    f_title = _font('impact', 130)
    f_sub   = _font('consolas', 22)
    f_quote = _font('regular', 17)
    f_label = _font('consolas', 12)

    center_x(draw, 'LOCK IN', f_title, 60, WHITE)
    center_x(draw, 'NO MORE EXCUSES', f_sub, 218, (100, 100, 100))

    # Orange divider
    draw.rectangle([(W//2 - 180, 270), (W//2 + 180, 274)], fill=ORANGE)

    # Three quote cards
    quotes = [
        ('"Pain from discipline weighs ounces.\nRegret weighs tons."',   360),
        ('"Every scroll you make\nis someone else\'s come up."',          460),
        ('"Stop watching. Start doing.\nThe clock doesn\'t wait."',       555),
    ]
    card_w = 700
    cx     = (W - card_w) // 2
    for text, y in quotes:
        draw.rectangle([(cx, y), (cx + card_w, y + 78)],
                        fill=(18, 18, 18))
        draw.rectangle([(cx, y), (cx + 4, y + 78)], fill=ORANGE)
        draw.multiline_text((cx + 22, y + 14), text, fill=(200, 200, 200),
                            font=f_quote, spacing=6)

    # Counter
    center_x(draw, 'SECONDS WASTED TODAY', f_label, 652, (80, 80, 80))
    center_x(draw, '47,832', _font('impact', 52), 668, ORANGE)

    img.save(os.path.join(OUT, '1-website.png'))
    print('[+] 1-website.png')

# ─────────────────────────────────────────────────────────────
#  2. PYTHON PHONE GUARD (camera + terminal)
# ─────────────────────────────────────────────────────────────
def make_phone_guard():
    img  = Image.new('RGB', (W, H), (12, 12, 12))
    draw = ImageDraw.Draw(img)

    f_mono  = _font('consolas', 14)
    f_small = _font('consolas', 12)
    f_label = _font('consolas', 16)

    # Camera panel (left)
    CAM_W, CAM_H = 820, 616
    CAM_X, CAM_Y = 20, 20

    # Simulated camera feed
    for y in range(CAM_H):
        shade = int(30 + 20 * (y / CAM_H))
        for x in range(0, CAM_W, 4):
            noise = random.randint(-8, 8)
            v = max(0, min(255, shade + noise))
            draw.point((CAM_X + x, CAM_Y + y), fill=(v, v, v))

    # Camera header bar
    draw.rectangle([(CAM_X, CAM_Y), (CAM_X + CAM_W, CAM_Y + 36)],
                    fill=(8, 8, 8))
    draw.text((CAM_X + 10, CAM_Y + 9),
              'CAM 0  PHONE 91%  18/18', fill=(0, 80, 255), font=f_label)

    # Phone bounding box (orange)
    bx1, by1 = CAM_X + 310, CAM_Y + 140
    bx2, by2 = CAM_X + 520, CAM_Y + 490
    draw.rectangle([(bx1, by1), (bx2, by2)], outline=(0, 80, 255), width=3)
    draw.text((bx1, by1 - 22), '91%', fill=(0, 80, 255), font=f_label)

    # Camera border
    draw.rectangle([(CAM_X, CAM_Y), (CAM_X + CAM_W, CAM_Y + CAM_H)],
                    outline=(0, 80, 255), width=2)

    # Status bar below camera
    draw.rectangle([(CAM_X, CAM_Y + CAM_H), (CAM_X + CAM_W, CAM_Y + CAM_H + 42)],
                    fill=(6, 6, 6))
    draw.text((CAM_X + 12, CAM_Y + CAM_H + 12),
              'PHONE  ██████████████████  18/18  (91%)  → lockdown #1 = 5m',
              fill=(0, 80, 255), font=f_small)

    # Terminal panel (right)
    TX = CAM_X + CAM_W + 16
    TW = W - TX - 16
    lines = [
        ('', None),
        ('  ════════════════════════════════════════════════', (40, 40, 40)),
        ('    LOCK IN — Phone Guard  (escalating)',            (200, 200, 200)),
        ('  ════════════════════════════════════════════════', (40, 40, 40)),
        ('  Offences so far  : 0',   GRAY),
        ('  Next lockdown    : 5m',  GRAY),
        ('  Confidence       : 55%', GRAY),
        ('  Frames to warn   : 18',  GRAY),
        ('  Countdown        : 4s',  GRAY),
        ('  Preview          : on',  GRAY),
        ('  ════════════════════════════════════════════════', (40, 40, 40)),
        ('', None),
        ('[*] Scanning camera indices 0–7 ...', (0, 160, 60)),
        ('    [+] Camera 0  (1280×720)',         (0, 160, 60)),
        ('', None),
        ('[+] 1 camera(s) found: [0]',           (0, 160, 60)),
        ('[*] Loading YOLOv8 model ...',          GRAY),
        ('[+] Model ready: yolov8n.pt',           (0, 160, 60)),
        ('[+] 1 camera(s) active.',               (0, 160, 60)),
        ('', None),
        ('  Watching... Ctrl+C or Q to stop.', GRAY),
        ('', None),
        ('  PHONE  ██████████████████  18/18', (0, 80, 255)),
        ('  !!! PUT IT DOWN  ████████████░░░░░░  1.8s  !!!', (0, 0, 220)),
    ]
    ty = 28
    for text, color in lines:
        if color and text:
            draw.text((TX, ty), text, fill=color, font=f_small)
        ty += 20

    img.save(os.path.join(OUT, '2-phone-guard.png'))
    print('[+] 2-phone-guard.png')

# ─────────────────────────────────────────────────────────────
#  3. LOCKDOWN OVERLAY
# ─────────────────────────────────────────────────────────────
def make_lockdown():
    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    grid_lines(draw)

    f_badge  = _font('consolas', 18)
    f_big    = _font('impact', 100)
    f_huge   = _font('impact', 130)
    f_timer  = _font('consolas', 96)
    f_sub    = _font('consolas', 16)
    f_next   = _font('consolas', 17)
    f_quote  = _font('consolas', 14)

    cy = 60

    # Badge
    badge = '  OFFENCE  #1  '
    bb    = draw.textbbox((0, 0), badge, font=f_badge)
    bw    = bb[2] - bb[0] + 28
    bx    = (W - bw) // 2
    draw.rectangle([(bx, cy), (bx + bw, cy + 38)], fill=ORANGE)
    draw.text((bx + 14, cy + 8), badge.strip(), fill=BG, font=f_badge)
    cy += 72

    # YOU WERE
    h1 = center_x(draw, 'YOU WERE', f_big, cy, WHITE)
    cy += h1 + 4
    h2 = center_x(draw, 'CAUGHT.', f_huge, cy, ORANGE)
    cy += h2 + 20

    # Label
    center_x(draw, 'LOCKDOWN ENDS IN', f_sub, cy, ORANGE)
    cy += 28

    # Timer
    h3 = center_x(draw, '4:59', f_timer, cy, WHITE)
    cy += h3 + 10

    # Progress bar
    bar_w = 560
    bx    = (W - bar_w) // 2
    draw.rectangle([(bx, cy), (bx + bar_w, cy + 10)], fill=(17, 17, 17))
    draw.rectangle([(bx, cy), (bx + int(bar_w * 0.17), cy + 10)], fill=ORANGE)
    cy += 24

    # Next offence
    center_x(draw, 'NEXT OFFENCE: 10M', f_next, cy, ORANGE)
    cy += 44

    # Rotating quote
    center_x(draw,
             '"Every scroll you make is someone else\'s come up."',
             f_quote, cy, (40, 40, 40))

    img.save(os.path.join(OUT, '3-lockdown.png'))
    print('[+] 3-lockdown.png')

# ─────────────────────────────────────────────────────────────
#  4. CHROME EXTENSION — BLOCKED PAGE
# ─────────────────────────────────────────────────────────────
def make_extension():
    img  = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    grid_lines(draw)

    f_eyebrow = _font('consolas', 11)
    f_big     = _font('impact', 90)
    f_huge    = _font('impact', 116)
    f_body    = _font('regular', 17)
    f_timer   = _font('impact', 72)
    f_label   = _font('consolas', 13)
    f_quote   = _font('consolas', 15)

    cy = 58

    # Eyebrow
    center_x(draw, 'B R O W S E R   L O C K D O W N   A C T I V E',
             f_eyebrow, cy, (180, 75, 0))
    cy += 44

    # YOU WERE CAUGHT
    h1 = center_x(draw, 'YOU WERE', f_big, cy, WHITE)
    cy += h1 + 2
    h2 = center_x(draw, 'CAUGHT.', f_huge, cy, ORANGE)
    cy += h2 + 18

    # Quote
    center_x(draw,
             'You picked up your phone. That choice has a consequence.',
             f_body, cy, (100, 100, 100))
    cy += 32

    # Timer box
    box_w, box_h = 380, 100
    bx = (W - box_w) // 2
    draw.rectangle([(bx, cy), (bx + box_w, cy + box_h)],
                    fill=(10, 8, 5), outline=(80, 42, 0), width=1)
    draw.rectangle([(bx, cy), (bx + 4, cy + box_h)], fill=ORANGE)
    draw.text((bx + 20, cy + 10), 'Lockdown ends in', fill=ORANGE, font=f_label)
    center_x(draw, '28:41', f_timer, cy + 28, WHITE, img_w=W)
    draw.text((bx + 20, cy + box_h - 22),
              'Distracting sites are blocked', fill=(60, 60, 60), font=f_label)
    cy += box_h + 28

    # Rotating quote
    center_x(draw,
             '"Pain from discipline weighs ounces. Regret weighs tons."',
             f_quote, cy, (38, 38, 38))
    cy += 50

    # Unlock button (greyed out)
    btn_txt = 'Emergency Unlock (22s)'
    bb      = draw.textbbox((0, 0), btn_txt, font=f_label)
    bw      = bb[2] - bb[0] + 40
    bx2     = (W - bw) // 2
    draw.rectangle([(bx2, cy), (bx2 + bw, cy + 34)],
                    outline=(40, 40, 40), width=1)
    draw.text((bx2 + 20, cy + 10), btn_txt, fill=(50, 50, 50), font=f_label)

    img.save(os.path.join(OUT, '4-extension-blocked.png'))
    print('[+] 4-extension-blocked.png')


if __name__ == '__main__':
    random.seed(42)
    make_website()
    make_phone_guard()
    make_lockdown()
    make_extension()
    print(f'\nAll screenshots saved to  screenshots/')
