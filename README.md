# Astrolab Play

An interactive astrolabe simulator built with Python and pygame. The app explains how a medieval astrolabe works by linking the classic 2D projection to a live 3D celestial sphere, a south-facing wall sundial, and a heliocentric "view from outside" — all driven by the same Sun and showing the **same gnomon shadow** in every panel.

![Four-panel 2x2 layout: 2D astrolabe · 3D sphere · wall sundial · heliocentric orrery]

---

## Features

The window is a **2×2 grid** of synchronized panels. Moving any slider updates all four at once.

### Panel 1 — 2D Astrolabe (top-left)
- **Tympan** (fixed plate): altitude circles (almucantars) and azimuth arcs computed for the selected latitude
- **Rete** (rotating star map): ecliptic ring with the Sun's position, 16 bright stars
- **Ecliptic scale**: month boundaries (major ticks) and 5° minor ticks on the ecliptic ring, with month abbreviations (Jan–Dec) — rotates with the rete
- **Rule**: line from centre to the Sun, reads solar time on the hour ring
- **Hour ring** (limb): 24-hour scale around the outer rim, labelled in solar time (6 = sunrise, 12 = noon, 18 = sunset); orientation: North at bottom, South at top, East left, West right

### Panel 2 — 3D Celestial Sphere (top-right)
- Wireframe celestial sphere with equatorial grid
- **Celestial equator** (blue), **ecliptic** (red), **horizon circle** (gold)
- **Tropical band**: semi-transparent zone between the Tropic of Cancer (+23.4°) and the Tropic of Capricorn (−23.4°), with 72 RA meridian lines (every 5°, thicker every 30° for the 12 months)
- **Ground grid**: horizontal plane in green with N / S / E / W cardinal labels, orienting the scene for the current latitude and time
- **South wall sundial**: a vertical, south-facing dial standing on the ground grid; polar gnomon (foot on the wall → tip in front), with the shadow on the wall face and the incoming sun ray drawn collinear with it
- **Stereographic projection ray**: line from the South Celestial Pole through the Sun to the astrolabe plate

### Panel 3 — South Wall Sundial (bottom-left)
- Face-on view (from the south) of the vertical wall dial
- **Polar gnomon** with hour lines from the direct-south formula `tan(θ) = sin(lat) · tan(H · 15°)`
- **Daily shadow trace**: full arc the tip's shadow draws across the wall from sunrise to sunset, sampled every 5 minutes
- **Current shadow** with a semi-transparent sun-triangle (gnomon foot → tip → shadow tip)
- The shadow only appears while the Sun lights the south face

### Panel 4 — Heliocentric View / Orrery (bottom-right)
- The "view from outside": the **Sun fixed at the centre**, the **Earth orbiting** along the ecliptic with the date and **spinning with the hours**
- Earth's spin axis is **fixed in space** and tilted by the obliquity — the seasons fall out of the orbital position
- Globe with a latitude/longitude grid, highlighted equator, polar axis, and the **sub-solar point** (where the Sun is overhead)
- Carries the **same wall sundial** at the chosen latitude and longitude; because the Sun's rays are effectively parallel at the Earth, the gnomon's shadow here is the **same shadow** as the other panels
- Schematic (not to distance scale) so the Earth is visible — **zoom the panel** to fly the focus from the Sun in to the globe and see the wall and its shadow

---

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.10 + |
| pygame | 2.x |

Install pygame with:

```bash
pip install pygame
```

> If you use a conda environment (recommended):
> ```bash
> conda install -c conda-forge pygame
> ```

---

## Running

```bash
python main.py
```

---

## Controls

| Input | Action |
|---|---|
| **Latitude slider** | Change observer's latitude (−89° … +89°) |
| **Longitude slider** | Place the wall on the globe in the heliocentric panel (−180° … +180°, default 0°) |
| **Date slider** | Move through the year (day 1–365) |
| **Solar time slider** | Set time of day (0 h – 24 h solar time) |
| **Drag on astrolabe** | Rotate the rete (advance / retard LST) |
| `,` / `.` keys | Step LST back / forward 1 hour |
| `←` / `→` keys | Step date back / forward 1 day |
| `↑` / `↓` keys | Increase / decrease latitude by 1° |
| **Drag on 3D / orrery panel** | Rotate that camera (azimuth / elevation) |
| **Scroll wheel** | Zoom in / out on the panel under the cursor |
| **Middle-click** | Reset zoom to 1× for that panel |
| `ESC` | Quit |

> Longitude only **places** the wall on the globe; the local solar time (and therefore the shadow) stays driven by the time slider, so the shadow remains consistent across all four panels.

---

## Coordinate conventions

- **Stereographic projection** from the South Celestial Pole onto the equatorial plane: `r = cos(δ) / (1 + sin(δ))`
- **Hour Angle** (HA): 0 h = meridian (south), increases westward. HA = LST − RA
- **Tympan** almucantars and azimuth arcs are computed via the horizon ↔ equatorial transform for the current latitude
- **Solar time** displayed on the slider and hour ring: `solar_time = 12 + (LST − RA_sun) / 15°`
- **Wall shadow** — the one shared formula: with the Sun's local direction `(se, sn, su)` from `equ_to_hor`, the tip's shadow on the south wall is `t = −g · cos(lat) / sn`, `shadow = (−t·se, −t·su)` in the wall's (East, Up) plane. `SundialWall`, the 3D wall in `View3D`, and `Heliocentric` all use this identical formula, so the shadow is the same in every panel.

---

## File structure

```
astrolab_play/
├── astronomy.py        # coordinate transforms, stereographic projection, star catalogue
├── draw/               # rendering package (one class per module)
│   ├── __init__.py     #   re-exports the four classes
│   ├── palette.py      #   shared colours
│   ├── astrolabe2d.py  #   Astrolabe2D
│   ├── view3d.py       #   View3D (celestial sphere + wall sundial + ground grid)
│   ├── sundial.py      #   SundialWall
│   └── heliocentric.py #   Heliocentric (orrery)
├── main.py             # pygame event loop, sliders, 2×2 layout
└── README.md
```

---

## Educational purpose

The four panels together answer *"how does a medieval astrolabe encode the 3D sky onto a flat disc — and how does that relate to where the Earth actually is?"*:

1. The **3D sphere** shows the local geometry — the Sun on the ecliptic, the horizon tilted by latitude, the wall and its shadow, the stereographic projection ray.
2. The **2D astrolabe** is the projection of that sphere: rotate the rete until the Sun sits on the horizon line to find sunrise/sunset; read the hour from the rule on the limb.
3. The **wall sundial** is what an observer reads on a south-facing wall: the polar gnomon's shadow sweeps across the dial and its direction gives the solar hour.
4. The **heliocentric orrery** steps all the way out: the same observer, the same shadow, now seen on a tilted, spinning Earth orbiting the Sun — so the seasons, the day, and the sundial reading all come from one picture.
