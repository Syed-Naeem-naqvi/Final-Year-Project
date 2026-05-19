# =========================
# SECTION 1 — Imports & Environment Detection
# =========================
import time
import sys
import os
import pygame

RUNNING_ON_PI = os.uname().sysname == "Linux" and os.path.exists("/sys/class/gpio")

try:
    if RUNNING_ON_PI:
        import RPi.GPIO as GPIO
    else:
        raise Exception("Not on Pi")
except Exception:
    class FakeGPIO:
        BCM = OUT = None
        def setmode(self, *a, **k): pass
        def setup(self, *a, **k): pass
        def output(self, *a, **k): pass
        def cleanup(self): pass
    GPIO = FakeGPIO()


# =========================
# SECTION 2 — GPIO Pin Setup
# =========================
DIN = 17
CLK = 27
LE  = 22
BL  = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIN, GPIO.OUT)
GPIO.setup(CLK, GPIO.OUT)
GPIO.setup(LE,  GPIO.OUT)
GPIO.setup(BL,  GPIO.OUT)
GPIO.output(BL, 0)


# =========================
# SECTION 3 — HV507 Driver
# =========================
def shift_bit(bit):
    GPIO.output(DIN, bit)
    GPIO.output(CLK, 1)
    GPIO.output(CLK, 0)

def update_display(pattern64):
    for bit in pattern64:
        shift_bit(bit)
    GPIO.output(LE, 1)
    GPIO.output(LE, 0)
    print("HV507 LATCHED:", "".join(str(b) for b in pattern64))

def blank_outputs():
    GPIO.output(BL, 0)

def enable_outputs():
    GPIO.output(BL, 1)

def all_off_64():
    return [0] * 64


# =========================
# SECTION 4 — Symbol Patterns (40-bit UI)
# =========================
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

p1 = smile


# =========================
# SECTION 5 — UI→HV507 Mapping (40→64)
# =========================
UI_TO_HV = [
     0,  8, 16, 25, 39,
     1,  9, 17, 24, 38,
     2, 10, 18, 29, 37,
     3, 11, 19, 28, 36,
     4, 13, 22, 27, 35,
     5, 12, 21, 26, 34,
     6, 14, 20, 31, 33,
     7, 15, 23, 30, 32
]

def map_40_to_64(pattern40):
    mapped = [0] * 64
    for ui_index, hv_pin in enumerate(UI_TO_HV):
        mapped[hv_pin] = pattern40[ui_index]
    return mapped


# =========================
# SECTION 6 — UI Layout & Symbol Paths
# =========================
DEFAULT_WIDTH  = 1400
DEFAULT_HEIGHT = 700
UI_PANEL_RATIO = 0.5
REGION_R_SIZE = (150, 150)

SYMBOLS = {
    "p1": "/home/capstoneocad/Desktop/CAPSTONE/symbols/symbol_p1.jpg",
    "p2": "/home/capstoneocad/Desktop/CAPSTONE/symbols/symbol_p2.jpg",
    "p3": "/home/capstoneocad/Desktop/CAPSTONE/symbols/symbol_p3.jpg",
}

current_symbol_name = "p1"

COLS = 5
ROWS = 8
TOTAL_BUBBLES = 40

def init_unified_window():
    pygame.init()
    return pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)


# =========================
# SECTION 7 — Visual Simulator Panel (Raw 40-bit UI Pattern)
# =========================
def draw_simulator_panel(screen, ui_pattern40, ui_panel_width):
    width, height = screen.get_size()
    grid_panel_x = ui_panel_width
    grid_panel_width = width - ui_panel_width
    grid_panel_height = height

    pygame.draw.rect(screen, (25, 25, 25),
                     pygame.Rect(grid_panel_x, 0, grid_panel_width, grid_panel_height))

    cell_width  = grid_panel_width  / COLS
    cell_height = grid_panel_height / ROWS
    cell_size = int(min(cell_width, cell_height))

    grid_total_width  = cell_size * COLS
    grid_total_height = cell_size * ROWS
    offset_x = grid_panel_x + (grid_panel_width  - grid_total_width)  // 2
    offset_y = (grid_panel_height - grid_total_height) // 2

    for i, bit in enumerate(ui_pattern40):
        row = i // COLS
        col = i % COLS
        x = offset_x + col * cell_size
        y = offset_y + row * cell_size
        color = (255, 255, 255) if bit == 1 else (60, 60, 60)
        pygame.draw.rect(screen, color, (x, y, cell_size - 4, cell_size - 4))


# =========================
# SECTION 8 — Mock HV507 (Windows)
# =========================
USE_MOCK = not RUNNING_ON_PI

class MockHV507:
    def __init__(self):
        self.latched_output = [0] * 64
    def shift_bit(self, bit): pass
    def update_display(self, pattern64):
        self.latched_output = list(pattern64)
        print("MOCK HV507:", "".join(str(b) for b in pattern64))
    def blank_outputs(self):
        self.latched_output = [0] * 64
    def enable_outputs(self): pass

if USE_MOCK:
    _mock = MockHV507()
    def shift_bit(bit): _mock.shift_bit(bit)
    def update_display(pattern64): _mock.update_display(pattern64)
    def blank_outputs(): _mock.blank_outputs()
    def enable_outputs(): _mock.enable_outputs()


# =========================
# SECTION 9 — Main Demo Logic
# =========================
def demo():
    global current_symbol_name

    screen = init_unified_window()
    clock = pygame.time.Clock()

    symbol_path = SYMBOLS.get(current_symbol_name)
    try:
        symbol_image = pygame.image.load(symbol_path)
    except:
        symbol_image = None

    inside_R_since = None
    symbol_shown = False
    pattern_sent_time = None

    ui_pattern40 = [0] * 40
    mapped_pattern64 = all_off_64()

    blank_outputs()
    update_display(mapped_pattern64)

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
                ui_pattern40 = [0] * 40
                mapped_pattern64 = all_off_64()
                update_display(mapped_pattern64)
            inside_R_since = None
            symbol_shown = False
            pattern_sent_time = None

        if inside_R_since and (now - inside_R_since) >= 1.0:
            if not symbol_shown:
                symbol_shown = True
                ui_pattern40 = p1[:40]
                mapped_pattern64 = map_40_to_64(ui_pattern40)
                time.sleep(1.0)
                enable_outputs()
                update_display(mapped_pattern64)
                pattern_sent_time = time.time()

        if pattern_sent_time and (now - pattern_sent_time) >= 10.0:
            blank_outputs()
            ui_pattern40 = [0] * 40
            mapped_pattern64 = all_off_64()
            update_display(mapped_pattern64)
            pattern_sent_time = None

        screen.fill((30, 30, 30))
        pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(0, 0, ui_panel_width, height))
        pygame.draw.rect(screen, (80, 80, 200), REGION_R, 2)

        if symbol_shown and symbol_image:
            img_w, img_h = symbol_image.get_size()
            scale_factor = min(r_w / img_w, r_h / img_h)
            new_size = (int(img_w * scale_factor), int(img_h * scale_factor))
            scaled_img = pygame.transform.smoothscale(symbol_image, new_size)
            scaled_rect = scaled_img.get_rect(center=REGION_R.center)
            screen.blit(scaled_img, scaled_rect)

        pygame.draw.circle(screen, (200, 200, 0), (x, y), 5)
        draw_simulator_panel(screen, ui_pattern40, ui_panel_width)

        pygame.display.flip()
        clock.tick(60)

    blank_outputs()
    update_display(all_off_64())
    GPIO.cleanup()
    pygame.quit()


# =========================
# SECTION 10 — Entry Point
# =========================
if __name__ == "__main__":
    try:
        demo()
    except KeyboardInterrupt:
        blank_outputs()
        update_display(all_off_64())
        GPIO.cleanup()
        pygame.quit()
        sys.exit(0)
