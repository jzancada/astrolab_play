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

# month name → day-of-year of its 1st, for ticks around the orbit
MONTHS = [("Jan", 1),  ("Feb", 32), ("Mar", 60), ("Apr", 91),
          ("May", 121), ("Jun", 152), ("Jul", 182), ("Aug", 213),
          ("Sep", 244), ("Oct", 274), ("Nov", 305), ("Dec", 335)]


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
                    obs_dir=obs_dir, observer=observer, u=u, N=N, E=E, H=H,
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

        # month marks around the orbit (Earth's heliocentric longitude = sun_lon+180)
        for name, d in MONTHS:
            th    = math.radians(sun_lon(d)) + math.pi
            dirv  = (math.cos(th), math.sin(th), 0.0)
            pygame.draw.line(surf, (120, 100, 80),
                             self._proj(_mul(dirv, self.R_ORBIT*0.96)),
                             self._proj(_mul(dirv, self.R_ORBIT*1.05)), 1)
            lab = self._proj(_mul(dirv, self.R_ORBIT*1.14))
            txt = self._font_sm.render(name, True, (150, 140, 110))
            surf.blit(txt, (lab[0] - txt.get_width()//2, lab[1] - txt.get_height()//2))

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

        # lat/lon grid.  Geographic longitude λ maps to angle m0 = radians(λ) +
        # phase about the spin axis, with phase chosen so the observer sits at its
        # own longitude and the grid spins with the hour angle H.
        phase = sc["H"] - math.radians(lon_deg)
        for lc in (-60, -30, 0, 30, 60):
            col = (70, 95, 130) if lc else (90, 140, 110)
            self._globe_curve(surf, earth,
                              self._parallel(math.radians(lc), X_b, Y_b, P, phase),
                              col, 2 if lc == 0 else 1)
        for lam_g in range(0, 360, 30):
            m0 = math.radians(lam_g) + phase
            greenwich = (lam_g == 0)
            self._globe_curve(surf, earth, self._meridian(m0, X_b, Y_b, P),
                              (90, 200, 230) if greenwich else (60, 80, 110),
                              2 if greenwich else 1)
        # label the Greenwich meridian where it crosses the equator (front side)
        g_dir = _add(_mul(X_b, math.cos(phase)), _mul(Y_b, math.sin(phase)))
        if _dot(g_dir, self._fwd) < 0.0:
            gp = self._proj(_add(earth, _mul(g_dir, self.R_EARTH)))
            surf.blit(self._font_sm.render("0°", True, (130, 220, 240)),
                      (gp[0] + 3, gp[1] - 12))

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

        # ── the church tower carrying the sundial (visible when zoomed) ───────
        self._draw_tower(surf, sc)

        # title
        surf.blit(self._font.render("Heliocentric view", True, GRAY),
                  (self.cx - 60, self.cy - self.R - 4))

    def _draw_tower(self, surf, sc):
        """
        A small square church tower standing at the observer, with the sundial
        on its south face and a Christian cross on top.  Local axes: E (east),
        N (north), u (up).  The tower's south face lies in the observer's E–U
        plane (N=0), so the dial geometry — and its shadow — match the other
        panels exactly.
        """
        observer = sc["observer"]
        u, N, E  = sc["u"], sc["N"], sc["E"]
        phi      = sc["phi"]
        se, sn, su = sc["se"], sc["sn"], sc["su"]
        s_hat    = sc["s_hat"]

        # only when the observer's side of the globe faces us
        if _dot(sc["obs_dir"], self._fwd) >= 0.0:
            return

        g = self.G_LEN * self.R_EARTH
        w_h  = g * 1.5          # tower half-width (square footprint)
        h_t  = g * 4.0          # wall height
        roof = g * 1.8          # roof height
        cx_h = g * 1.4          # cross height
        cx_w = g * 0.5          # cross half-arm

        def L(e, n, up):
            """local (east, north, up) → world."""
            return _add(observer, _add(_add(_mul(E, e), _mul(N, n)), _mul(u, up)))

        # footprint: south face at n=0 (through the observer), north at n=2·w_h
        SWb, SEb = L(-w_h, 0, 0),       L( w_h, 0, 0)
        NEb, NWb = L( w_h, 2*w_h, 0),   L(-w_h, 2*w_h, 0)
        SWt, SEt = L(-w_h, 0, h_t),     L( w_h, 0, h_t)
        NEt, NWt = L( w_h, 2*w_h, h_t), L(-w_h, 2*w_h, h_t)
        apex     = L(0, w_h, h_t + roof)

        # faces: (corners, outward normal) — walls then the four roof slopes
        faces = [
            ([SWb, SEb, SEt, SWt], _mul(N, -1.0)),   # south (dial side)
            ([NEb, NWb, NWt, NEt],  N),              # north
            ([SEb, NEb, NEt, SEt],  E),              # east
            ([NWb, SWb, SWt, NWt], _mul(E, -1.0)),   # west
            ([SWt, SEt, apex],     _add(_mul(N, -1.0), _mul(u, 0.6))),   # roof S
            ([NEt, NWt, apex],     _add(N,             _mul(u, 0.6))),   # roof N
            ([SEt, NEt, apex],     _add(E,             _mul(u, 0.6))),   # roof E
            ([NWt, SWt, apex],     _add(_mul(E, -1.0), _mul(u, 0.6))),   # roof W
        ]
        # painter's sort: far faces first (larger depth along the view direction)
        faces.sort(key=lambda fc: _dot(_sub(_mul(_add(fc[0][0], fc[0][2]), 0.5),
                                            self._focus), self._fwd), reverse=True)
        stone = (200, 190, 165)
        for corners, normal in faces:
            sh  = max(0.0, _dot(_norm(normal), s_hat))   # simple sun shading
            col = tuple(int(c * (0.40 + 0.60*sh)) for c in stone)
            poly = [self._proj(p) for p in corners]
            pygame.draw.polygon(surf, col, poly)
            pygame.draw.polygon(surf, (70, 60, 45), poly, 1)

        # Christian cross above the apex
        base = L(0, w_h, h_t + roof)
        top  = L(0, w_h, h_t + roof + cx_h)
        barL = L(-cx_w, w_h, h_t + roof + cx_h*0.62)
        barR = L( cx_w, w_h, h_t + roof + cx_h*0.62)
        pygame.draw.line(surf, (230, 220, 195), self._proj(base), self._proj(top), 2)
        pygame.draw.line(surf, (230, 220, 195), self._proj(barL), self._proj(barR), 2)

        # ── sundial on the south face, at mid-height ──────────────────────────
        c_phi, s_phi = math.cos(phi), math.sin(phi)
        C = L(0, 0, h_t * 0.55)                       # dial centre on the south wall
        A = _add(C, _mul(u,  g * s_phi))              # gnomon foot   (E=0, U=g·sinφ)
        T = _add(C, _mul(N, -g * c_phi))              # gnomon tip in front (N=-g·cosφ)
        a2, t2 = self._proj(A), self._proj(T)

        # shadow of the tip on the wall (sun lighting the south face: sn < 0)
        if su > 0.005 and sn < -1e-6:
            t_sh   = -g * c_phi / sn
            shadow = _add(C, _add(_mul(E, -t_sh * se), _mul(u, -t_sh * su)))
            sh2    = self._proj(shadow)
            tri = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(tri, (255, 215, 90,  60), [a2, t2, sh2])
            pygame.draw.polygon(tri, (255, 200, 70, 140), [a2, t2, sh2], 1)
            surf.blit(tri, (0, 0))
            pygame.draw.line(surf, (60, 40, 10), a2, sh2, 2)
            pygame.draw.circle(surf, (45, 28, 5), sh2, 3)
            ray = _add(T, _mul(s_hat, g * 2.0))       # incoming ray grazing the tip
            pygame.draw.line(surf, (255, 210, 60), self._proj(ray), t2, 2)

        # polar gnomon rod A → T
        pygame.draw.line(surf, (190, 165, 100), a2, t2, 2)
