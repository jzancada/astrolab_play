"""
Drawing: 2D astrolabe face and 3D celestial sphere with sundial.
"""
import math
import pygame

from astronomy import (
    stereo, to_screen, ecl_to_equ, hor_to_equ, equ_to_hor, ra_dec_to_xyz,
    sun_lon, CAPRICORN_R, OBL, STARS,
)

# ── palette ────────────────────────────────────────────────────────────────────
PARCHMENT  = (230, 210, 168)
BROWN      = (130,  80,  35)
DARK_BROWN = ( 80,  48,  18)
DIM_GOLD   = (130, 100,  35)
HORIZ_C    = (210, 180,  60)   # horizon / almucantars
BLUE_EQ    = ( 80, 120, 210)   # celestial equator
ECLIPTIC_C = (210,  60,  50)   # ecliptic
STAR_C     = (210, 210, 230)
YELLOW     = (255, 215,  35)
WHITE      = (255, 255, 255)
GRAY       = (160, 160, 160)
GRID_3D    = ( 45,  45,  70)


# ══════════════════════════════════════════════════════════════════════════════
# 2-D astrolabe
# ══════════════════════════════════════════════════════════════════════════════

class Astrolabe2D:
    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.R = cx, cy, radius
        self.scale = radius / CAPRICORN_R
        self._font_sm = None
        self._font_hr = None   # hour-ring labels

    def _lazy(self):
        if self._font_sm is None:
            self._font_sm = pygame.font.SysFont("Segoe UI", 10)
        if self._font_hr is None:
            self._font_hr = pygame.font.SysFont("Segoe UI", 11)

    def ts(self, px, py):
        # flip y so north horizon appears at bottom, south at top
        return to_screen(px, -py, self.cx, self.cy, self.scale)

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
            r_px = int(abs(math.cos(d) / (1.0 + math.sin(d))) * self.scale)
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

    # ── rete (ecliptic ring + stars, rotates with LST) ───────────────────────

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


# ══════════════════════════════════════════════════════════════════════════════
# 3-D celestial sphere + sundial
# ══════════════════════════════════════════════════════════════════════════════

class View3D:
    """
    Orthographic 3-D view (equatorial frame X=RA0, Y=RA90, Z=NCP).
    Rotate with cam_azi / cam_elv (degrees). Mouse-draggable.
    """

    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.R = cx, cy, radius
        self.cam_azi  = 35.0     # camera azimuth (degrees)
        self.cam_elv  = 28.0     # camera elevation (degrees)
        self._right   = None
        self._up      = None
        self._fwd     = None
        self._font_sm = None

    def _lazy(self):
        if self._font_sm is None:
            self._font_sm = pygame.font.SysFont("Segoe UI", 11)

    # ── camera basis ─────────────────────────────────────────────────────────

    def _update_basis(self):
        a = math.radians(self.cam_azi)
        e = math.radians(self.cam_elv)
        # camera sits at this point on the unit sphere
        ex = math.cos(e) * math.sin(a)
        ey = math.cos(e) * math.cos(a)
        ez = math.sin(e)
        # forward = toward origin
        fx, fy, fz = -ex, -ey, -ez
        # up hint: Z (NCP) unless camera is near the poles
        ux, uy, uz = (0.0, 0.0, 1.0) if abs(ez) < 0.99 else (0.0, 1.0, 0.0)
        # right = forward × up_hint
        rx = fy*uz - fz*uy; ry = fz*ux - fx*uz; rz = fx*uy - fy*ux
        rm = math.sqrt(rx*rx + ry*ry + rz*rz)
        rx, ry, rz = rx/rm, ry/rm, rz/rm
        # true up = right × forward
        ux2 = ry*fz - rz*fy; uy2 = rz*fx - rx*fz; uz2 = rx*fy - ry*fx
        self._right = (rx, ry, rz)
        self._up    = (ux2, uy2, uz2)
        self._fwd   = (fx, fy, fz)

    def _proj(self, X, Y, Z, scale=0.72):
        """3-D point → (sx, sy, depth).  scale: world units per self.R pixels."""
        r, u, f = self._right, self._up, self._fwd
        xs    = X*r[0] + Y*r[1] + Z*r[2]
        ys    = X*u[0] + Y*u[1] + Z*u[2]
        depth = X*f[0] + Y*f[1] + Z*f[2]
        return (int(self.cx + xs * self.R * scale),
                int(self.cy - ys * self.R * scale),
                depth)

    def _polyline(self, surf, pts3, color, w=1, closed=False, scale=0.72):
        pts2 = [self._proj(*p, scale)[:2] for p in pts3]
        if len(pts2) > 1:
            try:
                pygame.draw.lines(surf, color, closed, pts2, w)
            except Exception:
                pass

    # ── geometry helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _lat_circle(dec_deg, n=60):
        d = math.radians(dec_deg); r = math.cos(d); z = math.sin(d)
        return [(r*math.cos(2*math.pi*i/n), r*math.sin(2*math.pi*i/n), z)
                for i in range(n + 1)]

    @staticmethod
    def _great_circle(nx, ny, nz, n=72):
        """Great circle with given pole direction."""
        m = math.sqrt(nx*nx + ny*ny + nz*nz)
        nx, ny, nz = nx/m, ny/m, nz/m
        # orthogonal basis
        if abs(nx) < 0.9:
            vx, vy, vz = 1.0, 0.0, 0.0
        else:
            vx, vy, vz = 0.0, 1.0, 0.0
        u1x = ny*vz - nz*vy; u1y = nz*vx - nx*vz; u1z = nx*vy - ny*vx
        m1  = math.sqrt(u1x*u1x + u1y*u1y + u1z*u1z)
        u1x, u1y, u1z = u1x/m1, u1y/m1, u1z/m1
        u2x = ny*u1z - nz*u1y; u2y = nz*u1x - nx*u1z; u2z = nx*u1y - ny*u1x
        return [(u1x*math.cos(2*math.pi*i/n) + u2x*math.sin(2*math.pi*i/n),
                 u1y*math.cos(2*math.pi*i/n) + u2y*math.sin(2*math.pi*i/n),
                 u1z*math.cos(2*math.pi*i/n) + u2z*math.sin(2*math.pi*i/n))
                for i in range(n + 1)]

    # ── sub-components ────────────────────────────────────────────────────────

    def _draw_sphere_grid(self, surf):
        for dec in range(-60, 90, 30):
            if dec == 0:
                continue
            self._polyline(surf, self._lat_circle(dec), GRID_3D, 1, True)
        for ra in range(0, 360, 30):
            pts = []
            for di in range(-90, 91, 6):
                d = math.radians(di); rr = math.radians(ra)
                pts.append((math.cos(d)*math.cos(rr), math.cos(d)*math.sin(rr), math.sin(d)))
            self._polyline(surf, pts, GRID_3D, 1)

    @staticmethod
    def _meridian_in_band(ra_deg, n=10):
        """Points along RA=ra_deg between Capricorn and Cancer."""
        ra = math.radians(ra_deg)
        d0, d1 = math.radians(-OBL), math.radians(OBL)
        return [(math.cos(d0 + (d1 - d0) * i / n) * math.cos(ra),
                 math.cos(d0 + (d1 - d0) * i / n) * math.sin(ra),
                 math.sin(d0 + (d1 - d0) * i / n))
                for i in range(n + 1)]

    def _draw_tropic_lines(self, surf):
        """Tropic circles + RA meridian lines within the tropical band."""
        # Tropic of Cancer and Tropic of Capricorn (bounding parallels)
        self._polyline(surf, self._lat_circle( OBL, 90), (255, 165, 50), 2, True)
        self._polyline(surf, self._lat_circle(-OBL, 90), (255, 165, 50), 2, True)

        # 72 meridian lines every 5° of RA
        for ra_deg in range(0, 360, 5):
            major = (ra_deg % 30 == 0)   # every 30° → thicker, brighter
            self._polyline(surf,
                           self._meridian_in_band(ra_deg),
                           (255, 168, 52) if major else (185, 115, 30),
                           2 if major else 1)

    def _draw_tropical_band(self, surf):
        """Semi-transparent band on the sphere between the two tropics (±OBL)."""
        n = 72   # longitude slices
        d_hi = math.radians( OBL)   # Tropic of Cancer
        d_lo = math.radians(-OBL)   # Tropic of Capricorn
        r_hi, z_hi = math.cos(d_hi), math.sin(d_hi)
        r_lo, z_lo = math.cos(d_lo), math.sin(d_lo)

        # build quads and their average camera-space depth
        quads = []
        for i in range(n):
            a0 = 2 * math.pi * i       / n
            a1 = 2 * math.pi * (i + 1) / n
            p = [
                (r_hi * math.cos(a0), r_hi * math.sin(a0), z_hi),
                (r_hi * math.cos(a1), r_hi * math.sin(a1), z_hi),
                (r_lo * math.cos(a1), r_lo * math.sin(a1), z_lo),
                (r_lo * math.cos(a0), r_lo * math.sin(a0), z_lo),
            ]
            fx, fy, fz = self._fwd
            cx = sum(q[0] for q in p) / 4
            cy_ = sum(q[1] for q in p) / 4
            cz = sum(q[2] for q in p) / 4
            depth = cx*fx + cy_*fy + cz*fz
            quads.append((depth, [self._proj(*q)[:2] for q in p]))

        # painter's algorithm: draw back-to-front so front quads win
        quads.sort(reverse=True, key=lambda q: q[0])

        band_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for _, pts in quads:
            pygame.draw.polygon(band_surf, (230, 140, 40, 38), pts)
        surf.blit(band_surf, (0, 0))

    def _draw_tangent_plane(self, surf, lat_deg, lst_deg):
        """Semi-transparent horizontal tangent plane at the observer's position."""
        lat_r, lst_r = math.radians(lat_deg), math.radians(lst_deg)
        E = (-math.sin(lst_r),  math.cos(lst_r), 0.0)
        N = (-math.sin(lat_r) * math.cos(lst_r),
             -math.sin(lat_r) * math.sin(lst_r),
              math.cos(lat_r))

        s = 0.58  # half-size in world units
        corners = [
            tuple( s*E[i] + s*N[i] for i in range(3)),   # NE
            tuple( s*E[i] - s*N[i] for i in range(3)),   # SE
            tuple(-s*E[i] - s*N[i] for i in range(3)),   # SW
            tuple(-s*E[i] + s*N[i] for i in range(3)),   # NW
        ]
        pts = [self._proj(*c)[:2] for c in corners]

        plane_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(plane_surf, (210, 185, 80, 35), pts)   # fill
        pygame.draw.polygon(plane_surf, (210, 185, 80, 110), pts, 1)  # border
        surf.blit(plane_surf, (0, 0))

    def _draw_equator(self, surf):
        self._polyline(surf, self._lat_circle(0, 90), BLUE_EQ, 2, True)

    def _draw_ecliptic(self, surf):
        pts = []
        for lon in range(0, 361, 3):
            ra, dec = ecl_to_equ(lon)
            pts.append(ra_dec_to_xyz(ra, dec))
        self._polyline(surf, pts, ECLIPTIC_C, 2, True)

    def _draw_horizon(self, surf, lat_deg, lst_deg):
        zx, zy, zz = ra_dec_to_xyz(lst_deg, lat_deg)   # zenith in equatorial
        pts = self._great_circle(zx, zy, zz)
        self._polyline(surf, pts, HORIZ_C, 2, True)

    def _draw_astrolabe_plate(self, surf):
        """Rim of the astrolabe plate (equatorial plane, radius = CAPRICORN_R)."""
        s = CAPRICORN_R
        pts = [(s*math.cos(2*math.pi*i/72), s*math.sin(2*math.pi*i/72), 0.0)
               for i in range(73)]
        self._polyline(surf, pts, BROWN, 1, True)

    def _draw_sun_3d(self, surf, day):
        lon    = sun_lon(day)
        ra, dec = ecl_to_equ(lon)
        sx, sy, _ = self._proj(*ra_dec_to_xyz(ra, dec))
        pygame.draw.circle(surf, YELLOW, (sx, sy), 10)
        pygame.draw.circle(surf, (255, 160, 20), (sx, sy), 10, 2)
        pygame.draw.circle(surf, (255, 255, 200), (sx, sy), 5)

    def _draw_projection_ray(self, surf, day, lst_deg):
        """Stereographic projection ray: south pole → sun → astrolabe plate."""
        lon    = sun_lon(day)
        ra, dec = ecl_to_equ(lon)
        sun3d  = ra_dec_to_xyz(ra, dec)
        south  = (0.0, 0.0, -1.0)

        # projected point on z=0 plane: t = 1/(1+sz)
        sz = sun3d[2]
        if 1.0 + sz < 1e-6:
            return
        t    = 1.0 / (1.0 + sz)
        proj = (t * sun3d[0], t * sun3d[1], 0.0)

        self._polyline(surf, [south, sun3d],  (150, 150, 80), 1)
        self._polyline(surf, [sun3d,  proj],  (255, 255, 80), 1)
        px, py, _ = self._proj(*proj)
        pygame.draw.circle(surf, (255, 255, 80), (px, py), 5)

    def _draw_sundial(self, surf, lat_deg, day, lst_deg):
        """
        Horizontal sundial in the observer's tangent plane.
        Gnomon points toward the NCP (= Earth's rotation axis).
        Shows shadow on the horizontal plane.
        """
        lon     = sun_lon(day)
        ra_sun, dec_sun = ecl_to_equ(lon)
        ha_sun  = (lst_deg - ra_sun) % 360.0
        alt_sun, az_sun = equ_to_hor(ha_sun, dec_sun, lat_deg)

        if alt_sun <= 1.0:
            return  # sun below horizon

        lst_r   = math.radians(lst_deg)
        lat_r   = math.radians(lat_deg)

        # local frame in equatorial coords (X=RA0, Y=RA90, Z=NCP)
        E = (-math.sin(lst_r),  math.cos(lst_r), 0.0)
        N = (-math.sin(lat_r)*math.cos(lst_r),
             -math.sin(lat_r)*math.sin(lst_r),
              math.cos(lat_r))
        U = ( math.cos(lat_r)*math.cos(lst_r),
              math.cos(lat_r)*math.sin(lst_r),
              math.sin(lat_r))

        # sun direction in equatorial coords
        alt_r = math.radians(alt_sun); az_r = math.radians(az_sun)
        se = math.cos(alt_r)*math.sin(az_r)   # East component
        sn = math.cos(alt_r)*math.cos(az_r)   # North component
        su = math.sin(alt_r)                   # Up component
        sun_dir = tuple(se*E[i] + sn*N[i] + su*U[i] for i in range(3))

        # gnomon: from origin toward NCP (Z axis in equatorial), length 0.3
        g_len = 0.3
        g_tip = (0.0, 0.0, g_len)   # always toward (0,0,1) = NCP

        # shadow tip: ray from g_tip in -sun_dir until it hits horizontal plane
        # plane: dot(P, U) = 0 (through origin, normal = zenith)
        denom = sum(sun_dir[i] * U[i] for i in range(3))  # = sin(alt_sun)
        numer = sum(g_tip[i]   * U[i] for i in range(3))  # = g_len*sin(lat)
        if abs(denom) < 1e-6:
            return
        t_shad = numer / denom
        shad_tip = tuple(g_tip[i] - t_shad * sun_dir[i] for i in range(3))

        # draw horizontal plane cross (N–S and E–W arms)
        ps = 0.45
        for arm in [N, E]:
            pt_a = tuple(-ps * arm[i] for i in range(3))
            pt_b = tuple(+ps * arm[i] for i in range(3))
            self._polyline(surf, [pt_a, pt_b], (90, 70, 30), 1)

        # compass labels
        self._lazy()
        for label, pt in [("N", tuple(ps * N[i] for i in range(3))),
                           ("E", tuple(ps * E[i] for i in range(3)))]:
            lx, ly, _ = self._proj(*pt)
            txt = self._font_sm.render(label, True, (140, 120, 60))
            surf.blit(txt, (lx + 3, ly - 7))

        # projected screen positions of the three triangle vertices
        sb = self._proj(0.0, 0.0, 0.0)   # gnomon base / shadow root
        st = self._proj(*g_tip)            # gnomon tip
        ss = self._proj(*shad_tip)         # shadow tip

        # semi-transparent triangle (gnomon base → gnomon tip → shadow tip)
        tri_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(tri_surf, (255, 215, 90, 55), [sb[:2], st[:2], ss[:2]])
        pygame.draw.polygon(tri_surf, (255, 200, 70, 130), [sb[:2], st[:2], ss[:2]], 1)
        surf.blit(tri_surf, (0, 0))

        # gnomon rod (on top of triangle)
        pygame.draw.line(surf, (190, 165, 100), sb[:2], st[:2], 3)

        # shadow line (on top of triangle)
        pygame.draw.line(surf, (70, 50, 15), sb[:2], ss[:2], 2)
        pygame.draw.circle(surf, (55, 38, 10), ss[:2], 4)

    def _draw_sun_angles(self, surf, lat_deg, day, lst_deg):
        """
        Draw azimuth and elevation of the Sun as arrows in the tangent plane,
        and as text labels.
        """
        self._lazy()
        lon = sun_lon(day)
        ra_sun, dec_sun = ecl_to_equ(lon)
        ha_sun  = (lst_deg - ra_sun) % 360.0
        alt_sun, az_sun = equ_to_hor(ha_sun, dec_sun, lat_deg)

        if alt_sun < -1:
            return

        lst_r = math.radians(lst_deg)
        lat_r = math.radians(lat_deg)
        E = (-math.sin(lst_r),  math.cos(lst_r), 0.0)
        N = (-math.sin(lat_r)*math.cos(lst_r),
             -math.sin(lat_r)*math.sin(lst_r),
              math.cos(lat_r))
        U = ( math.cos(lat_r)*math.cos(lst_r),
              math.cos(lat_r)*math.sin(lst_r),
              math.sin(lat_r))

        # Azimuth arrow in the horizontal plane (N→sun direction projected onto plane)
        az_r = math.radians(az_sun)
        horiz_dir = (math.sin(az_r)*E[i] + math.cos(az_r)*N[i] for i in range(3))
        horiz_dir = tuple(horiz_dir)
        az_tip = tuple(0.55 * horiz_dir[i] for i in range(3))

        origin3 = (0.0, 0.0, 0.0)
        self._polyline(surf, [origin3, az_tip], (255, 200, 50), 2)

        # Elevation angle arc label in 3D (just show text near the sun arrow)
        ax, ay, _ = self._proj(*az_tip)

        # text panel (just use screen-space text near the 3D view centre)
        # — draw in the _draw_info_overlay instead, called from main

    # ── combined ──────────────────────────────────────────────────────────────

    def draw_all(self, surf, lat_deg, day, lst_deg):
        self._update_basis()
        self._draw_tropical_band(surf)
        self._draw_sphere_grid(surf)
        self._draw_tropic_lines(surf)
        self._draw_tangent_plane(surf, lat_deg, lst_deg)
        self._draw_astrolabe_plate(surf)
        self._draw_equator(surf)
        self._draw_ecliptic(surf)
        self._draw_horizon(surf, lat_deg, lst_deg)
        self._draw_projection_ray(surf, day, lst_deg)
        self._draw_sun_3d(surf, day)
        self._draw_sundial(surf, lat_deg, day, lst_deg)
        self._draw_sun_angles(surf, lat_deg, day, lst_deg)


# ══════════════════════════════════════════════════════════════════════════════
# Top-down sundial view (North up, East right)
# ══════════════════════════════════════════════════════════════════════════════

class SundialTop:
    """Orthographic top-down view of the horizontal sundial."""

    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.R = cx, cy, radius
        self.scale = radius / 0.85   # shadow units → pixels; clips long shadows
        self._font    = None
        self._font_sm = None

    def _lazy(self):
        if self._font is None:
            self._font    = pygame.font.SysFont("Segoe UI", 13, bold=True)
            self._font_sm = pygame.font.SysFont("Segoe UI", 10)

    # ── geometry helpers ──────────────────────────────────────────────────────

    def _shadow_ne(self, sol_t, day, lat_deg):
        """(East, North) of shadow tip for solar time sol_t, or None if no sun."""
        lon = sun_lon(day)
        ra_sun, dec_sun = ecl_to_equ(lon)
        lst_t  = (ra_sun + (sol_t - 12.0) * 15.0) % 360.0
        ha_sun = (lst_t - ra_sun) % 360.0
        alt, az = equ_to_hor(ha_sun, dec_sun, lat_deg)
        if alt <= 0.3:
            return None

        lst_r, lat_r = math.radians(lst_t), math.radians(lat_deg)
        E = (-math.sin(lst_r),  math.cos(lst_r), 0.0)
        N = (-math.sin(lat_r) * math.cos(lst_r),
             -math.sin(lat_r) * math.sin(lst_r),
              math.cos(lat_r))
        U = ( math.cos(lat_r) * math.cos(lst_r),
              math.cos(lat_r) * math.sin(lst_r),
              math.sin(lat_r))

        alt_r, az_r = math.radians(alt), math.radians(az)
        se = math.cos(alt_r) * math.sin(az_r)
        sn = math.cos(alt_r) * math.cos(az_r)
        su = math.sin(alt_r)
        sd = tuple(se*E[i] + sn*N[i] + su*U[i] for i in range(3))

        g_len = 0.3
        g_tip = (0.0, 0.0, g_len)
        denom = sum(sd[i] * U[i] for i in range(3))
        if abs(denom) < 1e-6:
            return None
        t_sh  = sum(g_tip[i] * U[i] for i in range(3)) / denom
        shad  = tuple(g_tip[i] - t_sh * sd[i] for i in range(3))
        return (sum(shad[i] * E[i] for i in range(3)),
                sum(shad[i] * N[i] for i in range(3)))

    def _pt(self, e, n):
        """Local (East, North) → screen pixel. North = up."""
        return int(self.cx + e * self.scale), int(self.cy - n * self.scale)

    def _in_disk(self, sx, sy):
        return (sx - self.cx)**2 + (sy - self.cy)**2 <= self.R * self.R

    def _clip(self, sx, sy):
        """Clamp (sx, sy) to the display circle."""
        dx, dy = sx - self.cx, sy - self.cy
        d = math.sqrt(dx*dx + dy*dy)
        if d < 1e-6 or d <= self.R:
            return sx, sy
        f = (self.R - 2) / d
        return int(self.cx + dx * f), int(self.cy + dy * f)

    # ── drawing ───────────────────────────────────────────────────────────────

    def draw_all(self, surf, lat_deg, day, lst_deg):
        self._lazy()

        # background disc
        pygame.draw.circle(surf, (225, 205, 158), (self.cx, self.cy), self.R)
        pygame.draw.circle(surf, DARK_BROWN,      (self.cx, self.cy), self.R, 3)

        # faint reference rings at 1/3 and 2/3 of radius
        for frac in (0.33, 0.66):
            pygame.draw.circle(surf, (185, 158, 112),
                               (self.cx, self.cy), int(frac * self.R), 1)

        # cardinal arms
        for de, dn in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            x0, y0 = self._pt(de * 0.06, dn * 0.06)
            x1, y1 = self._clip(*self._pt(de, dn))
            pygame.draw.line(surf, (150, 120, 60), (x0, y0), (x1, y1), 1)

        # N / S / E / W labels
        for label, (de, dn) in [("N", (0, 0.87)), ("S", (0, -0.87)),
                                  ("E", (0.87,  0)), ("W", (-0.87, 0))]:
            lx, ly = self._pt(de, dn)
            t = self._font.render(label, True, DARK_BROWN)
            surf.blit(t, (lx - t.get_width()//2, ly - t.get_height()//2))

        # daily trace (5-minute steps)
        trace, seg = [], []
        for step in range(289):
            sol_t = step / 288.0 * 24.0
            ne = self._shadow_ne(sol_t, day, lat_deg)
            if ne:
                sx, sy = self._pt(*ne)
                if self._in_disk(sx, sy):
                    trace.append((sx, sy))
                else:
                    trace.append(self._clip(sx, sy))
                    trace.append(None)   # break segment at rim
            elif trace and trace[-1] is not None:
                trace.append(None)

        for pt in trace + [None]:
            if pt is None:
                if len(seg) >= 2:
                    pygame.draw.lines(surf, (165, 115, 38), False, seg, 2)
                seg = []
            else:
                seg.append(pt)

        # hour dots + labels on the trace
        for h in range(5, 20):
            ne = self._shadow_ne(float(h), day, lat_deg)
            if ne:
                sx, sy = self._pt(*ne)
                if self._in_disk(sx, sy):
                    pygame.draw.circle(surf, DARK_BROWN, (sx, sy), 3)
                    if h % 2 == 0:
                        t = self._font_sm.render(str(h), True, DARK_BROWN)
                        surf.blit(t, (sx + 4, sy - 6))

        # current shadow (bright line + tip dot)
        ra_s, _ = ecl_to_equ(sun_lon(day))
        sol_cur = (12.0 + (lst_deg - ra_s) / 15.0) % 24.0
        ne_cur  = self._shadow_ne(sol_cur, day, lat_deg)

        if ne_cur:
            sx_tip, sy_tip = self._clip(*self._pt(*ne_cur))
            pygame.draw.line(surf, (60, 40, 10),
                             (self.cx, self.cy), (sx_tip, sy_tip), 3)
            pygame.draw.circle(surf, (45, 28, 5), (sx_tip, sy_tip), 5)

        # gnomon base at centre
        pygame.draw.circle(surf, (190, 165, 100), (self.cx, self.cy), 6)
        pygame.draw.circle(surf, DARK_BROWN,      (self.cx, self.cy), 6, 2)

        # panel title
        title = self._font.render("Sundial — top view", True, GRAY)
        surf.blit(title, (self.cx - title.get_width()//2,
                          self.cy - self.R - 22))
