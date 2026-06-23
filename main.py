"""
Interactive Astrolabe — main entry point.
Run with:  D:\\producto\\miniconda3\\python.exe main.py

Controls:
  Drag astrolabe   — rotate the rete (advance / retard LST)
  ← → arrows       — change date by 1 day
  ↑ ↓ arrows       — change latitude by 1°
  , / .            — advance / retard LST by 1 hour
  Drag 3D panel    — rotate 3D view (azimuth / elevation)
  ESC              — quit
"""
import sys
import math
import pygame

from astronomy import sun_lon, ecl_to_equ, equ_to_hor
from draw import Astrolabe2D, View3D, SundialWall

# ── layout ────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1650, 720
SPLIT         = 615          # 2D | 3D divider
SPLIT2        = 1165         # 3D | sundial-top divider

ASTRO_CX, ASTRO_CY, ASTRO_R = 308, 330, 272

VIEW3_CX = (SPLIT + SPLIT2) // 2    # 890
VIEW3_CY = 330
VIEW3_R  = 235

DIAL_CX  = (SPLIT2 + WIDTH) // 2   # 1407
DIAL_CY  = 330
DIAL_R   = 210

CTRL_Y   = 645               # y of control strip

# ── colour ────────────────────────────────────────────────────────────────────
BG   = (12, 12, 22)
GRAY = (145, 145, 160)
HINT = ( 70,  70,  95)
YELLOW = (255, 215, 35)

# ── calendar helpers ──────────────────────────────────────────────────────────
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec"]
M_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]

def day_str(d):
    d = max(1, min(365, d))
    for m in range(12):
        if M_DAYS[m] < d <= M_DAYS[m + 1]:
            return f"{d - M_DAYS[m]} {MONTHS[m]}"
    return f"Day {d}"

# ── pygame init ───────────────────────────────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Interactive Astrolabe")
clock  = pygame.time.Clock()

font    = pygame.font.SysFont("Segoe UI", 14)
font_lg = pygame.font.SysFont("Segoe UI", 16, bold=True)

astro     = Astrolabe2D(ASTRO_CX, ASTRO_CY, ASTRO_R)
view3     = View3D(VIEW3_CX, VIEW3_CY, VIEW3_R)
dial_wall = SundialWall(DIAL_CX, DIAL_CY, DIAL_R)

# ── state ─────────────────────────────────────────────────────────────────────
latitude    = 41.0   # Madrid
day_of_year = 172    # ~21 Jun (summer solstice)
lst_deg     = 0.0    # Local Sidereal Time in degrees (0–360)

# rete drag
dragging_rete  = False
drag_ang0      = 0.0
drag_lst0      = 0.0

# 3D drag
dragging_3d    = False
drag_xy0       = (0, 0)
drag_cam0      = (0.0, 0.0)

# sliders
LAT_RECT = pygame.Rect(40,  CTRL_Y, 220, 12)
DAY_RECT = pygame.Rect(310, CTRL_Y, 220, 12)
LST_RECT = pygame.Rect(580, CTRL_Y, 220, 12)
active_slider = None

# ── helpers ───────────────────────────────────────────────────────────────────

def ang_from(mx, my, cx, cy):
    return math.degrees(math.atan2(my - cy, mx - cx))

def in_circle(mx, my, cx, cy, r):
    return (mx - cx)**2 + (my - cy)**2 <= r * r

def slider_v(rect, mx, lo, hi):
    t = max(0.0, min(1.0, (mx - rect.x) / rect.width))
    return lo + t * (hi - lo)

def draw_slider(surf, rect, val, lo, hi, label):
    pygame.draw.rect(surf, (40, 40, 62), rect, border_radius=3)
    t  = (val - lo) / (hi - lo)
    kx = int(rect.x + t * rect.width)
    pygame.draw.circle(surf, (190, 150, 60), (kx, rect.centery), 9)
    surf.blit(font.render(label, True, GRAY), (rect.x, rect.y - 18))

def draw_legend(surf, x, y):
    """3D view legend."""
    items = [
        ((80, 120, 210), "Celestial equator"),
        ((210, 60, 50),  "Ecliptic"),
        ((210, 180, 60), "Horizon"),
        ((255, 215, 35), "Sun"),
        ((190, 165, 100),"Gnomon (sundial)"),
        ((70, 50, 15),   "Shadow"),
    ]
    for i, (color, text) in enumerate(items):
        pygame.draw.rect(surf, color, (x, y + i*17, 12, 10))
        surf.blit(font.render(text, True, GRAY), (x + 16, y + i*17 - 1))

def draw_sun_info(surf, lat_deg, day, lst_deg, x, y):
    """Display Sun azimuth & elevation in the local frame."""
    lon           = sun_lon(day)
    ra_sun, dec_sun = ecl_to_equ(lon)
    ha_sun        = (lst_deg - ra_sun) % 360.0
    alt_sun, az_sun = equ_to_hor(ha_sun, dec_sun, lat_deg)

    lines = [
        ("Sun — local position", YELLOW),
        (f"  Azimuth (N→E):  {az_sun:6.1f}°", GRAY),
        (f"  Elevation:       {alt_sun:6.1f}°", GRAY),
    ]
    for i, (text, color) in enumerate(lines):
        f_ = font_lg if i == 0 else font
        surf.blit(f_.render(text, True, color), (x, y + i * 19))

# ── main loop ─────────────────────────────────────────────────────────────────
if __name__ != '__main__':
    pygame.quit()
    raise SystemExit("main.py is not a library — run it directly.")

running = True
while running:
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False

        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.key == pygame.K_UP:
                latitude = min(89, latitude + 1)
            elif ev.key == pygame.K_DOWN:
                latitude = max(-89, latitude - 1)
            elif ev.key == pygame.K_RIGHT:
                day_of_year = min(365, day_of_year + 1)
            elif ev.key == pygame.K_LEFT:
                day_of_year = max(1, day_of_year - 1)
            elif ev.key == pygame.K_COMMA:      # , → step back 1 hour
                lst_deg = (lst_deg - 15.0) % 360
            elif ev.key == pygame.K_PERIOD:     # . → step forward 1 hour
                lst_deg = (lst_deg + 15.0) % 360

        elif ev.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            factor = 1.12 ** ev.y
            if mx < SPLIT:
                astro.zoom    = max(0.25, min(6.0, astro.zoom    * factor))
            elif mx < SPLIT2:
                view3.zoom    = max(0.25, min(6.0, view3.zoom    * factor))
            else:
                dial_wall.zoom = max(0.25, min(6.0, dial_wall.zoom * factor))

        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 2:
            mx, my = ev.pos
            if mx < SPLIT:
                astro.zoom    = 1.0
            elif mx < SPLIT2:
                view3.zoom    = 1.0
            else:
                dial_wall.zoom = 1.0

        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            if LAT_RECT.inflate(0, 24).collidepoint(mx, my):
                active_slider = "lat"
            elif DAY_RECT.inflate(0, 24).collidepoint(mx, my):
                active_slider = "day"
            elif LST_RECT.inflate(0, 24).collidepoint(mx, my):
                active_slider = "lst"
            elif in_circle(mx, my, ASTRO_CX, ASTRO_CY, ASTRO_R):
                dragging_rete = True
                drag_ang0     = ang_from(mx, my, ASTRO_CX, ASTRO_CY)
                drag_lst0     = lst_deg
            elif mx > SPLIT:
                dragging_3d  = True
                drag_xy0     = (mx, my)
                drag_cam0    = (view3.cam_azi, view3.cam_elv)

        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            dragging_rete = dragging_3d = False
            active_slider = None

        elif ev.type == pygame.MOUSEMOTION:
            mx, my = ev.pos
            if active_slider == "lat":
                latitude = float(round(max(-89.0,
                                           min(89.0, slider_v(LAT_RECT, mx, -89, 89)))))
            elif active_slider == "day":
                day_of_year = int(max(1, min(365, slider_v(DAY_RECT, mx, 1, 365))))
            elif active_slider == "lst":
                sol_t = slider_v(LST_RECT, mx, 0, 24)
                ra_sun, _ = ecl_to_equ(sun_lon(day_of_year))
                lst_deg = (ra_sun + (sol_t - 12.0) * 15.0) % 360
            elif dragging_rete:
                cur     = ang_from(mx, my, ASTRO_CX, ASTRO_CY)
                lst_deg = (drag_lst0 + (cur - drag_ang0)) % 360
            elif dragging_3d:
                dx           = mx - drag_xy0[0]
                dy           = my - drag_xy0[1]
                view3.cam_azi = (drag_cam0[0] + dx * 0.5) % 360
                view3.cam_elv = max(-89, min(89, drag_cam0[1] - dy * 0.3))

    # ── render ────────────────────────────────────────────────────────────────
    screen.fill(BG)

    # panel dividers
    pygame.draw.line(screen, (35, 35, 55), (SPLIT,  0), (SPLIT,  HEIGHT), 1)
    pygame.draw.line(screen, (35, 35, 55), (SPLIT2, 0), (SPLIT2, HEIGHT), 1)

    # 2-D astrolabe (left panel)
    astro.draw_all(screen, latitude, day_of_year, lst_deg)

    # 3-D view (centre panel)
    view3.draw_all(screen, latitude, day_of_year, lst_deg)

    # sundial top-down view (right panel)
    dial_wall.draw_all(screen, latitude, day_of_year, lst_deg)

    # legend (top-right)
    draw_legend(screen, SPLIT + 14, 14)

    # Sun azimuth / elevation info (right panel, below legend)
    draw_sun_info(screen, latitude, day_of_year, lst_deg, SPLIT + 14, 135)

    # control strip
    pygame.draw.rect(screen, (14, 14, 28), (0, CTRL_Y - 22, WIDTH, HEIGHT - (CTRL_Y - 22)))

    draw_slider(screen, LAT_RECT, latitude, -89, 89,
                f"Latitude: {latitude:.0f}°")
    draw_slider(screen, DAY_RECT, day_of_year, 1, 365,
                f"Date: {day_str(day_of_year)}")

    ra_sun, _ = ecl_to_equ(sun_lon(day_of_year))
    sol_t = (12.0 + (lst_deg - ra_sun) / 15.0) % 24.0
    lst_label = f"Solar time: {int(sol_t):02d}h {int((sol_t % 1) * 60):02d}m"
    draw_slider(screen, LST_RECT, sol_t, 0, 24, lst_label)

    screen.blit(font.render(
        "↑↓ latitude  ·  ←→ date  ·  drag rete = rotate  ·  , . time +/-1h  ·  drag 3D = rotate view",
        True, HINT), (10, HEIGHT - 22))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
