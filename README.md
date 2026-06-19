# Astrolab Play

An interactive astrolabe simulator built with Python and pygame. The app explains how a medieval astrolabe works by linking the classic 2D projection to a live 3D celestial sphere and a top-down sundial view.

![Three-panel layout: 2D astrolabe · 3D sphere · sundial top view]

---

## Features

### Panel 1 — 2D Astrolabe (left)
- **Tympan** (fixed plate): altitude circles (almucantars) and azimuth arcs computed for the selected latitude
- **Rete** (rotating star map): ecliptic ring with the Sun's position, 16 bright stars
- **Ecliptic scale**: month boundaries (major ticks) and 5° minor ticks on the ecliptic ring, with month abbreviations (Jan–Dec) — rotates with the rete
- **Rule**: line from centre to the Sun, reads solar time on the hour ring
- **Hour ring** (limb): 24-hour scale around the outer rim, labelled in solar time (6 = sunrise, 12 = noon, 18 = sunset); orientation: North at bottom, South at top, East left, West right

### Panel 2 — 3D Celestial Sphere (centre)
- Wireframe celestial sphere with equatorial grid
- **Celestial equator** (blue), **ecliptic** (red), **horizon circle** (gold)
- **Tropical band**: semi-transparent zone between the Tropic of Cancer (+23.4°) and the Tropic of Capricorn (−23.4°), with 72 RA meridian lines (every 5°, thicker every 30° for the 12 months)
- **Tangent plane**: semi-transparent horizontal plane at the observer's position, updates with latitude and time
- **Sundial**: gnomon pointing to the North Celestial Pole, shadow on the horizontal plane, semi-transparent triangle connecting gnomon base → gnomon tip → shadow tip
- **Stereographic projection ray**: line from the South Celestial Pole through the Sun to the astrolabe plate

### Panel 3 — Sundial Top View (right)
- Orthographic top-down view of the horizontal sundial (North up, East right)
- **Daily shadow trace**: full arc from sunrise to sunset for the current date, sampled every 5 minutes
- Hour marks (6 h – 18 h) labelled on the trace
- **Current shadow** shown as a dark line from the gnomon base to the shadow tip
- The trace shape changes with the date slider (hyperbola in winter, straight line near the equinoxes)

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
| **Date slider** | Move through the year (day 1–365) |
| **Solar time slider** | Set time of day (0 h – 24 h solar time) |
| **Drag on astrolabe** | Rotate the rete (advance / retard LST) |
| `,` / `.` keys | Step LST back / forward 1 hour |
| `←` / `→` keys | Step date back / forward 1 day |
| `↑` / `↓` keys | Increase / decrease latitude by 1° |
| **Drag on 3D panel** | Rotate the 3D camera (azimuth / elevation) |
| **Scroll wheel** | Zoom in / out on the panel under the cursor |
| **Middle-click** | Reset zoom to 1× for that panel |
| `ESC` | Quit |

---

## Coordinate conventions

- **Stereographic projection** from the South Celestial Pole onto the equatorial plane: `r = cos(δ) / (1 + sin(δ))`
- **Hour Angle** (HA): 0 h = meridian (south), increases westward. HA = LST − RA
- **Tympan** almucantars and azimuth arcs are computed via the horizon ↔ equatorial transform for the current latitude
- **Solar time** displayed on the slider and hour ring: `solar_time = 12 + (LST − RA_sun) / 15°`
- **Shadow tip** found by ray–plane intersection: ray from gnomon tip along −sun_direction until it meets the horizontal plane (normal = zenith vector)

---

## File structure

```
astrolab_play/
├── astronomy.py   # coordinate transforms, stereographic projection, star catalogue
├── draw.py        # Astrolabe2D, View3D, SundialTop rendering classes
├── main.py        # pygame event loop, sliders, layout
└── README.md
```

---

## Educational purpose

The three panels together answer the question *"how does a medieval astrolabe encode the 3D sky onto a flat disc?"*:

1. The **3D sphere** shows the actual geometry — the Sun on the ecliptic, the horizon tilted by latitude, the stereographic projection ray.
2. The **2D astrolabe** is the projection of that sphere: rotate the rete until the Sun sits on the horizon line to find sunrise/sunset; read the hour from the rule on the limb.
3. The **sundial** shows what an observer on the ground sees: the gnomon's shadow traces a hyperbola across the dial plate throughout the day, and its direction reads the solar hour.
