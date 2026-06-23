"""Vertical south-facing wall sundial, viewed face-on."""
import math
import pygame

from astronomy import sun_lon, ecl_to_equ, equ_to_hor
from .palette import DARK_BROWN, GRAY


class SundialWall:
    """
    Vertical south-facing wall sundial, viewed face-on from the south.
    Orientation: East = right, Up = up.
    Gnomon: perpendicular to wall, pointing southward (toward viewer).
    Hour lines: tan(θ) = sin(lat) × tan(H×15°)  [direct-south formula].
    """

    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.R = cx, cy, radius
        self.scale = radius / 1.2
        self.zoom  = 1.0
        self._font    = None
        self._font_sm = None

    def _lazy(self):
        if self._font is None:
            self._font    = pygame.font.SysFont("Segoe UI", 13, bold=True)
            self._font_sm = pygame.font.SysFont("Segoe UI", 10)

    def _shadow_eu(self, sol_t, day, lat_deg):
        """
        (East, Up) of shadow tip on the south wall face.
        Polar gnomon (parallel to Earth's axis):
          - attachment on wall face: (E=0, N=0, U=g·sin(lat))  above dial centre
          - casting end (free tip): (E=0, N=-g·cos(lat), U=0)  in front of wall
        Shadow exists only when sn < 0 (sun in southern sky).
        """
        lon = sun_lon(day)
        ra_sun, dec_sun = ecl_to_equ(lon)
        lst_t  = (ra_sun + (sol_t - 12.0) * 15.0) % 360.0
        ha_sun = (lst_t - ra_sun) % 360.0
        alt, az = equ_to_hor(ha_sun, dec_sun, lat_deg)
        if alt <= 0.3:
            return None
        alt_r, az_r = math.radians(alt), math.radians(az)
        se = math.cos(alt_r) * math.sin(az_r)
        sn = math.cos(alt_r) * math.cos(az_r)
        su = math.sin(alt_r)
        if sn >= -1e-6:
            return None   # sun in northern sky — no shadow on south face
        g_len = 0.3
        c_lat = math.cos(math.radians(lat_deg))
        # casting end at (0, -g_len·cos(lat), 0); projects to wall-centre in face-on view
        # t = -g_tip_N / sn = g_len·cos(lat) / |sn|  > 0
        t = -g_len * c_lat / sn
        return -t * se, -t * su   # (shadow_E, shadow_U); shadow_U < 0

    def _pt(self, e, u):
        """(East, Up) → screen pixel.  East = right, Up = up."""
        s = self.scale * self.zoom
        return int(self.cx + e * s), int(self.cy - u * s)

    def _in_disk(self, sx, sy, margin=2):
        return (sx - self.cx)**2 + (sy - self.cy)**2 <= (self.R - margin)**2

    def _clip(self, sx, sy):
        dx, dy = sx - self.cx, sy - self.cy
        d = math.sqrt(dx*dx + dy*dy)
        if d <= self.R - 2:
            return sx, sy
        f = (self.R - 2) / d
        return int(self.cx + dx * f), int(self.cy + dy * f)

    def draw_all(self, surf, lat_deg, day, lst_deg):
        self._lazy()
        lat_r = math.radians(lat_deg)

        # background disc
        pygame.draw.circle(surf, (225, 205, 158), (self.cx, self.cy), self.R)
        pygame.draw.circle(surf, DARK_BROWN,      (self.cx, self.cy), self.R, 3)

        # faint cross-hair reference lines
        pygame.draw.line(surf, (185, 158, 112),
                         (self.cx - self.R, self.cy), (self.cx + self.R, self.cy), 1)
        pygame.draw.line(surf, (185, 158, 112),
                         (self.cx, self.cy - self.R), (self.cx, self.cy + self.R), 1)

        # hour lines: H from noon (positive = afternoon = east/right)
        for H in range(-6, 7):
            if H == 0:
                # noon line: straight down from centre
                sx1, sy1 = self._clip(*self._pt(0, -1.4))
                pygame.draw.line(surf, (200, 140, 50), (self.cx, self.cy), (sx1, sy1), 2)
                if self._in_disk(sx1, sy1, 16):
                    txt = self._font_sm.render("12", True, (120, 80, 25))
                    surf.blit(txt, (sx1 - txt.get_width()//2, sy1 - txt.get_height()//2))
                continue
            tan_theta = math.sin(lat_r) * math.tan(math.radians(H * 15.0))
            theta = math.atan(tan_theta)
            # direction from centre: angle theta from "straight down" toward east
            de =  math.sin(theta)    # East component
            du = -math.cos(theta)    # Up component (negative = downward)
            sx1, sy1 = self._clip(*self._pt(de * 1.4, du * 1.4))
            major = (abs(H) == 6)
            pygame.draw.line(surf,
                             (200, 140, 50) if major else (165, 115, 38),
                             (self.cx, self.cy), (sx1, sy1),
                             2 if major else 1)
            if self._in_disk(sx1, sy1, 16):
                txt = self._font_sm.render(str(12 + H), True, (120, 80, 25))
                surf.blit(txt, (sx1 - txt.get_width()//2, sy1 - txt.get_height()//2))

        # daily shadow trace (5-minute steps)
        trace, seg = [], []
        for step in range(289):
            sol_t = step / 288.0 * 24.0
            eu = self._shadow_eu(sol_t, day, lat_deg)
            if eu:
                sx, sy = self._pt(*eu)
                if self._in_disk(sx, sy):
                    trace.append((sx, sy))
                else:
                    trace.append(self._clip(sx, sy))
                    trace.append(None)
            elif trace and trace[-1] is not None:
                trace.append(None)

        for pt in trace + [None]:
            if pt is None:
                if len(seg) >= 2:
                    pygame.draw.lines(surf, (165, 115, 38), False, seg, 2)
                seg = []
            else:
                seg.append(pt)

        # polar gnomon attachment point on wall face  (E=0, U=g·sin(lat))
        g_len   = 0.3
        s_lat   = math.sin(lat_r)
        g_h_px  = int(g_len * s_lat * self.scale * self.zoom)
        gnomon_attach = (self.cx, self.cy - g_h_px)   # on the wall, above centre
        gnomon_cast   = (self.cx, self.cy)             # projection of casting end = centre

        # current shadow + semi-transparent triangle
        ra_s, _ = ecl_to_equ(sun_lon(day))
        sol_cur = (12.0 + (lst_deg - ra_s) / 15.0) % 24.0
        eu_cur  = self._shadow_eu(sol_cur, day, lat_deg)
        if eu_cur:
            sx_tip, sy_tip = self._clip(*self._pt(*eu_cur))
            ss = (sx_tip, sy_tip)
            # triangle: attachment (top) → shadow-origin/centre (bottom-mid) → shadow-tip
            tri = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(tri, (255, 215, 90,  55),
                                [gnomon_attach, gnomon_cast, ss])
            pygame.draw.polygon(tri, (255, 200, 70, 130),
                                [gnomon_attach, gnomon_cast, ss], 1)
            surf.blit(tri, (0, 0))
            # shadow line (from casting-end projection to shadow tip)
            pygame.draw.line(surf, (60, 40, 10), gnomon_cast, ss, 3)
            pygame.draw.circle(surf, (45, 28, 5), ss, 5)

        # gnomon line on wall face: from casting-end projection (centre) up to attachment
        pygame.draw.line(surf, (190, 165, 100), gnomon_cast, gnomon_attach, 3)
        pygame.draw.circle(surf, (190, 165, 100), gnomon_attach, 5)
        pygame.draw.circle(surf, DARK_BROWN,      gnomon_attach, 5, 1)

        # gnomon base marker at centre (casting-end projection)
        pygame.draw.circle(surf, (190, 165, 100), (self.cx, self.cy), 6)
        pygame.draw.circle(surf, DARK_BROWN,      (self.cx, self.cy), 6, 2)

        # E / W labels
        for label, (de, du) in [("E", (0.87, 0)), ("W", (-0.87, 0))]:
            lx, ly = self._pt(de, du)
            t = self._font.render(label, True, DARK_BROWN)
            surf.blit(t, (lx - t.get_width()//2, ly - t.get_height()//2))

        # panel title
        title = self._font.render("South wall sundial", True, GRAY)
        surf.blit(title, (self.cx - title.get_width()//2,
                          self.cy - self.R - 22))
