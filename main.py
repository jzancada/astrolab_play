"""
Interactive Astrolabe — main entry point.
Run with:  D:\\producto\\miniconda3\\python.exe main.py

2x2 panels:
  top-left     2D astrolabe          top-right    3D celestial sphere + wall
  bottom-left  south wall sundial    bottom-right heliocentric (orrery)

Controls:
  Drag astrolabe   — rotate the rete (advance / retard LST)
  ← → arrows       — change date by 1 day
  ↑ ↓ arrows       — change latitude by 1°
  , / .            — advance / retard LST by 1 hour
  Drag 3D / orrery — rotate that view
  Wheel            — zoom the panel under the cursor (middle-click = reset)
  ESC              — quit
"""
import sys
import math
import pygame

from astronomy import sun_lon, ecl_to_equ, equ_to_hor
from draw import Astrolabe2D, View3D, SundialWall, Heliocentric

# ── layout (2x2 grid) ──────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1645, 1115
VDIV  = 825          # vertical divider (left | right)
HDIV  = 545          # horizontal divider (top | bottom)

ASTRO_CX, ASTRO_CY, ASTRO_R = 415, 290, 250      # top-left
VIEW3_CX, VIEW3_CY, VIEW3_R = 1230, 290, 235     # top-right
DIAL_CX,  DIAL_CY,  DIAL_R  = 415, 790, 200      # bottom-left
HELIO_CX, HELIO_CY, HELIO_R = 1230, 790, 235     # bottom-right

CTRL_TOP = 1015              # top of control strip
LAT_Y    = 1042
LON_Y    = 1076

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
helio     = Heliocentric(HELIO_CX, HELIO_CY, HELIO_R)

# ── state ─────────────────────────────────────────────────────────────────────
latitude    = 41.0   # Madrid
longitude   = 0.0    # observer longitude (places the wall on the globe)
day_of_year = 172    # ~21 Jun (summer solstice)
lst_deg     = 0.0    # Local Sidereal Time in degrees (0–360)

# rete drag
dragging_rete  = False
drag_ang0      = 0.0
drag_lst0      = 0.0

# camera drags (3D view and orrery)
dragging_3d    = False
dragging_helio = False
drag_xy0       = (0, 0)
drag_cam0      = (0.0, 0.0)

# sliders
LAT_RECT = pygame.Rect(40,  LAT_Y, 220, 12)
LON_RECT = pygame.Rect(40,  LON_Y, 220, 12)
DAY_RECT = pygame.Rect(330, LAT_Y, 220, 12)
LST_RECT = pygame.Rect(620, LAT_Y, 220, 12)
active_slider = None

# ── helpers ───────────────────────────────────────────────────────────────────

def ang_from(mx, my, cx, cy):
    return math.degrees(math.atan2(my - cy, mx - cx))

def in_circle(mx, my, cx, cy, r):
    return (mx - cx)**2 + (my - cy)**2 <= r * r

def slider_v(rect, mx, lo, hi):
    t = max(0.0, min(1.0, (mx - rect.x) / rect.width))
    return lo + t * (hi - lo)

def panel_obj(mx, my):
    """Return the panel object under (mx, my), or None if in the control strip."""
    if my >= CTRL_TOP:
        return None
    if mx < VDIV:
        return astro if my < HDIV else dial_wall
    return view3 if my < HDIV else helio

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
            obj = panel_obj(mx, my)
            if obj is not None:
                obj.zoom = max(0.25, min(8.0, obj.zoom * 1.12 ** ev.y))

        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 2:
            obj = panel_obj(*ev.pos)
            if obj is not None:
                obj.zoom = 1.0

        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            if LAT_RECT.inflate(0, 24).collidepoint(mx, my):
                active_slider = "lat"
            elif LON_RECT.inflate(0, 24).collidepoint(mx, my):
                active_slider = "lon"
            elif DAY_RECT.inflate(0, 24).collidepoint(mx, my):
                active_slider = "day"
            elif LST_RECT.inflate(0, 24).collidepoint(mx, my):
                active_slider = "lst"
            elif in_circle(mx, my, ASTRO_CX, ASTRO_CY, ASTRO_R):
                dragging_rete = True
                drag_ang0     = ang_from(mx, my, ASTRO_CX, ASTRO_CY)
                drag_lst0     = lst_deg
            else:
                obj = panel_obj(mx, my)
                if obj is view3:
                    dragging_3d = True
                    drag_xy0    = (mx, my)
                    drag_cam0   = (view3.cam_azi, view3.cam_elv)
                elif obj is helio:
                    dragging_helio = True
                    drag_xy0       = (mx, my)
                    drag_cam0      = (helio.cam_azi, helio.cam_elv)

        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            dragging_rete = dragging_3d = dragging_helio = False
            active_slider = None

        elif ev.type == pygame.MOUSEMOTION:
            mx, my = ev.pos
            if active_slider == "lat":
                latitude = float(round(max(-89.0,
                                           min(89.0, slider_v(LAT_RECT, mx, -89, 89)))))
            elif active_slider == "lon":
                longitude = float(round(max(-180.0,
                                            min(180.0, slider_v(LON_RECT, mx, -180, 180)))))
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
                dx = mx - drag_xy0[0]
                dy = my - drag_xy0[1]
                view3.cam_azi = (drag_cam0[0] + dx * 0.5) % 360
                view3.cam_elv = max(-89, min(89, drag_cam0[1] - dy * 0.3))
            elif dragging_helio:
                dx = mx - drag_xy0[0]
                dy = my - drag_xy0[1]
                helio.cam_azi = (drag_cam0[0] + dx * 0.5) % 360
                helio.cam_elv = max(-89, min(89, drag_cam0[1] - dy * 0.3))

    # ── render ────────────────────────────────────────────────────────────────
    screen.fill(BG)

    # panel dividers
    pygame.draw.line(screen, (35, 35, 55), (VDIV, 0), (VDIV, CTRL_TOP), 1)
    pygame.draw.line(screen, (35, 35, 55), (0, HDIV), (WIDTH, HDIV), 1)

    # each panel is clipped to its quadrant so a zoomed view can't bleed over
    for rect, draw in (
        (pygame.Rect(0, 0, VDIV, HDIV),
         lambda: astro.draw_all(screen, latitude, day_of_year, lst_deg)),
        (pygame.Rect(VDIV, 0, WIDTH - VDIV, HDIV),
         lambda: view3.draw_all(screen, latitude, day_of_year, lst_deg)),
        (pygame.Rect(0, HDIV, VDIV, CTRL_TOP - HDIV),
         lambda: dial_wall.draw_all(screen, latitude, day_of_year, lst_deg)),
        (pygame.Rect(VDIV, HDIV, WIDTH - VDIV, CTRL_TOP - HDIV),
         lambda: helio.draw_all(screen, latitude, day_of_year, lst_deg, longitude)),
    ):
        screen.set_clip(rect)
        draw()
    screen.set_clip(None)

    # legend + sun info (top-right panel)
    draw_legend(screen, VDIV + 14, 14)
    draw_sun_info(screen, latitude, day_of_year, lst_deg, VDIV + 14, 135)

    # control strip
    pygame.draw.rect(screen, (14, 14, 28), (0, CTRL_TOP, WIDTH, HEIGHT - CTRL_TOP))

    draw_slider(screen, LAT_RECT, latitude, -89, 89,
                f"Latitude: {latitude:.0f}°")
    draw_slider(screen, LON_RECT, longitude, -180, 180,
                f"Longitude: {longitude:.0f}°")
    draw_slider(screen, DAY_RECT, day_of_year, 1, 365,
                f"Date: {day_str(day_of_year)}")

    ra_sun, _ = ecl_to_equ(sun_lon(day_of_year))
    sol_t = (12.0 + (lst_deg - ra_sun) / 15.0) % 24.0
    lst_label = f"Solar time: {int(sol_t):02d}h {int((sol_t % 1) * 60):02d}m"
    draw_slider(screen, LST_RECT, sol_t, 0, 24, lst_label)

    screen.blit(font.render(
        "↑↓ latitude  ·  ←→ date  ·  drag rete = rotate  ·  , . time +/-1h  ·  "
        "drag 3D / orrery = rotate  ·  wheel = zoom panel",
        True, HINT), (10, HEIGHT - 20))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
