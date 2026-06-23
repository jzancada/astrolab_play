"""
Heliocentric orrery — the view 'from outside': the Sun fixed at the centre,
the Earth orbiting along the ecliptic with the date and spinning with the
hours, carrying the south-facing wall sundial at (latitude, longitude).

Schematic (NOT to distance scale) so the Earth is visible; the angles are
correct (axial tilt fixed in space → seasons, rotation → hour angle), and the
Sun's rays at the Earth are treated as parallel, so the gnomon's shadow on the
wall is the same shadow as the other panels.  Zoom the panel to fly in toward
the globe and see the wall and its shadow.
"""
import math
import pygame

from astronomy import sun_lon, ecl_to_equ, equ_to_hor, OBL
from .palette import YELLOW, ECLIPTIC_C, BLUE_EQ, GRAY, DARK_BROWN


def _norm(v):
    m = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])
    return (v[0]/m, v[1]/m, v[2]/m) if m > 1e-12 else v

def _cross(a, b):
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])

def _dot(a, b):
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def _add(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def _sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def _mul(a, s): return (a[0]*s, a[1]*s, a[2]*s)


class Heliocentric:
    """
    Frame: ecliptic plane = XY, Sun at origin, ecliptic north = +Z.
    Earth orbits a circle of radius R_ORBIT; its spin axis is fixed in space,
    tilted by the obliquity toward ecliptic longitude 90°, so the seasons fall
    out of the date.  Mouse-draggable camera; per-panel zoom flies in to the
    globe (the focus point lerps from the Sun to the Earth as you zoom).
    """
    R_ORBIT = 1.0
    R_EARTH = 0.18
    G_LEN   = 0.07     # gnomon length in Earth-radius units (visible when zoomed)

    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.R = cx, cy, radius
        self.cam_azi = 40.0
        self.cam_elv = 35.0
        self.zoom    = 1.0
        self._right = self._up = self._fwd = None
        self._focus = (0.0, 0.0, 0.0)
        self._font = self._font_sm = None

    def _lazy(self):
        if self._font is None:
            self._font    = pygame.font.SysFont("Segoe UI", 12, bold=True)
            self._font_sm = pygame.font.SysFont("Segoe UI", 9)

    # ── camera ────────────────────────────────────────────────────────────────

    def _update_basis(self):
        a = math.radians(self.cam_azi)
        e = math.radians(self.cam_elv)
        ex = math.cos(e) * math.sin(a)
        ey = math.cos(e) * math.cos(a)
        ez = math.sin(e)
        f  = (-ex, -ey, -ez)
        uh = (0.0, 0.0, 1.0) if abs(ez) < 0.99 else (0.0, 1.0, 0.0)
        r  = _norm(_cross(f, uh))
        u  = _cross(r, f)
        self._right, self._up, self._fwd = r, u, f

    def _proj(self, P):
        rel = _sub(P, self._focus)
        s   = self.R * 0.62 * self.zoom
        return (int(self.cx + _dot(rel, self._right) * s),
                int(self.cy - _dot(rel, self._up)    * s))

    # ── geometry of the observer / Sun in the local frame ─────────────────────

    def _scene(self, lat_deg, day, lst_deg, lon_deg):
        """
        Build all the world-space vectors needed to draw the globe and the wall.
        Returns a dict; the sun's local components reproduce equ_to_hor exactly,
        so the wall shadow matches the other panels.
        """
        lam   = math.radians(sun_lon(day))      # Sun geocentric ecliptic longitude
        eps   = math.radians(OBL)
        earth = (self.R_ORBIT * math.cos(lam + math.pi),
                 self.R_ORBIT * math.sin(lam + math.pi), 0.0)
        s_hat = _norm(_sub((0.0, 0.0, 0.0), earth))   # Earth → Sun (parallel rays)

        # Earth's spin axis: fixed in space, tilted toward ecliptic longitude 90°
        P = (0.0, math.sin(eps), math.cos(eps))

        # sub-solar meridian basis (X_b toward the Sun's meridian, Y_b = P × X_b)
        X_b = _norm(_sub(s_hat, _mul(P, _dot(s_hat, P))))
        Y_b = _norm(_cross(P, X_b))

        ra_sun, dec_sun = ecl_to_equ(sun_lon(day))
        ha   = (lst_deg - ra_sun) % 360.0           # observer hour angle (= other panels)
        H    = math.radians(ha)
        phi  = math.radians(lat_deg)

        # observer position on the globe: hour angle H west of the sub-solar meridian
        obs_dir = _add(_add(_mul(X_b, math.cos(phi) * math.cos(H)),
                            _mul(Y_b, math.cos(phi) * math.sin(H))),
                       _mul(P, math.sin(phi)))
        observer = _add(earth, _mul(obs_dir, self.R_EARTH))

        # local East/North/Up at the observer
        u = obs_dir
        N = _norm(_sub(P, _mul(u, _dot(P, u))))
        E = _norm(_cross(N, u))

        # Sun in local coords from equ_to_hor → identical to SundialWall
        alt, az = equ_to_hor(ha, dec_sun, lat_deg)
        ar, zr  = math.radians(alt), math.radians(az)
        se = math.cos(ar) * math.sin(zr)
        sn = math.cos(ar) * math.cos(zr)
        su = math.sin(ar)

        return dict(lam=lam, earth=earth, s_hat=s_hat, P=P, X_b=X_b, Y_b=Y_b,
                    obs_dir=obs_dir, observer=observer, u=u, N=N, E=E,
                    alt=alt, az=az, se=se, sn=sn, su=su, phi=phi)

    def observer_sun_local(self, lat_deg, day, lst_deg, lon_deg=0.0):
        """(se, sn, su) of the Sun in the observer's local frame — for tests."""
        s = self._scene(lat_deg, day, lst_deg, lon_deg)
        return s["se"], s["sn"], s["su"]

    # ── globe helpers ─────────────────────────────────────────────────────────

    def _globe_curve(self, surf, center, dirs, color, w):
        """Draw a curve of unit directions on the globe, culling the far side."""
        seg = []
        for d in dirs:
            if _dot(d, self._fwd) < 0.0:        # near side: normal faces the camera
                seg.append(self._proj(_add(center, _mul(d, self.R_EARTH))))
            elif len(seg) >= 2:
                pygame.draw.lines(surf, color, False, seg, w); seg = []
            else:
                seg = []
        if len(seg) >= 2:
            pygame.draw.lines(surf, color, False, seg, w)

    def _parallel(self, latc, X_b, Y_b, P, phase, n=72):
        c, s = math.cos(latc), math.sin(latc)
        out = []
        for i in range(n + 1):
            m = 2*math.pi*i/n + phase
            out.append(_add(_add(_mul(X_b, c*math.cos(m)), _mul(Y_b, c*math.sin(m))),
                            _mul(P, s)))
        return out

    def _meridian(self, m0, X_b, Y_b, P, n=48):
        out = []
        for i in range(n + 1):
            psi = -math.pi/2 + math.pi*i/n
            c, s = math.cos(psi), math.sin(psi)
            out.append(_add(_add(_mul(X_b, c*math.cos(m0)), _mul(Y_b, c*math.sin(m0))),
                            _mul(P, s)))
        return out

    def _great_circle(self, pole, n=96):
        """Unit directions of the great circle whose pole is `pole`."""
        pole = _norm(pole)
        ref  = (1.0, 0.0, 0.0) if abs(pole[0]) < 0.9 else (0.0, 1.0, 0.0)
        a = _norm(_cross(pole, ref))
        b = _cross(pole, a)
        return [_add(_mul(a, math.cos(2*math.pi*i/n)), _mul(b, math.sin(2*math.pi*i/n)))
                for i in range(n + 1)]

    # ── main draw ─────────────────────────────────────────────────────────────

    def draw_all(self, surf, lat_deg, day, lst_deg, lon_deg=0.0):
        self._lazy()
        self._update_basis()
        sc = self._scene(lat_deg, day, lst_deg, lon_deg)
        earth = sc["earth"]
        # focus lerps from the Sun (origin) to the Earth as the user zooms in
        self._focus = _mul(earth, max(0.0, min(1.0, (self.zoom - 1.0) / 2.0)))

        # Earth's orbit (the ecliptic)
        orbit = [(self.R_ORBIT*math.cos(2*math.pi*i/120),
                  self.R_ORBIT*math.sin(2*math.pi*i/120), 0.0) for i in range(121)]
        pts = [self._proj(p) for p in orbit]
        pygame.draw.lines(surf, (90, 70, 60), False, pts, 1)

        # Sun at the centre
        sun2 = self._proj((0.0, 0.0, 0.0))
        pygame.draw.circle(surf, YELLOW, sun2, 12)
        pygame.draw.circle(surf, (255, 160, 20), sun2, 12, 2)
        surf.blit(self._font_sm.render("Sun", True, (255, 210, 120)),
                  (sun2[0] + 14, sun2[1] - 6))

        # Sun → Earth ray (incoming sunlight direction)
        pygame.draw.line(surf, (120, 110, 60), sun2, self._proj(earth), 1)

        P, X_b, Y_b = sc["P"], sc["X_b"], sc["Y_b"]

        # filled Earth disc (projected sphere outline)
        ec = self._proj(earth)
        er_px = max(2, int(self.R_EARTH * self.R * 0.62 * self.zoom))
        pygame.draw.circle(surf, (28, 46, 78), ec, er_px)

        # night side: shade the hemisphere away from the Sun (pole = -s_hat)
        # (drawn as the terminator great circle; fill kept simple)
        term = self._great_circle(sc["s_hat"])
        self._globe_curve(surf, earth, term, (60, 70, 95), 1)

        # lat/lon grid — meridians carry a phase so the globe visibly spins with
        # the hour angle; longitude offsets them (places the observer's meridian)
        ha_phase = -math.radians((lst_deg) % 360.0)
        lon_off  = math.radians(lon_deg)
        for lc in (-60, -30, 0, 30, 60):
            col = (70, 95, 130) if lc else (90, 140, 110)
            self._globe_curve(surf, earth,
                              self._parallel(math.radians(lc), X_b, Y_b, P, ha_phase),
                              col, 2 if lc == 0 else 1)
        for k in range(12):
            m0 = ha_phase + lon_off + k * math.pi/6
            self._globe_curve(surf, earth, self._meridian(m0, X_b, Y_b, P),
                              (60, 80, 110), 1)

        # spin axis (poles)
        np_dir, sp_dir = P, _mul(P, -1.0)
        if _dot(np_dir, self._fwd) < 0.2:
            pygame.draw.line(surf, (150, 150, 170),
                             self._proj(_add(earth, _mul(np_dir, self.R_EARTH*1.25))),
                             self._proj(_add(earth, _mul(sp_dir, self.R_EARTH*1.25))), 1)

        # sub-solar point (where the Sun is overhead) — small bright dot
        sub = sc["s_hat"]
        if _dot(sub, self._fwd) < 0.0:
            pygame.draw.circle(surf, (255, 220, 120), self._proj(_add(earth, _mul(sub, self.R_EARTH))), 3)

        # Earth label
        surf.blit(self._font_sm.render("Earth", True, (150, 180, 210)),
                  (ec[0] + er_px + 4, ec[1] - 6))

        # ── the wall sundial at the observer (visible when zoomed) ────────────
        self._draw_wall(surf, sc)

        # title
        surf.blit(self._font.render("Heliocentric view", True, GRAY),
                  (self.cx - 60, self.cy - self.R - 4))

    def _draw_wall(self, surf, sc):
        observer = sc["observer"]
        u, N, E  = sc["u"], sc["N"], sc["E"]
        phi      = sc["phi"]
        se, sn, su = sc["se"], sc["sn"], sc["su"]

        # only when this side of the globe faces us
        if _dot(sc["obs_dir"], self._fwd) >= 0.0:
            return

        g = self.G_LEN * self.R_EARTH
        c_phi, s_phi = math.cos(phi), math.sin(phi)
        A = _add(observer, _mul(u, g * s_phi))     # gnomon foot on the wall (E=0,U=g·sinφ)
        T = _add(observer, _mul(N, -g * c_phi))    # gnomon tip in front      (N=-g·cosφ)

        # local horizon disc (small), to seat the wall
        ws = g * 1.6
        quad = [_add(_add(observer, _mul(E,  ws)), _mul(u,  ws)),
                _add(_add(observer, _mul(E,  ws)), _mul(u, -ws)),
                _add(_add(observer, _mul(E, -ws)), _mul(u, -ws)),
                _add(_add(observer, _mul(E, -ws)), _mul(u,  ws))]
        wsurf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(wsurf, (225, 205, 158, 70), [self._proj(q) for q in quad])
        pygame.draw.polygon(wsurf, (120, 90, 40, 160), [self._proj(q) for q in quad], 1)
        surf.blit(wsurf, (0, 0))

        a2 = self._proj(A)
        t2 = self._proj(T)

        # shadow of the tip on the wall (sun lighting the south face: sn < 0)
        if su > 0.005 and sn < -1e-6:
            t_sh   = -g * c_phi / sn
            shadow = _add(_add(observer, _mul(E, -t_sh * se)), _mul(u, -t_sh * su))
            sh2    = self._proj(shadow)
            tri = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(tri, (255, 215, 90,  60),  [a2, t2, sh2])
            pygame.draw.polygon(tri, (255, 200, 70, 140), [a2, t2, sh2], 1)
            surf.blit(tri, (0, 0))
            pygame.draw.line(surf, (60, 40, 10), a2, sh2, 2)
            pygame.draw.circle(surf, (45, 28, 5), sh2, 3)
            # incoming sun ray grazing the tip (parallel → collinear with shadow)
            ray = _add(T, _mul(sc["s_hat"], g * 2.0))
            pygame.draw.line(surf, (255, 210, 60), self._proj(ray), t2, 2)

        # polar gnomon rod A → T
        pygame.draw.line(surf, (190, 165, 100), a2, t2, 2)
        pygame.draw.circle(surf, (210, 80, 60), a2, 3)   # observer marker
