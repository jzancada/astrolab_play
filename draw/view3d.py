"""3-D celestial sphere with tropical band, horizon and horizontal sundial."""
import math
import pygame

from astronomy import ecl_to_equ, equ_to_hor, ra_dec_to_xyz, sun_lon, CAPRICORN_R, OBL
from .palette import BROWN, BLUE_EQ, ECLIPTIC_C, HORIZ_C, YELLOW, GRID_3D


class View3D:
    """
    Orthographic 3-D view (equatorial frame X=RA0, Y=RA90, Z=NCP).
    Rotate with cam_azi / cam_elv (degrees). Mouse-draggable.
    """

    def __init__(self, cx, cy, radius):
        self.cx, self.cy, self.R = cx, cy, radius
        self.cam_azi  = 35.0
        self.cam_elv  = 28.0
        self.zoom     = 1.0
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
        s = self.R * scale * self.zoom
        return (int(self.cx + xs * s),
                int(self.cy - ys * s),
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

    def _draw_wall_sundial(self, surf, lat_deg, day, lst_deg):
        """
        Vertical south-facing wall sundial placed in the scene — the 3-D
        counterpart of the 2-D 'South wall sundial' panel.

        The wall lies in the local E–U plane (N = 0), facing south.  The polar
        gnomon runs from its foot A on the wall to the tip T in front of it,
        parallel to Earth's axis.  The shadow of T on the wall is computed with
        the same formula as draw.sundial.SundialWall, so the shadow shown here
        and in the side panel are the same shadow (this view is its frontal
        projection seen from the south).
        """
        lon     = sun_lon(day)
        ra_sun, dec_sun = ecl_to_equ(lon)
        ha_sun  = (lst_deg - ra_sun) % 360.0
        alt_sun, az_sun = equ_to_hor(ha_sun, dec_sun, lat_deg)

        lst_r = math.radians(lst_deg)
        lat_r = math.radians(lat_deg)

        # local frame in equatorial coords (X=RA0, Y=RA90, Z=NCP)
        E = (-math.sin(lst_r),  math.cos(lst_r), 0.0)
        N = (-math.sin(lat_r)*math.cos(lst_r),
             -math.sin(lat_r)*math.sin(lst_r),
              math.cos(lat_r))
        U = ( math.cos(lat_r)*math.cos(lst_r),
              math.cos(lat_r)*math.sin(lst_r),
              math.sin(lat_r))

        def lc(e, n, u):
            """local (East, North, Up) → equatorial xyz."""
            return tuple(e*E[i] + n*N[i] + u*U[i] for i in range(3))

        g_len = 0.3
        s_lat, c_lat = math.sin(lat_r), math.cos(lat_r)
        A = lc(0.0, 0.0,  g_len * s_lat)   # gnomon foot on the wall  (E=0, U=g·sinφ)
        T = lc(0.0, -g_len * c_lat, 0.0)   # gnomon tip in front      (N=-g·cosφ)

        # wall face quad in the E–U plane (semi-transparent), East = +E, Up = +U
        ws = 0.45
        corners = [lc( ws, 0.0,  ws), lc( ws, 0.0, -ws),
                   lc(-ws, 0.0, -ws), lc(-ws, 0.0,  ws)]
        cpts = [self._proj(*c)[:2] for c in corners]
        wall_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(wall_surf, (225, 205, 158, 60), cpts)
        pygame.draw.polygon(wall_surf, (120,  90,  40, 150), cpts, 1)
        surf.blit(wall_surf, (0, 0))

        # E / W labels on the wall edges
        self._lazy()
        for label, pt in [("E", lc( ws * 0.92, 0.0, 0.0)),
                           ("W", lc(-ws * 0.92, 0.0, 0.0))]:
            lx, ly, _ = self._proj(*pt)
            txt = self._font_sm.render(label, True, (140, 120, 60))
            surf.blit(txt, (lx + 3, ly - 7))

        a2 = self._proj(*A)[:2]
        t2 = self._proj(*T)[:2]

        # shadow of the tip on the wall — only when the sun lights the south face
        se = math.cos(math.radians(alt_sun)) * math.sin(math.radians(az_sun))
        sn = math.cos(math.radians(alt_sun)) * math.cos(math.radians(az_sun))
        su = math.sin(math.radians(alt_sun))
        if alt_sun > 0.3 and sn < -1e-6:
            t_sh   = -g_len * c_lat / sn
            shadow = lc(-t_sh * se, 0.0, -t_sh * su)   # on the wall (N=0)
            sh2    = self._proj(*shadow)[:2]

            # sun-triangle A → T → shadow (its frontal projection is the 2-D panel)
            tri = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(tri, (255, 215, 90,  55), [a2, t2, sh2])
            pygame.draw.polygon(tri, (255, 200, 70, 130), [a2, t2, sh2], 1)
            surf.blit(tri, (0, 0))

            pygame.draw.line(surf, (60, 40, 10), a2, sh2, 2)   # shadow on the wall
            pygame.draw.circle(surf, (45, 28, 5), sh2, 4)       # shadow tip

        # polar gnomon rod A → T (drawn on top)
        pygame.draw.line(surf, (190, 165, 100), a2, t2, 3)
        pygame.draw.circle(surf, (190, 165, 100), a2, 4)

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
        self._draw_astrolabe_plate(surf)
        self._draw_equator(surf)
        self._draw_ecliptic(surf)
        self._draw_horizon(surf, lat_deg, lst_deg)
        self._draw_projection_ray(surf, day, lst_deg)
        self._draw_sun_3d(surf, day)
        self._draw_wall_sundial(surf, lat_deg, day, lst_deg)
        self._draw_sun_angles(surf, lat_deg, day, lst_deg)
