# Pi_ready_v2.1

import time
import sys
import os

print("RUNNING FILE:", __file__)

# =========================
# 1) Imports: GPIO + UI
# =========================

import pygame  # Used for mouse tracking and displaying the symbol image

# Auto-detect Raspberry Pi vs Windows
RUNNING_ON_PI = os.uname().sysname == "Linux" and os.path.exists("/sys/class/gpio")

try:
    if RUNNING_ON_PI:
        import RPi.GPIO as GPIO
    else:
        raise Exception("Not on Pi")
except Exception:
    # Running on Windows or non‑Pi environment
    class FakeGPIO:
        BCM = OUT = None

        def setmode(self, *a, **k): pass
        def setup(self, *a, **k): pass
        def output(self, *a, **k): pass
        def cleanup(self): pass

    GPIO = FakeGPIO()
    print("[INFO] Using FakeGPIO (Windows / non‑Pi environment)")

# =========================
# 2) GPIO pin definitions
# =========================

DIN = 17
CLK = 27
LE  = 22
BL  = 23

# =========================
# 3) GPIO setup
# =========================

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIN, GPIO.OUT)
GPIO.setup(CLK, GPIO.OUT)
GPIO.setup(LE,  GPIO.OUT)
GPIO.setup(BL,  GPIO.OUT)

# Start with outputs blanked (safe state)
GPIO.output(BL, 0)

# =========================
# 4) Low-level HV507 driver
# =========================

def shift_bit(bit):
    print("SHIFT:", bit)
    GPIO.output(DIN, bit)
    GPIO.output(CLK, 1)
    GPIO.output(CLK, 0)

def update_display(pattern64):
    if len(pattern64) != 64:
        raise ValueError("pattern64 must be length 64")
    for bit in pattern64:
        shift_bit(bit)
    GPIO.output(LE, 1)
    GPIO.output(LE, 0)

def blank_outputs():
    GPIO.output(BL, 0)

def enable_outputs():
    GPIO.output(BL, 1)

# =========================
# 5) Pattern tools
# =========================

def all_off_64():
    return [0] * 64

def all_on_64():
    return [1] * 64

# Example symbol patterns
magnifier = [
    0,0,0,0,0,
    0,0,0,0,0,
    1,1,1,0,0,
    1,0,1,0,0,
    1,1,1,0,0,
    0,0,0,1,0,
    0,0,0,0,1,
    0,0,0,0,0
] + [0]*24

smile = [
    0,0,0,0,0,
    0,0,0,0,0,
    0,1,0,1,0,
    0,0,0,0,0,
    1,0,0,0,1,
    0,1,1,1,0,
    0,0,0,0,0,
    0,0,0,0,0
] + [0]*24

all_symbols = [magnifier, smile]

p1 = all_symbols[1]   # Your original selection preserved

# =========================
# 6) Mapping function
# =========================

mapping_function = {str(i): i for i in range(64)}

def apply_mapping(pattern_unmapped, mapping):
    if len(pattern_unmapped) != 64:
        raise ValueError("pattern_unmapped must be length 64")
    mapped = [0] * 64
    for i, bit in enumerate(pattern_unmapped):
        mapped[mapping[str(i)]] = bit
    return mapped

# =========================
# 7) Unified UI setup (Pygame)
# =========================

DEFAULT_WIDTH  = 1400
DEFAULT_HEIGHT = 700
UI_PANEL_RATIO = 0.5
REGION_R_SIZE = (150, 150)

# =========================
# Symbol library (Pi paths)
# =========================

SYMBOLS = {
    "p1": "/home/capstoneocad/Desktop/CAPSTONE/symbols/symbol_p1.jpg",
    "p2": "/home/capstoneocad/Desktop/CAPSTONE/symbols/symbol_p2.jpg",
    "p3": "/home/capstoneocad/Desktop/CAPSTONE/symbols/symbol_p3.jpg",
}

current_symbol_name = "p1"

# Grid parameters
COLS = 5
ROWS = 8
TOTAL_BUBBLES = 40

def init_unified_window():
    pygame.init()
    return pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)

# =========================
# 8) Visual simulator drawing
# =========================

def draw_simulator_panel(screen, pattern64, ui_panel_width):
    width, height = screen.get_size()
    grid_panel_x = ui_panel_width
    grid_panel_width = width - ui_panel_width
    grid_panel_height = height

    pygame.draw.rect(screen, (25, 25, 25),
                     pygame.Rect(grid_panel_x, 0, grid_panel_width, grid_panel_height))

    pattern40 = pattern64[:TOTAL_BUBBLES]

    cell_width  = grid_panel_width  / COLS
    cell_height = grid_panel_height / ROWS
    cell_size = int(min(cell_width, cell_height))

    grid_total_width  = cell_size * COLS
    grid_total_height = cell_size * ROWS
    offset_x = grid_panel_x + (grid_panel_width  - grid_total_width)  // 2
    offset_y = (grid_panel_height - grid_total_height) // 2

    for i, bit in enumerate(pattern40):
        row = i // COLS
        col = i % COLS
        x = offset_x + col * cell_size
        y = offset_y + row * cell_size
        color = (255, 255, 255) if bit == 1 else (60, 60, 60)
        pygame.draw.rect(screen, color, (x, y, cell_size - 4, cell_size - 4))

# =========================
# 9) Mock HV507 driver
# =========================

USE_MOCK = not RUNNING_ON_PI

class MockHV507:
    def __init__(self):
        self.latched_output = [0] * 64

    def shift_bit(self, bit): pass

    def update_display(self, pattern64):
        self.latched_output = list(pattern64)
        print("\n[MOCK HV507] Latched 64-bit pattern:")
        print("".join(str(b) for b in pattern64))

    def blank_outputs(self):
        print("[MOCK HV507] BLANK")
        self.latched_output = [0] * 64

    def enable_outputs(self):
        print("[MOCK HV507] ENABLE outputs")

if USE_MOCK:
    print("\n[INFO] MOCK MODE — no GPIO used.\n")
    _mock = MockHV507()
    def shift_bit(bit): _mock.shift_bit(bit)
    def update_display(pattern64): _mock.update_display(pattern64)
    def blank_outputs(): _mock.blank_outputs()
    def enable_outputs(): _mock.enable_outputs()

# =========================
# 10) Demo logic
# =========================

def demo():
    global current_symbol_name

    screen = init_unified_window()
    clock = pygame.time.Clock()

    symbol_path = SYMBOLS.get(current_symbol_name)
    try:
        symbol_image = pygame.image.load(symbol_path)
    except:
        print(f"[ERROR] Could not load image: {symbol_path}")
        symbol_image = None

    inside_R_since = None
    symbol_shown = False
    pattern_sent_time = None
    current_pattern = all_off_64()

    blank_outputs()
    update_display(current_pattern)

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: current_symbol_name = "p1"
                elif event.key == pygame.K_2: current_symbol_name = "p2"
                elif event.key == pygame.K_3: current_symbol_name = "p3"

                symbol_path = SYMBOLS.get(current_symbol_name)
                try:
                    symbol_image = pygame.image.load(symbol_path)
                except:
                    print(f"[ERROR] Could not load image: {symbol_path}")
                    symbol_image = None

        width, height = screen.get_size()
        ui_panel_width = int(width * UI_PANEL_RATIO)

        r_w, r_h = REGION_R_SIZE
        REGION_R = pygame.Rect(ui_panel_width - r_w - 50, 50, r_w, r_h)

        x, y = pygame.mouse.get_pos()
        cursor_in_R = REGION_R.collidepoint(x, y)
        now = time.time()

        if cursor_in_R:
            if inside_R_since is None:
                inside_R_since = now
        else:
            if symbol_shown or pattern_sent_time:
                blank_outputs()
                current_pattern = all_off_64()
                update_display(current_pattern)
            inside_R_since = None
            symbol_shown = False
            pattern_sent_time = None

        if inside_R_since and (now - inside_R_since) >= 1.0:
            if not symbol_shown:
                symbol_shown = True
                mapped = apply_mapping(p1, mapping_function)
                current_pattern = mapped
                time.sleep(1.0)
                enable_outputs()
                update_display(mapped)
                pattern_sent_time = time.time()

        if pattern_sent_time and (now - pattern_sent_time) >= 10.0:
            blank_outputs()
            current_pattern = all_off_64()
            update_display(current_pattern)
            pattern_sent_time = None

        screen.fill((30, 30, 30))
        pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(0, 0, ui_panel_width, height))
        pygame.draw.rect(screen, (80, 80, 200), REGION_R, 2)

        # SCALE IMAGE TO FIT REGION R
        if symbol_shown and symbol_image:
            img_w, img_h = symbol_image.get_size()
            scale_factor = min(r_w / img_w, r_h / img_h)
            new_size = (int(img_w * scale_factor), int(img_h * scale_factor))
            scaled_img = pygame.transform.smoothscale(symbol_image, new_size)
            scaled_rect = scaled_img.get_rect(center=REGION_R.center)
            screen.blit(scaled_img, scaled_rect)

        pygame.draw.circle(screen, (200, 200, 0), (x, y), 5)
        draw_simulator_panel(screen, current_pattern, ui_panel_width)

        pygame.display.flip()
        clock.tick(60)

    blank_outputs()
    update_display(all_off_64())
    GPIO.cleanup()
    pygame.quit()

# =========================
# 11) Main entry point
# =========================

if __name__ == "__main__":
    print("______Pi_ready_v2.1 RUN_______")
    try:
        demo()
    except KeyboardInterrupt:
        blank_outputs()
        update_display(all_off_64())
        GPIO.cleanup()
        pygame.quit()
        sys.exit(0)
