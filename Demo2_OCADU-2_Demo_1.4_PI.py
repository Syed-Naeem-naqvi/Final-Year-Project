import sys
import time
import math
import pygame
import os
import RPi.GPIO as GPIO


# =========================
# 1) GPIO setup (Raspberry Pi)
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
# 2) HV507 driver
# =========================

def shift_bit(bit):
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

    print("\n[HV507] Latched 64-bit pattern:")
    print("".join(str(b) for b in pattern64))

def blank_outputs():
    GPIO.output(BL, 0)
    print("[HV507] BLANK outputs")

def enable_outputs():
    GPIO.output(BL, 1)
    print("[HV507] ENABLE outputs")

def all_off_64():
    return [0] * 64


# =========================
# 3) UI config
# =========================

WIN_WIDTH  = 850
WIN_HEIGHT = 700

ROWS = 8
COLS = 5

GRID_TOP_MARGIN    = 120
GRID_BOTTOM_MARGIN = 200
GRID_SIDE_MARGIN   = 80

COLOR_BG           = (10, 10, 15)
COLOR_GRID_BG      = (20, 20, 30)
COLOR_CELL_OFF     = (60, 60, 70)
COLOR_BUTTON_TEXT  = (230, 230, 230)

COLOR_BUTTON_START = (0, 160, 120)
COLOR_BUTTON_STOP  = (200, 80, 40)
COLOR_BUTTON_CLEAR = (80, 80, 200)
COLOR_BUTTON_KILL  = (200, 40, 40)

COLOR_NEON_CYAN        = (0, 200, 255)
COLOR_NEON_CYAN_SOFT   = (0, 120, 180)
COLOR_TITLE            = (255, 255, 255)

BUTTON_HEIGHT = 55
BUTTON_WIDTH  = 260
BUTTON_MARGIN = 30


ASCII_BANNER = r"""
                        O  C  A  D  U  -  2
"""


# =========================
# 4) Splash screen
# =========================

def run_splash_screen(screen, clock):
    width, height = screen.get_size()
    font_big = pygame.font.SysFont("consolas", 72, bold=True)
    font_small = pygame.font.SysFont("consolas", 32)

    title = font_big.render("OCADU-2", True, (255, 255, 255))
    subtitle = font_small.render("Demo V1.4", True, (180, 180, 180))

    title_rect = title.get_rect(center=(width // 2, height // 2 - 20))
    subtitle_rect = subtitle.get_rect(center=(width // 2, height // 2 + 40))

    fade_in_time = 300
    hold_time = 400
    fade_out_time = 300
    total_time = fade_in_time + hold_time + fade_out_time

    start_ticks = pygame.time.get_ticks()

    while True:
        now = pygame.time.get_ticks() - start_ticks
        if now >= total_time:
            break

        if now < fade_in_time:
            alpha = int((now / fade_in_time) * 255)
        elif now < fade_in_time + hold_time:
            alpha = 255
        else:
            t = now - (fade_in_time + hold_time)
            alpha = int(255 * (1 - (t / fade_out_time)))

        screen.fill((10, 10, 15))

        title_surf = title.copy()
        subtitle_surf = subtitle.copy()
        title_surf.set_alpha(alpha)
        subtitle_surf.set_alpha(alpha)

        screen.blit(title_surf, title_rect)
        screen.blit(subtitle_surf, subtitle_rect)

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)


# =========================
# 5) Glow helpers
# =========================

def draw_glow_text(surface, text, font, center_x, y, color, glow_color):
    label = font.render(text, True, color)
    text_rect = label.get_rect()
    x = center_x - text_rect.width // 2

    outline = font.render(text, True, (0, 0, 0))
    surface.blit(outline, (x-1, y))
    surface.blit(outline, (x+1, y))
    surface.blit(outline, (x, y-1))
    surface.blit(outline, (x, y+1))

    for offset in range(1, 3):
        glow = font.render(text, True, glow_color)
        surface.blit(glow, (x - offset, y))
        surface.blit(glow, (x + offset, y))
        surface.blit(glow, (x, y - offset))
        surface.blit(glow, (x, y + offset))

    surface.blit(label, (x, y))


def draw_tooltip(surface, text, font, x, y):
    text = f"‹ {text} ›"
    label = font.render(text, True, (255, 255, 255))
    padding = 8
    bg_rect = pygame.Rect(
        x - padding,
        y - padding,
        label.get_width() + padding * 2,
        label.get_height() + padding * 2
    )
    pygame.draw.rect(surface, (30, 30, 40), bg_rect, border_radius=6)
    pygame.draw.rect(surface, COLOR_NEON_CYAN, bg_rect, width=2, border_radius=6)
    surface.blit(label, (x, y))


def draw_portal_button(surface, rect, text, font, base_color, glow_color, hover):
    pygame.draw.rect(surface, base_color, rect, border_radius=10)

    outline_color = glow_color if hover else (
        glow_color[0] // 3, glow_color[1] // 3, glow_color[2] // 3
    )
    pygame.draw.rect(surface, outline_color, rect, width=4, border_radius=10)

    if hover:
        for g in range(1, 3):
            inflated = rect.inflate(g * 3, g * 3)
            pygame.draw.rect(surface, outline_color, inflated, width=1, border_radius=12)

    label = font.render(text, True, COLOR_BUTTON_TEXT)
    label_rect = label.get_rect(center=rect.center)
    surface.blit(label, label_rect)


def draw_glowing_circle(surface, cx, cy, radius, on):
    if on:
        for g in range(1, 3):
            pygame.draw.circle(surface, COLOR_NEON_CYAN_SOFT, (cx, cy), radius + g * 2, width=1)
        pygame.draw.circle(surface, COLOR_NEON_CYAN, (cx, cy), radius, width=3)
        pygame.draw.circle(surface, (240, 240, 255), (cx, cy), radius - 3)
    else:
        pygame.draw.circle(surface, COLOR_CELL_OFF, (cx, cy), radius)


def draw_hover_highlight(surface, cx, cy, radius):
    pygame.draw.circle(surface, COLOR_NEON_CYAN_SOFT, (cx, cy), radius + 6, width=2)


# =========================
# 6) Button class
# =========================

class Button:
    def __init__(self, rect, text, base_color, glow_color, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.base_color = base_color
        self.glow_color = glow_color
        self.font = font
        self.press_timer = 0
        self.press_duration = 5

    def draw(self, surface, hover):
        if self.press_timer > 0:
            shrink = 0.95
            new_w = int(self.rect.width * shrink)
            new_h = int(self.rect.height * shrink)
            dx = (self.rect.width - new_w) // 2
            dy = (self.rect.height - new_h) // 2
            anim_rect = pygame.Rect(
                self.rect.x + dx,
                self.rect.y + dy,
                new_w,
                new_h
            )
        else:
            anim_rect = self.rect

        draw_portal_button(surface, anim_rect, self.text, self.font,
                           self.base_color, self.glow_color, hover)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

    def trigger_press(self):
        self.press_timer = self.press_duration


# =========================
# 7) Grid class
# =========================

class CircularGrid:
    def __init__(self, rows, cols, area_rect):
        self.rows = rows
        self.cols = cols
        self.area_rect = area_rect
        self.pattern = [0] * (rows * cols)
        self.circles = []
        self._compute_geometry()

    def _compute_geometry(self):
        x0, y0, w, h = self.area_rect
        gap = 6

        r_max_x = (w - gap * (self.cols - 1)) / (2 * self.cols)
        r_max_y = (h - gap * (self.rows - 1)) / (2 * self.rows)
        radius = int(max(4, min(r_max_x, r_max_y)))

        total_w = 2 * radius * self.cols + gap * (self.cols - 1)
        total_h = 2 * radius * self.rows + gap * (self.rows - 1)

        start_x = x0 + (w - total_w) / 2
        start_y = y0 + (h - total_h) / 2

        self.circles = []
        for r in range(self.rows):
            for c in range(self.cols):
                cx = int(start_x + c * (2 * radius + gap) + radius)
                cy = int(start_y + r * (2 * radius + gap) + radius)
                self.circles.append((cx, cy, radius))

    def draw(self, surface, mouse_pos, editing_mode):
        pygame.draw.rect(surface, COLOR_GRID_BG, self.area_rect)

        if editing_mode:
            mx, my = mouse_pos
            for cx, cy, radius in self.circles:
                if (mx - cx)**2 + (my - cy)**2 <= radius**2:
                    draw_hover_highlight(surface, cx, cy, radius)
                    break

        for idx, (cx, cy, radius) in enumerate(self.circles):
            draw_glowing_circle(surface, cx, cy, radius, self.pattern[idx] == 1)

    def toggle_at_pos(self, pos):
        x, y = pos
        for idx, (cx, cy, radius) in enumerate(self.circles):
            if (x - cx)**2 + (y - cy)**2 <= radius**2:
                self.pattern[idx] ^= 1
                return True
        return False

    def get_pattern40(self):
        return list(self.pattern)

    def clear(self):
        self.pattern = [0] * (self.rows * self.cols)


# =========================
# 8) UI → HV507 mapping (0‑based)
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
# =========================
# 9) Main demo
# =========================

def demo():
    print(ASCII_BANNER)

    pygame.init()
    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("OCADU-2 — Demo V1.4")
    clock = pygame.time.Clock()

    run_splash_screen(screen, clock)

    font = pygame.font.SysFont("consolas", 24)
    title_font = pygame.font.SysFont("consolas", 56, bold=True)

    def compute_grid_rect():
        width, height = screen.get_size()
        return pygame.Rect(
            GRID_SIDE_MARGIN,
            GRID_TOP_MARGIN,
            width - 2 * GRID_SIDE_MARGIN,
            height - GRID_TOP_MARGIN - GRID_BOTTOM_MARGIN
        )

    grid_rect = compute_grid_rect()
    grid = CircularGrid(ROWS, COLS, grid_rect)

    def compute_buttons():
        width, height = screen.get_size()
        y = height - BUTTON_HEIGHT - 40
        total_width = 4 * BUTTON_WIDTH + 3 * BUTTON_MARGIN
        start_x = (width - total_width) // 2

        return (
            (start_x, y, BUTTON_WIDTH, BUTTON_HEIGHT),
            (start_x + (BUTTON_WIDTH + BUTTON_MARGIN), y, BUTTON_WIDTH, BUTTON_HEIGHT),
            (start_x + 2 * (BUTTON_WIDTH + BUTTON_MARGIN), y, BUTTON_WIDTH, BUTTON_HEIGHT),
            (start_x + 3 * (BUTTON_WIDTH + BUTTON_MARGIN), y, BUTTON_WIDTH, BUTTON_HEIGHT),
        )

    start_rect, display_rect, clear_rect, kill_rect = compute_buttons()

    reading_active = False
    error_flash_timer = 0

    start_button = Button(start_rect, "Start Reading", COLOR_BUTTON_START, COLOR_NEON_CYAN, font)
    display_button = Button(display_rect, "Display", COLOR_BUTTON_CLEAR, COLOR_NEON_CYAN, font)
    clear_button = Button(clear_rect, "Clear Pattern", COLOR_BUTTON_CLEAR, COLOR_NEON_CYAN, font)
    kill_button = Button(kill_rect, "KILL SWITCH", COLOR_BUTTON_KILL, COLOR_NEON_CYAN, font)

    blank_outputs()
    update_display(all_off_64())

    running = True
    mouse_pos = (0, 0)

    while running:
        if error_flash_timer > 0:
            error_flash_timer -= 1

        if start_button.press_timer > 0:
            start_button.press_timer -= 1
        if display_button.press_timer > 0:
            display_button.press_timer -= 1
        if clear_button.press_timer > 0:
            clear_button.press_timer -= 1
        if kill_button.press_timer > 0:
            kill_button.press_timer -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                grid_rect = compute_grid_rect()
                grid.area_rect = grid_rect
                grid._compute_geometry()
                start_rect, display_rect, clear_rect, kill_rect = compute_buttons()
                start_button.rect = pygame.Rect(start_rect)
                display_button.rect = pygame.Rect(display_rect)
                clear_button.rect = pygame.Rect(clear_rect)
                kill_button.rect = pygame.Rect(kill_rect)

            elif event.type == pygame.MOUSEMOTION:
                mouse_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos

                # KILL SWITCH
                if kill_button.is_clicked(mouse_pos):
                    kill_button.trigger_press()
                    print("[KILL SWITCH] Emergency shutdown.")
                    blank_outputs()
                    update_display(all_off_64())
                    GPIO.cleanup()
                    pygame.quit()
                    sys.exit(0)

                # Start/Stop Reading
                elif start_button.is_clicked(mouse_pos):
                    start_button.trigger_press()
                    reading_active = not reading_active
                    start_button.text = "Stop Reading" if reading_active else "Start Reading"
                    start_button.base_color = COLOR_BUTTON_STOP if reading_active else COLOR_BUTTON_START

                # Display (with mapping)
                elif display_button.is_clicked(mouse_pos):
                    display_button.trigger_press()
                    if reading_active:
                        print("[UI] Cannot display while in editing mode.")
                        error_flash_timer = 10
                    else:
                        pattern40 = grid.get_pattern40()

                        mapped = [0] * 64
                        for ui_index, hv_pin in enumerate(UI_TO_HV):
                            mapped[hv_pin] = pattern40[ui_index]

                        enable_outputs()
                        update_display(mapped)

                # Clear pattern
                elif clear_button.is_clicked(mouse_pos):
                    clear_button.trigger_press()
                    if reading_active:
                        grid.clear()

                # Toggle grid bubble
                elif reading_active:
                    grid.toggle_at_pos(mouse_pos)

        # Draw UI
        screen.fill(COLOR_BG)

        width, _ = screen.get_size()
        draw_glow_text(screen, "OCADU-2", title_font, width // 2, 20,
                       COLOR_TITLE, COLOR_NEON_CYAN_SOFT)

        grid.draw(screen, mouse_pos, reading_active)

        hover_start   = start_button.rect.collidepoint(mouse_pos)
        hover_display = display_button.rect.collidepoint(mouse_pos)
        hover_clear   = clear_button.rect.collidepoint(mouse_pos)
        hover_kill    = kill_button.rect.collidepoint(mouse_pos)

        start_button.draw(screen, hover_start)

        if error_flash_timer > 0:
            old_color = display_button.base_color
            display_button.base_color = (200, 40, 40)
            display_button.draw(screen, False)
            display_button.base_color = old_color
        else:
            display_button.draw(screen, hover_display)

        clear_button.draw(screen, hover_clear)
        kill_button.draw(screen, hover_kill)

        if reading_active and hover_display:
            draw_tooltip(
                screen,
                "Exit editing mode to display",
                font,
                display_button.rect.centerx - 110,
                display_button.rect.top - 40
            )

        pygame.display.flip()
        clock.tick(60)

    # On exit: blank HV outputs safely
    blank_outputs()
    update_display(all_off_64())
    GPIO.cleanup()
    pygame.quit()


# =========================
# 10) Entry point
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
