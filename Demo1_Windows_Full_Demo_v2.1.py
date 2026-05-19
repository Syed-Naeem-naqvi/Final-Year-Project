import time
import sys


# =========================
# 1) Imports: GPIO + UI
# =========================

import pygame  # Used for mouse tracking and displaying the symbol image

try:
    import RPi.GPIO as GPIO
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
    """
    Shift a single bit into the HV507 via DIN and CLK.
    :param bit: 1 or 0, the next bit to place on the HV507 DIOA input pin.
    """
    GPIO.output(DIN, bit)   # Put bit on data line
    GPIO.output(CLK, 1)     # Rising edge: HV507 samples DIN
    GPIO.output(CLK, 0)     # Falling edge: prepare for next bit


def update_display(pattern64):
    """
    Send a full 64-bit pattern to the HV507 and latch it.
    :param pattern64: List of 64 bits (1 = bubble ON, 0 = bubble OFF).
    """
    if len(pattern64) != 64:
        raise ValueError("pattern64 must be length 64")

    for bit in pattern64:
        shift_bit(bit)

    GPIO.output(LE, 1)   # Latch
    GPIO.output(LE, 0)


def blank_outputs():
    """Turn all outputs off by blanking."""
    GPIO.output(BL, 0)


def enable_outputs():
    """Enable outputs (unblank)."""
    GPIO.output(BL, 1)

# =========================
# 5) Pattern tools
# =========================

def all_off_64():
    return [0] * 64


def all_on_64():
    return [1] * 64


# Example symbol pattern p1 (64 bits) – magnifying glass

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

p1 = all_symbols[0]

2
# =========================
# 6) Mapping function
# =========================

mapping_function = {str(i): i for i in range(64)}

def apply_mapping(pattern_unmapped, mapping):
    """
    Apply mapping_function to an unmapped 64-bit pattern.
    :param pattern_unmapped: List of 64 bits (original symbol vector p1).
    :param mapping: Dict mapping string index -> mapped index.
    :return: List of 64 bits, mapped to physical bubble positions.
    """
    if len(pattern_unmapped) != 64:
        raise ValueError("pattern_unmapped must be length 64")

    mapped = [0] * 64
    for i, bit in enumerate(pattern_unmapped):
        key = str(i)
        mapped_index = mapping[key]
        mapped[mapped_index] = bit
    return mapped

# =========================
# 7) Unified UI setup (Pygame)
# =========================

# Unified window defaults (A3 + W2 + L3)
DEFAULT_WIDTH  = 1400
DEFAULT_HEIGHT = 700

# Left panel (UI) and right panel (grid) split 50/50 (L3)
UI_PANEL_RATIO = 0.5  # 700 / 1400

# Region R: fixed size (R2)
REGION_R_SIZE = (150, 150)  # width, height

# =========================
# Symbol library (multiple JPEGs in symbols/ subfolder)
# =========================

SYMBOLS = {
    "p1": r"C:\Users\Naeem\PycharmProjects\CAPSTONE\symbols\symbol_p1.jpg",
    "p2": r"C:\Users\Naeem\PycharmProjects\CAPSTONE\symbols\symbol_p2.jpg",
    "p3": r"C:\Users\Naeem\PycharmProjects\CAPSTONE\symbols\symbol_p3.jpg",
    # Add more as needed
}

current_symbol_name = "p1"

# Grid parameters
COLS = 5
ROWS = 8
TOTAL_BUBBLES = 40

def init_unified_window():
    pygame.init()
    screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Bubble UI + HV507 Visual Simulator (Unified)")
    return screen

# =========================
# 8) Visual simulator drawing (in right panel)
# =========================

def draw_simulator_panel(screen, pattern64, ui_panel_width):
    """
    Draws the 5x8 grid in the right half of the unified window.
    No border (G2).
    """
    width, height = screen.get_size()
    grid_panel_x = ui_panel_width
    grid_panel_width = width - ui_panel_width
    grid_panel_height = height

    # Background for grid panel (slightly different shade)
    grid_bg_color = (25, 25, 25)
    pygame.draw.rect(screen, grid_bg_color,
                     pygame.Rect(grid_panel_x, 0, grid_panel_width, grid_panel_height))

    # Only use first 40 bits
    pattern40 = pattern64[:TOTAL_BUBBLES]

    # Compute cell size based on available space
    cell_width  = grid_panel_width  / COLS
    cell_height = grid_panel_height / ROWS
    cell_size = int(min(cell_width, cell_height))

    # Center grid within the grid panel
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
        pygame.draw.rect(screen, color,
                         (x, y, cell_size - 4, cell_size - 4))

# =========================
# 9) MOCK DRIVER + VISUAL SIMULATOR BACKEND
# =========================

USE_MOCK = True   # <<< SET TO False ON THE REAL PI WITH REAL HARDWARE

class MockHV507:
    def __init__(self):
        self.latched_output = [0] * 64

    def shift_bit(self, bit):
        pass  # Not needed for mock

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
    print("\n[INFO] Running in MOCK MODE — no GPIO used.\n")
    _mock = MockHV507()

    def shift_bit(bit):
        _mock.shift_bit(bit)

    def update_display(pattern64):
        _mock.update_display(pattern64)

    def blank_outputs():
        _mock.blank_outputs()

    def enable_outputs():
        _mock.enable_outputs()

# =========================
# 10) Demo logic (unified window)
# =========================

def demo():
    """
    Live demo in a unified, resizable window:
    - Left panel: Region R + symbol image + cursor tracking.
    - Right panel: 5x8 bubble simulator grid.
    - If cursor stays inside region R for 1 second:
        * Show symbol image.
        * Compute p1_mapped using mapping_function.
        * Wait 1 second.
        * Enable outputs and send p1_mapped to HV507.
        * After 10 seconds, automatically blank outputs.
    """
    global current_symbol_name

    screen = init_unified_window()
    clock = pygame.time.Clock()

    # Load the selected symbol image
    symbol_path = SYMBOLS.get(current_symbol_name)
    try:
        symbol_image = pygame.image.load(symbol_path)
    except Exception:
        print(f"[ERROR] Could not load image: {symbol_path}")
        symbol_image = None

    # State variables
    inside_R_since = None
    symbol_shown = False
    pattern_sent_time = None
    p1_mapped = None
    current_pattern = all_off_64()

    # Ensure outputs start off
    blank_outputs()
    update_display(current_pattern)

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                # Handle window resize
                new_w, new_h = event.w, event.h
                screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                # Simple symbol switching: 1 -> p1, 2 -> p2, 3 -> p3
                if event.key == pygame.K_1:
                    current_symbol_name = "p1"
                elif event.key == pygame.K_2:
                    current_symbol_name = "p2"
                elif event.key == pygame.K_3:
                    current_symbol_name = "p3"

                # Reload image when symbol changes
                symbol_path = SYMBOLS.get(current_symbol_name)
                try:
                    symbol_image = pygame.image.load(symbol_path)
                except Exception:
                    print(f"[ERROR] Could not load image: {symbol_path}")
                    symbol_image = None

        width, height = screen.get_size()
        ui_panel_width = int(width * UI_PANEL_RATIO)

        # Compute Region R position (fixed size, anchored near right side of UI panel)
        region_r_width, region_r_height = REGION_R_SIZE
        region_r_x = ui_panel_width - region_r_width - 50  # 50 px margin from split
        region_r_y = 50  # fixed top margin
        REGION_R = pygame.Rect(region_r_x, region_r_y, region_r_width, region_r_height)

        # Get mouse position
        x, y = pygame.mouse.get_pos()
        cursor_in_R = REGION_R.collidepoint(x, y)

        current_time = time.time()

        # Track how long the cursor has been inside region R
        if cursor_in_R:
            if inside_R_since is None:
                inside_R_since = current_time
        else:
            # If cursor leaves R, reset state and blank outputs
            if symbol_shown or pattern_sent_time is not None:
                blank_outputs()
                current_pattern = all_off_64()
                update_display(current_pattern)

            inside_R_since = None
            symbol_shown = False
            pattern_sent_time = None

        # Check if cursor has been in R for >= 1 second
        if inside_R_since is not None and (current_time - inside_R_since) >= 1.0:
            if not symbol_shown:
                symbol_shown = True

                # Compute mapped pattern
                p1_mapped = apply_mapping(p1, mapping_function)
                current_pattern = p1_mapped

                # Wait 1 second before actuating bubbles
                time.sleep(1.0)

                # Enable outputs and send pattern
                enable_outputs()
                update_display(p1_mapped)
                pattern_sent_time = time.time()

        # Automatically blank outputs 10 seconds after symbol output
        if pattern_sent_time is not None:
            if (current_time - pattern_sent_time) >= 10.0:
                blank_outputs()
                current_pattern = all_off_64()
                update_display(current_pattern)
                pattern_sent_time = None

        # -------------------------
        # Draw unified UI
        # -------------------------
        screen.fill((30, 30, 30))  # Background

        # Left panel background
        pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(0, 0, ui_panel_width, height))

        # Draw Region R
        pygame.draw.rect(screen, (80, 80, 200), REGION_R, 2)

        # ⭐ SCALE IMAGE TO FIT REGION R ⭐
        if symbol_shown and symbol_image is not None:
            img_w, img_h = symbol_image.get_size()
            r_w, r_h = REGION_R_SIZE

            # Scale to fit while preserving aspect ratio
            scale_factor = min(r_w / img_w, r_h / img_h)
            new_size = (int(img_w * scale_factor), int(img_h * scale_factor))

            scaled_img = pygame.transform.smoothscale(symbol_image, new_size)
            scaled_rect = scaled_img.get_rect(center=REGION_R.center)

            screen.blit(scaled_img, scaled_rect)

        # Draw cursor
        pygame.draw.circle(screen, (200, 200, 0), (x, y), 5)

        # Draw simulator grid in right panel using current_pattern
        draw_simulator_panel(screen, current_pattern, ui_panel_width)

        pygame.display.flip()
        clock.tick(60)

    # On exit: blank and clean up
    blank_outputs()
    update_display(all_off_64())
    GPIO.cleanup()
    pygame.quit()

# =========================
# 11) Main entry point
# =========================

if __name__ == "__main__":
    print("______NEW RUN_______")
    try:
        demo()
    except KeyboardInterrupt:
        blank_outputs()
        update_display(all_off_64())
        GPIO.cleanup()
        pygame.quit()
        sys.exit(0)


