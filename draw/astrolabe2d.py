"""2-D astrolabe face: limb, tympan, rete, sun and rule."""
import math
import pygame

from astronomy import (
    stereo, to_screen, ecl_to_equ, hor_to_equ, sun_lon, CAPRICORN_R, OBL, STARS,
)
from .palette import (
    PARCHMENT, BROWN, DARK_BROWN, DIM_GOLD, HORIZ_C, BLUE_EQ, ECLIPTIC_C,
    STAR_C, YELLOW, WHITE, GRAY,
)


class Astrolabe2D:
    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.R = cx, cy, radius
        self.scale = radius / CAPRICORN_R
        self.zoom  = 1.0
        self._font_sm = None
        self._font_hr = None   # hour-ring labels

    def _lazy(self):
        if self._font_sm is None:
            self._font_sm = pygame.font.SysFont("Segoe UI", 10)
        if self._font_hr is None:
            self._font_hr = pygame.font.SysFont("Segoe UI", 11)

    def ts(self, px, py):
        # flip y so north horizon appears at bottom, south at top
        return to_screen(px, -py, self.cx, self.cy, self.scale * self.zoom)

    # ── background ────────────────────────────────────────────────────────────

    def draw_background(self, surf):
        pygame.draw.circle(surf, PARCHMENT, (self.cx, self.cy), self.R)
        pygame.draw.circle(surf, DARK_BROWN, (self.cx, self.cy), self.R, 4)

    def draw_dec_circles(self, surf):
        for dec_deg, color, w in [
            (-OBL, BROWN,   2),
            (  0., BLUE_EQ, 1),
            (+OBL, BROWN,   2),
        ]:
            d    = math.radians(dec_deg)
            r_px = int(abs(math.cos(d) / (1.0 + math.sin(d))) * self.scale * self.zoom)
            pygame.draw.circle(surf, color, (self.cx, self.cy), r_px, w)

    # ── hour ring (limb) ──────────────────────────────────────────────────────

    def draw_hour_ring(self, surf):
        """
        Draw the hour scale on the outer limb.
        Convention after y-flip: HA=0h (south) at TOP, HA=12h (north) at BOTTOM,
        HA=6h (west) at RIGHT, HA=18h (east) at LEFT.
        Formula: sx = cx + sin(h*15°)*r*R,  sy = cy - cos(h*15°)*r*R
        """
        self._lazy()

        # inner border of the limb band
        pygame.draw.circle(surf, DARK_BROWN,
                           (self.cx, self.cy), int(self.R * 0.915), 1)

        for h in range(24):
            ha_r = math.radians(h * 15.0)
            sin_h, cos_h = math.sin(ha_r), math.cos(ha_r)

            # tick lengths
            if h % 6 == 0:           # cardinal hours (0, 6, 12, 18)
                r_in, w = 0.895, 2
            elif h % 2 == 0:         # even hours
                r_in, w = 0.930, 1
            else:                    # odd hours
                r_in, w = 0.950, 1

            r_out = 0.994            # just inside the outer rim stroke

            def pt(r, _s=sin_h, _c=cos_h):
                return (int(self.cx + _s * r * self.R),
                        int(self.cy - _c * r * self.R))

            pygame.draw.line(surf, DARK_BROWN, pt(r_in), pt(r_out), w)

        # half-hour minor ticks
        for hh in range(48):
            ha_r = math.radians(hh * 7.5)
            if hh % 2 == 0:
                continue             # already drawn as hour ticks
            sin_h, cos_h = math.sin(ha_r), math.cos(ha_r)
            r_in = 0.968
            def pt2(r, _s=sin_h, _c=cos_h):
                return (int(self.cx + _s * r * self.R),
                        int(self.cy - _c * r * self.R))
            pygame.draw.line(surf, DARK_BROWN, pt2(r_in), pt2(0.994), 1)

        # labels every 2 hours — show solar time = (HA + 12h) % 24
        for h in range(0, 24, 2):
            ha_r = math.radians(h * 15.0)
            sin_h, cos_h = math.sin(ha_r), math.cos(ha_r)
            lx = int(self.cx + sin_h * 0.865 * self.R)
            ly = int(self.cy - cos_h * 0.865 * self.R)
            label = (h + 12) % 24
            txt = self._font_hr.render(str(label), True, DARK_BROWN)
            tw, th = txt.get_size()
            surf.blit(txt, (lx - tw // 2, ly - th // 2))

    # ── tympan (fixed plate: almucantars + azimuth arcs) ─────────────────────

    def draw_tympan(self, surf, lat_deg):
        # altitude circles (almucantars) every 10°
        for alt in range(0, 91, 10):
            pts = []
            for az_i in range(0, 361, 3):
                ha, dec = hor_to_equ(alt, az_i, lat_deg)
                x, y    = stereo(ha, dec)
                sx, sy  = self.ts(x, y)
                if (sx - self.cx)**2 + (sy - self.cy)**2 <= (self.R + 4)**2:
                    pts.append((sx, sy))
            if len(pts) > 3:
                color = HORIZ_C if alt == 0 else DIM_GOLD
                w     = 2       if alt == 0 else 1
                try:
                    pygame.draw.lines(surf, color, True, pts, w)
                except Exception:
                    pass

        # azimuth arcs every 30°
        for az in range(0, 360, 30):
            pts = []
            for alt_i in range(0, 91, 3):
                ha, dec = hor_to_equ(alt_i, az, lat_deg)
                x, y    = stereo(ha, dec)
                pts.append(self.ts(x, y))
            if len(pts) > 1:
                pygame.draw.lines(surf, DIM_GOLD, False, pts, 1)

    # ── ecliptic scale helpers ────────────────────────────────────────────────

    def _ecl_screen(self, lon_deg, lst_deg):
        """Screen (sx, sy) for ecliptic longitude lon_deg."""
        ra, dec = ecl_to_equ(lon_deg)
        ha = (lst_deg - ra) % 360.0
        return self.ts(*stereo(ha, dec))

    def _ecl_circle_centre(self, lst_deg):
        """Screen-space centre of the ecliptic circle (circumcenter of 3 pts)."""
        p0 = self._ecl_screen(0,   lst_deg)
        p1 = self._ecl_screen(120, lst_deg)
        p2 = self._ecl_screen(240, lst_deg)
        ax, ay = p0;  bx, by = p1;  cx, cy = p2
        D = 2 * (ax*(by - cy) + bx*(cy - ay) + cx*(ay - by))
        if abs(D) < 1e-3:
            return None
        a2 = ax*ax + ay*ay;  b2 = bx*bx + by*by;  c2 = cx*cx + cy*cy
        return ((a2*(by-cy) + b2*(cy-ay) + c2*(ay-by)) / D,
                (a2*(cx-bx) + b2*(ax-cx) + c2*(bx-ax)) / D)

    def draw_ecl_scale(self, surf, lst_deg):
        """Month ticks and labels on the ecliptic ring (rotates with the rete)."""
        self._lazy()

        MONTHS = [("Jan", 1),  ("Feb", 32), ("Mar", 60), ("Apr", 91),
                  ("May",121), ("Jun",152), ("Jul",182), ("Aug",213),
                  ("Sep",244), ("Oct",274), ("Nov",305), ("Dec",335)]

        centre = self._ecl_circle_centre(lst_deg)
        if centre is None:
            return
        ecl_cx, ecl_cy = centre

        def radial(sx, sy):
            dx, dy = sx - ecl_cx, sy - ecl_cy
            d = math.hypot(dx, dy)
            return (dx / d, dy / d) if d > 1e-3 else (0.0, 0.0)

        def in_disk(sx, sy, margin=2):
            return (sx - self.cx)**2 + (sy - self.cy)**2 <= (self.R - margin)**2

        # minor ticks every 5° of ecliptic longitude (skip month boundaries)
        for lon in range(0, 360, 5):
            if lon % 30 == 0:
                continue          # drawn below as major
            sx, sy = self._ecl_screen(lon, lst_deg)
            if not in_disk(sx, sy):
                continue
            nx, ny = radial(sx, sy)
            pygame.draw.line(surf, ECLIPTIC_C,
                             (int(sx - nx*4), int(sy - ny*4)),
                             (int(sx + nx*4), int(sy + ny*4)), 1)

        # month boundaries (major ticks) + month name at midpoint
        for name, day in MONTHS:
            lon_start = sun_lon(day)
            lon_mid   = sun_lon(day + 14)

            # major boundary tick
            sx, sy = self._ecl_screen(lon_start, lst_deg)
            if in_disk(sx, sy):
                nx, ny = radial(sx, sy)
                pygame.draw.line(surf, ECLIPTIC_C,
                                 (int(sx - nx*7), int(sy - ny*7)),
                                 (int(sx + nx*7), int(sy + ny*7)), 2)

            # month label — prefer outward, fall back to inward
            sx_m, sy_m = self._ecl_screen(lon_mid, lst_deg)
            if not in_disk(sx_m, sy_m):
                continue
            nx, ny = radial(sx_m, sy_m)
            for sign in (1, -1):
                lx = int(sx_m + sign * nx * 12)
                ly = int(sy_m + sign * ny * 12)
                if in_disk(lx, ly, 6):
                    txt = self._font_sm.render(name, True, ECLIPTIC_C)
                    tw, th = txt.get_size()
                    surf.blit(txt, (lx - tw//2, ly - th//2))
                    break

    # ── rete (ecliptic ring + scale + stars, rotates with LST) ───────────────

    def draw_rete(self, surf, lst_deg):
        # ecliptic ring
        ecl_pts = []
        for lon in range(0, 361, 2):
            ra, dec = ecl_to_equ(lon)
            ha      = (lst_deg - ra) % 360.0
            x, y    = stereo(ha, dec)
            sx, sy  = self.ts(x, y)
            if (sx - self.cx)**2 + (sy - self.cy)**2 <= (self.R + 10)**2:
                ecl_pts.append((sx, sy))
        if len(ecl_pts) > 3:
            try:
                pygame.draw.lines(surf, ECLIPTIC_C, True, ecl_pts, 2)
            except Exception:
                pass

        # month/day scale on the ecliptic ring
        self.draw_ecl_scale(surf, lst_deg)

        # stars
        self._lazy()
        for name, ra, dec in STARS:
            ha      = (lst_deg - ra) % 360.0
            x, y    = stereo(ha, dec)
            sx, sy  = self.ts(x, y)
            if (sx - self.cx)**2 + (sy - self.cy)**2 <= self.R**2:
                pygame.draw.circle(surf, STAR_C, (sx, sy), 3)
                lbl = self._font_sm.render(name, True, GRAY)
                surf.blit(lbl, (sx + 4, sy - 5))

    # ── sun & rule ────────────────────────────────────────────────────────────

    def draw_sun(self, surf, day, lst_deg):
        """Returns (sx, sy) screen position of the sun."""
        lon    = sun_lon(day)
        ra, dec = ecl_to_equ(lon)
        ha     = (lst_deg - ra) % 360.0
        x, y   = stereo(ha, dec)
        sx, sy = self.ts(x, y)
        pygame.draw.circle(surf, YELLOW, (sx, sy), 10)
        pygame.draw.circle(surf, (255, 160, 20), (sx, sy), 10, 2)
        pygame.draw.circle(surf, (255, 255, 200), (sx, sy), 5)
        return sx, sy

    def draw_rule(self, surf, sun_sx, sun_sy):
        dx, dy = sun_sx - self.cx, sun_sy - self.cy
        d = math.hypot(dx, dy)
        if d < 1:
            return
        ex = int(self.cx + dx * self.R / d)
        ey = int(self.cy + dy * self.R / d)
        pygame.draw.line(surf, (200, 200, 100), (self.cx, self.cy), (ex, ey), 2)

    def draw_pole(self, surf):
        pygame.draw.circle(surf, WHITE, (self.cx, self.cy), 4, 1)

    # ── combined ──────────────────────────────────────────────────────────────

    def draw_all(self, surf, lat_deg, day, lst_deg):
        self.draw_background(surf)
        self.draw_dec_circles(surf)
        self.draw_hour_ring(surf)
        self.draw_tympan(surf, lat_deg)
        self.draw_rete(surf, lst_deg)
        sx, sy = self.draw_sun(surf, day, lst_deg)
        self.draw_rule(surf, sx, sy)
        self.draw_pole(surf)
