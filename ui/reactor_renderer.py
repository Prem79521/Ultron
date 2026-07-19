"""
ULTRON Reactor Renderer — Volumetric holographic reactor visualizer using QPainter.

Architecture: No closures in the hot path. The draw queue stores plain data tuples.
A single dispatcher executes them. Zero heap allocations per segment per frame.

Queue entry format: (z_depth, tag, x1, y1, x2, y2, r, g, b, a, extra)
  tag 'L' -> drawLine(x1,y1, x2,y2) with color (r,g,b,a), pen-width from extra
  tag 'E' -> drawEllipse centered at (x1,y1) with rx=x2, ry=y2, filled with color
  tag 'T' -> drawText at (x1,y1) with string in extra, color (r,g,b,a)
  tag 'S' -> scan ring: drawEllipse at (x1,y1) size (x2,y2)
"""
import math
import random
from typing import List, Dict, Any, Tuple
from PySide6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QRadialGradient, QLinearGradient, QImage
)
from PySide6.QtCore import QPointF, QRect, Qt


# ─── Draw tag constants ───────────────────────────────────────────────────────
_L = 0  # line segment (pen-width 1.0)
_LA = 1  # line segment (pen-width 1.5 — arc)
_LG = 2  # line segment (pen-width 1.2 — geo)
_E = 3  # filled ellipse (dot)
_T = 4  # text label
_S = 5  # scan ring ellipse outline


class BaseReactorRenderer:
    """Interface for rendering the cognitive reactor visualizer."""
    def render(self, painter: QPainter, rect: QRect, state: str,
               t: float, rot_x: float, rot_y: float, zoom: float) -> None:
        raise NotImplementedError


# ─── State Palette Configuration ──────────────────────────────────────────────
def _qc(r, g, b, a=255): return (r, g, b, a)

STATE_PARAMS = {
    "sleeping": {
        "color_br": _qc(255, 120, 20, 60),
        "color_mid": _qc(180, 70, 10, 40),
        "color_dim": _qc(120, 40, 0, 20),
        "color_faint": _qc(60, 15, 0, 10),
        "pulse_speed": 1.5,
        "rot_speed": 0.2,
        "particle_speed": 0.2,
        "glow_intensity": 0.3
    },
    "idle": {
        "color_br": _qc(255, 160, 30, 220),
        "color_mid": _qc(200, 90, 15, 160),
        "color_dim": _qc(130, 45, 5, 100),
        "color_faint": _qc(60, 15, 0, 50),
        "pulse_speed": 3.0,
        "rot_speed": 0.7,
        "particle_speed": 0.6,
        "glow_intensity": 0.7
    },
    "listening": {
        "color_br": _qc(255, 200, 40, 255),
        "color_mid": _qc(255, 130, 15, 200),
        "color_dim": _qc(170, 70, 5, 140),
        "color_faint": _qc(70, 25, 0, 70),
        "pulse_speed": 8.0,
        "rot_speed": 1.2,
        "particle_speed": 1.5,
        "glow_intensity": 1.2
    },
    "thinking": {
        "color_br": _qc(80, 230, 255, 255),
        "color_mid": _qc(15, 150, 220, 200),
        "color_dim": _qc(0, 80, 150, 140),
        "color_faint": _qc(0, 25, 70, 70),
        "pulse_speed": 6.0,
        "rot_speed": 2.2,
        "particle_speed": 2.5,
        "glow_intensity": 1.4
    },
    "planning": {
        "color_br": _qc(210, 120, 255, 255),
        "color_mid": _qc(150, 50, 240, 200),
        "color_dim": _qc(80, 0, 170, 140),
        "color_faint": _qc(30, 0, 80, 70),
        "pulse_speed": 4.5,
        "rot_speed": 1.0,
        "particle_speed": 1.0,
        "glow_intensity": 0.9
    },
    "executing": {
        "color_br": _qc(100, 255, 130, 255),
        "color_mid": _qc(25, 200, 75, 200),
        "color_dim": _qc(0, 120, 40, 140),
        "color_faint": _qc(0, 40, 10, 70),
        "pulse_speed": 10.0,
        "rot_speed": 3.0,
        "particle_speed": 3.5,
        "glow_intensity": 1.8
    },
    "speaking": {
        "color_br": _qc(255, 230, 100, 255),
        "color_mid": _qc(255, 170, 40, 200),
        "color_dim": _qc(180, 100, 10, 140),
        "color_faint": _qc(70, 40, 0, 70),
        "pulse_speed": 12.0,
        "rot_speed": 0.9,
        "particle_speed": 1.2,
        "glow_intensity": 1.1
    },
    "error": {
        "color_br": _qc(255, 90, 70, 255),
        "color_mid": _qc(210, 25, 25, 200),
        "color_dim": _qc(130, 5, 5, 140),
        "color_faint": _qc(50, 0, 0, 70),
        "pulse_speed": 15.0,
        "rot_speed": 4.0,
        "particle_speed": 4.5,
        "glow_intensity": 1.6
    }
}


class QPainterReactorRenderer(BaseReactorRenderer):
    """Holographic 3D-projected volumetric reactor visualizer with depth buffer.

    Zero heap allocations per segment per frame via pre-allocated list primitives.
    """

    def __init__(self):
        # Code snippets to float around the shell
        self._snippets = [
            "sys.init()", "0xFF3A", "malloc()", ">> SCAN", "void*", "ACK",
            "SYNC OK", "ptr_ref", "exec()", "hash256", "::bind", "core.0",
            "01101001", "10110100", ">>> RDY", "HEAP 4K", "TCP/SYN",
            "mutex.lk", "REG EAX", "kernel.d", "fork()", "SIGTERM",
            "AES-256", "RSA 4096", "TLS 1.3", "latency", "200 OK",
            "fn main", "use std", "impl Orb", "async {}", "spawn()",
        ]

        # Icosahedron geometry (computed once at init)
        phi = (1.0 + math.sqrt(5.0)) / 2.0
        raw = [
            (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
            (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
            (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
        ]
        self._ico_v: List[Tuple[float, float, float]] = [
            tuple(c / math.hypot(x, y, z) for c in (x, y, z))
            for x, y, z in raw
        ]
        self._ico_e: List[Tuple[int, int]] = []
        for i in range(12):
            for j in range(i + 1, 12):
                vx = self._ico_v[i][0] - self._ico_v[j][0]
                vy = self._ico_v[i][1] - self._ico_v[j][1]
                vz = self._ico_v[i][2] - self._ico_v[j][2]
                if math.hypot(vx, vy, vz) < 1.1:
                    self._ico_e.append((i, j))

        # Text particles
        random.seed(1337)
        self._text_particles: List[Dict[str, Any]] = [
            {
                "text": random.choice(self._snippets),
                "phi": math.acos(max(-1.0, min(1.0, 2 * random.random() - 1))),
                "theta": random.random() * math.pi * 2,
                "radius_offset": random.uniform(1.02, 1.15),
                "speed": random.uniform(0.12, 0.38) * (1 if random.random() > 0.5 else -1),
            }
            for _ in range(45)
        ]

        # Orbiting debris particles
        self._debris: List[Dict[str, Any]] = [
            {
                "orbit_r": random.uniform(1.15, 1.8),
                "speed": random.uniform(0.3, 1.2) * (1 if random.random() > 0.5 else -1),
                "tilt_x": random.uniform(-math.pi / 4, math.pi / 4),
                "tilt_z": random.uniform(-math.pi / 6, math.pi / 6),
                "phase": random.uniform(0, math.pi * 2),
                "size": random.uniform(2.0, 5.0),
                "bright": random.random() > 0.7,
                "mid": random.random() > 0.5,
                "history": [],
            }
            for _ in range(80)
        ]

        # Dense Swirling Dust Particles (200 particles)
        self._dust: List[Dict[str, Any]] = []
        for _ in range(200):
            rr = math.pow(random.random(), 0.6) * 1.7
            theta = random.random() * math.pi * 2
            phi = math.acos(2 * random.random() - 1)
            self._dust.append({
                "x": rr * math.sin(phi) * math.cos(theta),
                "y": rr * math.cos(phi),
                "z": rr * math.sin(phi) * math.sin(theta),
                "size": random.uniform(1.2, 3.2),
                "speed": random.uniform(0.15, 0.45)
            })

        # Pre-baked static star positions (seeded, never changes)
        random.seed(101)
        self._stars: List[Tuple[float, float]] = [
            (random.random(), random.random()) for _ in range(50)
        ]
        self._star_phases: List[float] = [random.uniform(0, math.pi * 2) for _ in range(50)]

        # Pre-baked dynamic film grain textures for high performance
        self._grain_images: List[QImage] = []
        for _ in range(4):
            img = QImage(128, 128, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            for x in range(128):
                for y in range(128):
                    val = random.randint(0, 14)  # Subtle alpha noise
                    img.setPixelColor(x, y, QColor(255, 255, 255, val))
            self._grain_images.append(img)

        # Smooth color state interpolation memory
        self._curr_br = list(STATE_PARAMS["idle"]["color_br"])
        self._curr_mid = list(STATE_PARAMS["idle"]["color_mid"])
        self._curr_dim = list(STATE_PARAMS["idle"]["color_dim"])
        self._curr_faint = list(STATE_PARAMS["idle"]["color_faint"])
        self._curr_pulse_speed = STATE_PARAMS["idle"]["pulse_speed"]
        self._curr_rot_speed = STATE_PARAMS["idle"]["rot_speed"]
        self._curr_particle_speed = STATE_PARAMS["idle"]["particle_speed"]
        self._curr_glow_intensity = STATE_PARAMS["idle"]["glow_intensity"]

        self._font = QFont("Courier New", 7, QFont.Weight.Bold)
        self._pen = QPen(Qt.PenStyle.SolidLine)
        self._queue = []

    # ──────────────────────────────────────────────────────────────────────────
    #  PUBLIC RENDER ENTRY POINT
    # ──────────────────────────────────────────────────────────────────────────

    def render(self, painter: QPainter, rect: QRect, state: str,
               t: float, rot_x: float, rot_y: float, zoom: float) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = rect.width(), rect.height()
        cx = rect.x() + w * 0.5
        cy = rect.y() + h * 0.5

        # Shutdown collapse animation
        radius_scale = 1.0
        if state.lower() == "shutdown":
            decay = (t * 2.0) % 5.0
            radius_scale = max(0.0, 1.0 - decay * 0.5)

        # Scale size dynamically
        R = min(w, h) * 0.28 * zoom * radius_scale
        if R < 1.0:
            return

        # ── Color & speed interpolation towards target states ─────────────────
        target = STATE_PARAMS.get(state.lower(), STATE_PARAMS["idle"])
        lerp_factor = 0.08
        for idx in range(4):
            self._curr_br[idx] += (target["color_br"][idx] - self._curr_br[idx]) * lerp_factor
            self._curr_mid[idx] += (target["color_mid"][idx] - self._curr_mid[idx]) * lerp_factor
            self._curr_dim[idx] += (target["color_dim"][idx] - self._curr_dim[idx]) * lerp_factor
            self._curr_faint[idx] += (target["color_faint"][idx] - self._curr_faint[idx]) * lerp_factor

        self._curr_pulse_speed += (target["pulse_speed"] - self._curr_pulse_speed) * lerp_factor
        self._curr_rot_speed += (target["rot_speed"] - self._curr_rot_speed) * lerp_factor
        self._curr_particle_speed += (target["particle_speed"] - self._curr_particle_speed) * lerp_factor
        self._curr_glow_intensity += (target["glow_intensity"] - self._curr_glow_intensity) * lerp_factor

        # Build QColor objects
        br = QColor(int(self._curr_br[0]), int(self._curr_br[1]), int(self._curr_br[2]), int(self._curr_br[3]))
        mid = QColor(int(self._curr_mid[0]), int(self._curr_mid[1]), int(self._curr_mid[2]), int(self._curr_mid[3]))
        dim = QColor(int(self._curr_dim[0]), int(self._curr_dim[1]), int(self._curr_dim[2]), int(self._curr_dim[3]))
        faint = QColor(int(self._curr_faint[0]), int(self._curr_faint[1]), int(self._curr_faint[2]), int(self._curr_faint[3]))

        # Pulse calculations
        pulse = 1.0 + 0.06 * math.sin(t * self._curr_pulse_speed)
        R_out = R * pulse
        R_in = R_out * 0.46
        R_core = R_out * 0.18

        # Basic rotations (apply state rotation speeds)
        rot_offset = t * self._curr_rot_speed * 0.2
        phi = rot_x + rot_offset
        theta = rot_y + t * 0.12

        # ── Background Stars ──────────────────────────────────────────────────
        self._draw_stars(painter, rect, t, faint)

        # ── Build Depth-Sorted Queue ──────────────────────────────────────────
        q = self._queue
        q.clear()

        core_phi = -phi * 1.5
        core_theta = -theta * 1.2

        # 1. Core cage & spirals (inner layers)
        self._push_lat_rings(q, cx, cy, R_in, core_phi, core_theta, mid, dim, 6, 18)
        self._push_meridians(q, cx, cy, R_in, core_phi, core_theta, dim, faint, 5, 18)
        self._push_geodesic_spirals(q, cx, cy, R_in, core_phi, core_theta, br, t)
        self._push_icosahedron(q, cx, cy, R_core, phi * 2.0, theta * 1.6, br)

        # 2. Outer shell layers
        self._push_lat_rings(q, cx, cy, R_out, phi, theta, mid, dim, 8, 24)
        self._push_meridians(q, cx, cy, R_out, phi, theta, dim, faint, 7, 24)
        self._push_broken_arcs(q, cx, cy, R_out * 1.08, phi, theta, br, mid, t)

        # 3. Intersecting holographic major tri-shield loops
        self._push_tri_shield_loops(q, cx, cy, R_out * 0.92, phi, theta, br, mid, t)

        # 4. Flows & particle systems
        self._push_energy_streams(q, cx, cy, R_out, R_in, phi, theta, t, br, mid)
        self._push_debris(q, cx, cy, R_out, phi, theta, t, br, mid, dim)
        self._push_dust(q, cx, cy, R_out, phi, theta, t, mid)
        self._push_text_sprites(q, cx, cy, R_out, phi, theta, t, br, mid)
        self._push_scan_rings(q, cx, cy, R_out, theta, t, br)

        # ── Draw all queued entities (Depth-Sorted) ──────────────────────────
        q.sort(key=lambda e: e[0])
        self._execute_queue(painter, q)

        # ── Multi-Layer Glow Bloom ────────────────────────────────────────────
        # Base core glow
        glow1 = QRadialGradient(cx, cy, R_core * 2.8)
        glow1.setColorAt(0.0, self._alpha_override(br, int(150 * self._curr_glow_intensity)))
        glow1.setColorAt(0.4, self._alpha_override(mid, int(70 * self._curr_glow_intensity)))
        glow1.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow1))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - R_core * 2.8), int(cy - R_core * 2.8), int(R_core * 5.6), int(R_core * 5.6))

        # Wide ambient outer bloom
        glow2 = QRadialGradient(cx, cy, R_out * 1.2)
        glow2.setColorAt(0.0, self._alpha_override(mid, int(45 * self._curr_glow_intensity)))
        glow2.setColorAt(0.6, self._alpha_override(dim, int(15 * self._curr_glow_intensity)))
        glow2.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow2))
        painter.drawEllipse(int(cx - R_out * 1.2), int(cy - R_out * 1.2), int(R_out * 2.4), int(R_out * 2.4))

        # ── Overlay Post Processing Effects ───────────────────────────────────
        self._draw_overlays(painter, rect, t)

    # ──────────────────────────────────────────────────────────────────────────
    #  QUEUE EXECUTION & RENDERING DISPATCHER
    # ──────────────────────────────────────────────────────────────────────────

    def _execute_queue(self, painter: QPainter, queue: List) -> None:
        pen = self._pen
        prev_tag = -1
        prev_rgba = (-1, -1, -1, -1)

        for entry in queue:
            tag = entry[1]
            r, g, b, a = entry[6], entry[7], entry[8], entry[9]
            rgba = (r, g, b, a)

            if tag != prev_tag:
                if tag == _L:
                    pen.setWidthF(1.0)
                elif tag == _LA:
                    pen.setWidthF(1.8)  # Thicker lines for shield arcs
                else:  # _LG, _S
                    pen.setWidthF(1.2)
                prev_tag = tag
                prev_rgba = (-1, -1, -1, -1)

            if rgba != prev_rgba:
                pen.setColor(QColor(r, g, b, a))
                prev_rgba = rgba

            x1, y1, x2, y2 = entry[2], entry[3], entry[4], entry[5]

            if tag in (_L, _LA, _LG):
                painter.setPen(pen)
                painter.drawLine(x1, y1, x2, y2)
            elif tag == _E:
                painter.setBrush(QColor(r, g, b, a))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(x1, y1), x2, y2)
                
                # Draw motion blur trail segments stored in extra
                trail = entry[10]
                if trail:
                    for k in range(len(trail) - 1):
                        ta = int(a * (k + 1) / len(trail) * 0.4)
                        painter.setPen(QColor(r, g, b, ta))
                        painter.drawLine(trail[k], trail[k + 1])
            elif tag == _T:
                painter.setFont(self._font)
                painter.setPen(QColor(r, g, b, a))
                painter.drawText(x1, y1, entry[10])
            elif tag == _S:
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(x1, y1, x2, y2)

    # ──────────────────────────────────────────────────────────────────────────
    #  3D GEOMETRY PUSHERS (All coordinates mapped with perspective scaling)
    # ──────────────────────────────────────────────────────────────────────────

    def _push_lat_rings(self, q, cx, cy, r, phi, theta, c_mid, c_dim, count, segs):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        seg_step = math.pi * 2.0 / segs
        d = r * 3.5

        for i in range(count):
            lat = -math.pi * 0.5 + (i + 1) * math.pi / (count + 1)
            lr = r * math.cos(lat)
            y3d = r * math.sin(lat)
            is_major = (i % 2 == 0)
            c = c_mid if is_major else c_dim
            cr, cg, cb = c.red(), c.green(), c.blue()
            opacity_base = 160 if is_major else 70

            for j in range(segs):
                lon1 = j * seg_step
                lon2 = lon1 + seg_step

                # Point 1 coords
                x3d_1 = lr * math.cos(lon1)
                z3d_1 = lr * math.sin(lon1)
                # Rotate around Y (phi)
                rx1 = x3d_1 * cos_p - z3d_1 * sin_p
                rz1 = x3d_1 * sin_p + z3d_1 * cos_p
                # Rotate around X (theta)
                ry1 = y3d * cos_t - rz1 * sin_t
                rz1_final = y3d * sin_t + rz1 * cos_t

                # Point 2 coords
                x3d_2 = lr * math.cos(lon2)
                z3d_2 = lr * math.sin(lon2)
                rx2 = x3d_2 * cos_p - z3d_2 * sin_p
                rz2 = x3d_2 * sin_p + z3d_2 * cos_p
                ry2 = y3d * cos_t - rz2 * sin_t
                rz2_final = y3d * sin_t + rz2 * cos_t

                depth = (rz1_final + rz2_final) * 0.5
                scale1 = d / (d - rz1_final) if (d - rz1_final) > 0.01 else 1.0
                scale2 = d / (d - rz2_final) if (d - rz2_final) > 0.01 else 1.0

                alpha = min(255, max(0, int(opacity_base * (1.0 + depth / (r * 2.0)))))
                q.append((depth, _L,
                           int(cx + rx1 * scale1), int(cy + ry1 * scale1),
                           int(cx + rx2 * scale2), int(cy + ry2 * scale2),
                           cr, cg, cb, alpha, None))

    def _push_meridians(self, q, cx, cy, r, phi, theta, c_mid, c_dim, count, segs):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        lat_step = math.pi / segs
        d = r * 3.5
        cr, cg, cb = c_dim.red(), c_dim.green(), c_dim.blue()

        for i in range(count):
            lon = i * math.pi / count
            for j in range(segs):
                lat1 = -math.pi * 0.5 + j * lat_step
                lat2 = lat1 + lat_step

                x3d_1 = r * math.cos(lat1) * math.cos(lon)
                y3d_1 = r * math.sin(lat1)
                z3d_1 = r * math.cos(lat1) * math.sin(lon)

                x3d_2 = r * math.cos(lat2) * math.cos(lon)
                y3d_2 = r * math.sin(lat2)
                z3d_2 = r * math.cos(lat2) * math.sin(lon)

                # Rotate & project P1
                rx1 = x3d_1 * cos_p - z3d_1 * sin_p
                rz1 = x3d_1 * sin_p + z3d_1 * cos_p
                ry1 = y3d_1 * cos_t - rz1 * sin_t
                rz1_final = y3d_1 * sin_t + rz1 * cos_t

                # Rotate & project P2
                rx2 = x3d_2 * cos_p - z3d_2 * sin_p
                rz2 = x3d_2 * sin_p + z3d_2 * cos_p
                ry2 = y3d_2 * cos_t - rz2 * sin_t
                rz2_final = y3d_2 * sin_t + rz2 * cos_t

                depth = (rz1_final + rz2_final) * 0.5
                scale1 = d / (d - rz1_final) if (d - rz1_final) > 0.01 else 1.0
                scale2 = d / (d - rz2_final) if (d - rz2_final) > 0.01 else 1.0

                alpha = min(255, max(0, int(70 * (1.0 + depth / (r * 2.0)))))
                q.append((depth, _L,
                           int(cx + rx1 * scale1), int(cy + ry1 * scale1),
                           int(cx + rx2 * scale2), int(cy + ry2 * scale2),
                           cr, cg, cb, alpha, None))

    def _push_broken_arcs(self, q, cx, cy, r, phi, theta, c_br, c_mid, t):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        d = r * 3.5
        segs = 8
        arc_len = math.pi / 3.0
        seg_frac = arc_len / segs

        for i in range(8):
            lat = -math.pi / 3.0 + i * math.pi / 12.0
            lr = r * math.cos(lat)
            y3d = r * math.sin(lat)
            start = t * (0.3 + 0.1 * i) + i * math.pi * 0.25

            for j in range(segs):
                a1 = start + j * seg_frac
                a2 = a1 + seg_frac

                x3d_1 = lr * math.cos(a1)
                z3d_1 = lr * math.sin(a1)
                rx1 = x3d_1 * cos_p - z3d_1 * sin_p
                rz1 = x3d_1 * sin_p + z3d_1 * cos_p
                ry1 = y3d * cos_t - rz1 * sin_t
                rz1_final = y3d * sin_t + rz1 * cos_t

                x3d_2 = lr * math.cos(a2)
                z3d_2 = lr * math.sin(a2)
                rx2 = x3d_2 * cos_p - z3d_2 * sin_p
                rz2 = x3d_2 * sin_p + z3d_2 * cos_p
                ry2 = y3d * cos_t - rz2 * sin_t
                rz2_final = y3d * sin_t + rz2 * cos_t

                depth = (rz1_final + rz2_final) * 0.5
                scale1 = d / (d - rz1_final) if (d - rz1_final) > 0.01 else 1.0
                scale2 = d / (d - rz2_final) if (d - rz2_final) > 0.01 else 1.0

                c = c_br if j % 2 == 0 else c_mid
                alpha = min(255, max(0, int(150 * (1.0 + depth / (r * 2.0)))))
                q.append((depth, _LA,
                           int(cx + rx1 * scale1), int(cy + ry1 * scale1),
                           int(cx + rx2 * scale2), int(cy + ry2 * scale2),
                           c.red(), c.green(), c.blue(), alpha, None))

    def _push_tri_shield_loops(self, q, cx, cy, r, phi, theta, c_br, c_mid, t):
        # Tri-lobe overlapping shield segments counter-rotating to create ULTRON emblem shape
        loop_phi = -phi * 0.7
        loop_theta = theta * 0.9

        cos_lp, sin_lp = math.cos(loop_phi), math.sin(loop_phi)
        cos_lt, sin_lt = math.cos(loop_theta), math.sin(loop_theta)
        d = r * 3.5

        def project_loop_pt(lx, ly, lz):
            # Rotate by loop angles
            x1 = lx * cos_lp - lz * sin_lp
            z1 = lx * sin_lp + lz * cos_lp
            y2 = ly * cos_lt - z1 * sin_lt
            z2_f = ly * sin_lt + z1 * cos_lt
            scale = d / (d - z2_f) if (d - z2_f) > 0.01 else 1.0
            return cx + x1 * scale, cy + y2 * scale, z2_f

        segs = 64
        step = math.pi * 2.0 / segs
        cr, cg, cb = c_br.red(), c_br.green(), c_br.blue()

        for k in range(3):
            angle_offset = k * math.pi * 2.0 / 3.0
            cos_k, sin_k = math.cos(angle_offset), math.sin(angle_offset)

            for j in range(segs):
                a1 = j * step
                a2 = a1 + step

                tilt = math.radians(28)
                cos_tlt, sin_tlt = math.cos(tilt), math.sin(tilt)

                # Loop local coords
                lx1 = r * math.cos(a1)
                ly1 = r * math.sin(a1) * cos_tlt
                lz1 = r * math.sin(a1) * sin_tlt

                # Rotate around Y-axis by offset
                rx1 = lx1 * cos_k - lz1 * sin_k
                rz1 = lx1 * sin_k + lz1 * cos_k
                ry1 = ly1

                # Point 2 local
                lx2 = r * math.cos(a2)
                ly2 = r * math.sin(a2) * cos_tlt
                lz2 = r * math.sin(a2) * sin_tlt

                rx2 = lx2 * cos_k - lz2 * sin_k
                rz2 = lx2 * sin_k + lz2 * cos_k
                ry2 = ly2

                px1, py1, pz1 = project_loop_pt(rx1, ry1, lz1)
                px2, py2, pz2 = project_loop_pt(rx2, ry2, lz2)

                depth = (pz1 + pz2) * 0.5
                alpha = min(255, max(0, int(220 * (1.0 + depth / (r * 2.0)))))

                # Draw overlapping outer segments to look thick and organic (motion blur look)
                q.append((depth, _LA, px1, py1, px2, py2, cr, cg, cb, alpha, None))
                q.append((depth - 1, _LA, px1 + 1.2, py1 + 1.2, px2 + 1.2, py2 + 1.2, cr, cg, cb, alpha // 2, None))

    def _push_energy_streams(self, q, cx, cy, r_out, r_in, phi, theta, t, c_br, c_mid):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        d = r_out * 3.5

        # 4 flowing energy streams
        for k in range(4):
            phase = k * math.pi * 0.5
            pts = []
            flow_offset = t * 1.6

            segs = 16
            for j in range(segs):
                t_val = j / (segs - 1)
                r = r_in + t_val * (r_out - r_in)
                a = t_val * math.pi * 2.0 + phase + flow_offset
                x = r * math.cos(a)
                y = (t_val - 0.5) * r_out * 0.25
                z = r * math.sin(a)

                rx = x * cos_p - z * sin_p
                rz = x * sin_p + z * cos_p
                ry = y * cos_t - rz * sin_t
                rz_final = y * sin_t + rz * cos_t

                scale = d / (d - rz_final) if (d - rz_final) > 0.01 else 1.0
                pts.append((cx + rx * scale, cy + ry * scale, rz_final))

            for j in range(len(pts) - 1):
                p1, p2 = pts[j], pts[j + 1]
                depth = (p1[2] + p2[2]) * 0.5

                # Bright energy pulse traveling along the spline
                pulse_pos = (t * 22.0) % len(pts)
                is_pulse_head = abs(j - pulse_pos) < 2
                c = c_br if is_pulse_head else c_mid

                alpha = min(255, max(0, int((220 if is_pulse_head else 70) * (1.0 + depth / (r_out * 2.0)))))
                q.append((depth, _LA, p1[0], p1[1], p2[0], p2[1], c.red(), c.green(), c.blue(), alpha, None))

    def _push_geodesic_spirals(self, q, cx, cy, r, phi, theta, c_br, t):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        d = r * 3.5
        segs = 30
        cr, cg, cb = c_br.red(), c_br.green(), c_br.blue()

        for s in range(4):
            phase = s * math.pi * 0.5
            for j in range(segs):
                t1, t2 = j / segs, (j + 1) / segs
                lat1 = t1 * math.pi - math.pi * 0.5
                lon1 = t1 * 5.0 * math.pi + phase + t * 0.8
                lat2 = t2 * math.pi - math.pi * 0.5
                lon2 = t2 * 5.0 * math.pi + phase + t * 0.8

                x1 = r * math.cos(lat1) * math.cos(lon1)
                y1 = r * math.sin(lat1)
                z1 = r * math.cos(lat1) * math.sin(lon1)

                x2 = r * math.cos(lat2) * math.cos(lon2)
                y2 = r * math.sin(lat2)
                z2 = r * math.cos(lat2) * math.sin(lon2)

                rx1 = x1 * cos_p - z1 * sin_p; rz1 = x1 * sin_p + z1 * cos_p
                ry1 = y1 * cos_t - rz1 * sin_t; rz1_final = y1 * sin_t + rz1 * cos_t

                rx2 = x2 * cos_p - z2 * sin_p; rz2 = x2 * sin_p + z2 * cos_p
                ry2 = y2 * cos_t - rz2 * sin_t; rz2_final = y2 * sin_t + rz2 * cos_t

                depth = (rz1_final + rz2_final) * 0.5
                scale1 = d / (d - rz1_final) if (d - rz1_final) > 0.01 else 1.0
                scale2 = d / (d - rz2_final) if (d - rz2_final) > 0.01 else 1.0

                alpha = min(255, max(0, int(150 * (1.0 + depth / (r * 2.0)))))
                q.append((depth, _LG,
                           int(cx + rx1 * scale1), int(cy + ry1 * scale1),
                           int(cx + rx2 * scale2), int(cy + ry2 * scale2),
                           cr, cg, cb, alpha, None))

    def _push_icosahedron(self, q, cx, cy, r, phi, theta, c_br):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        d = r * 3.5
        cr, cg, cb = c_br.red(), c_br.green(), c_br.blue()

        proj = []
        for vx, vy, vz in self._ico_v:
            x1 = vx * r
            y1 = vy * r
            z1 = vz * r
            rx = x1 * cos_p - z1 * sin_p
            rz = x1 * sin_p + z1 * cos_p
            ry = y1 * cos_t - rz * sin_t
            rz_final = y1 * sin_t + rz * cos_t

            scale = d / (d - rz_final) if (d - rz_final) > 0.01 else 1.0
            proj.append((rx * scale, ry * scale, rz_final))

        for i, j in self._ico_e:
            v1, v2 = proj[i], proj[j]
            depth = (v1[2] + v2[2]) * 0.5
            alpha = min(255, max(0, int(220 * (1.0 + depth / (r * 2.0)))))
            q.append((depth, _LG,
                       int(cx + v1[0]), int(cy + v1[1]),
                       int(cx + v2[0]), int(cy + v2[1]),
                       cr, cg, cb, alpha, None))

    def _push_debris(self, q, cx, cy, base_r, phi, theta, t, c_br, c_mid, c_dim):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        d = base_r * 3.5

        # Speed multiplied by state parameter speed
        p_speed_mult = self._curr_particle_speed

        for p in self._debris:
            angle = t * p["speed"] * p_speed_mult + p["phase"]
            orbit_r = base_r * p["orbit_r"]
            ox = orbit_r * math.cos(angle)
            oy = orbit_r * math.sin(angle) * 0.08 * math.sin(angle * 3)
            oz = orbit_r * math.sin(angle)

            y1 = oy * math.cos(p["tilt_x"]) - oz * math.sin(p["tilt_x"])
            z1 = oy * math.sin(p["tilt_x"]) + oz * math.cos(p["tilt_x"])
            x2 = ox * math.cos(p["tilt_z"]) - y1 * math.sin(p["tilt_z"])
            y2 = ox * math.sin(p["tilt_z"]) + y1 * math.cos(p["tilt_z"])
            z2 = z1

            vcx = x2 * cos_p - z2 * sin_p
            vcz = x2 * sin_p + z2 * cos_p
            vcy = y2 * cos_t - vcz * sin_t
            vcz_final = y2 * sin_t + vcz * cos_t

            scale = d / (d - vcz_final) if (d - vcz_final) > 0.01 else 1.0
            px = cx + vcx * scale
            py = cy + vcy * scale

            history = p["history"]
            history.append(QPointF(px, py))
            if len(history) > 6:
                history.pop(0)

            depth_scale = max(0.1, 1.0 + vcz_final / (base_r * 2.0))
            sz = max(0.5, p["size"] * depth_scale * 0.5)
            alpha = min(255, int(220 * depth_scale))
            c = c_br if p["bright"] else (c_mid if p["mid"] else c_dim)

            q.append((vcz_final, _E,
                       px, py, sz, sz,
                       c.red(), c.green(), c.blue(), alpha,
                       list(history[:-1]) if len(history) > 1 else None))

    def _push_dust(self, q, cx, cy, base_r, phi, theta, t, c_mid):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        d = base_r * 3.5
        cr, cg, cb = c_mid.red(), c_mid.green(), c_mid.blue()

        p_speed_mult = self._curr_particle_speed

        for p in self._dust:
            # Slow orbital swirl over time
            rot_y = t * p["speed"] * p_speed_mult * 0.1
            cos_ry, sin_ry = math.cos(rot_y), math.sin(rot_y)

            lx = p["x"] * cos_ry - p["z"] * sin_ry
            lz = p["x"] * sin_ry + p["z"] * cos_ry
            ly = p["y"]

            x3d = lx * base_r
            y3d = ly * base_r
            z3d = lz * base_r

            rx = x3d * cos_p - z3d * sin_p
            rz = x3d * sin_p + z3d * cos_p
            ry = y3d * cos_t - rz * sin_t
            rz_final = y3d * sin_t + rz * cos_t

            scale = d / (d - rz_final) if (d - rz_final) > 0.01 else 1.0
            px = cx + rx * scale
            py = cy + ry * scale

            depth_scale = max(0.1, 1.0 + rz_final / (base_r * 2.0))
            sz = max(0.4, p["size"] * depth_scale * 0.45)
            alpha = min(255, int(90 * depth_scale))

            q.append((rz_final, _E, px, py, sz, sz, cr, cg, cb, alpha, None))

    def _push_text_sprites(self, q, cx, cy, base_r, phi, theta, t, c_br, c_mid):
        cos_p, sin_p = math.cos(phi), math.sin(phi)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        d = base_r * 3.5

        for p in self._text_particles:
            r = base_r * p["radius_offset"]
            td = p["theta"] + t * p["speed"] * 0.04
            x = r * math.sin(p["phi"]) * math.cos(td)
            y3d = r * math.cos(p["phi"])
            z = r * math.sin(p["phi"]) * math.sin(td)

            rx = x * cos_p - z * sin_p
            rz = x * sin_p + z * cos_p
            ry = y3d * cos_t - rz * sin_t
            rz_final = y3d * sin_t + rz * cos_t

            scale = d / (d - rz_final) if (d - rz_final) > 0.01 else 1.0
            px = cx + rx * scale
            py = cy + ry * scale

            depth_scale = max(0.1, 1.0 + rz_final / (base_r * 2.0))
            alpha = min(255, max(0, int(200 * depth_scale)))
            c = c_mid if rz_final >= 0 else c_br
            txt = p["text"]
            tw = int(len(txt) * 5 * 0.5)

            q.append((rz_final, _T,
                       int(px) - tw, int(py) + 3, 0, 0,
                       c.red(), c.green(), c.blue(), alpha,
                       txt))

    def _push_scan_rings(self, q, cx, cy, r, theta, t, c_br):
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        cr, cg, cb = c_br.red(), c_br.green(), c_br.blue()

        for i in range(2):
            yn = math.sin(t * 0.8 + i * math.pi)
            rf = math.sqrt(max(0.0, 1.0 - yn * yn))
            sw = r * rf
            sh = r * rf * abs(sin_t)
            sy = cy + yn * r * cos_t
            depth = r * rf * sin_t
            alpha = min(255, max(0, int(150 * rf)))

            q.append((depth, _S,
                       int(cx - sw), int(sy - sh),
                       int(sw * 2), int(sh * 2),
                       cr, cg, cb, alpha, None))

    # ──────────────────────────────────────────────────────────────────────────
    #  SCREEN OVERLAYS (Film Grain, Scanlines, Vignette)
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_stars(self, painter: QPainter, rect: QRect, t: float, c_faint: QColor):
        painter.setBrush(Qt.BrushStyle.NoBrush)
        x0, y0, rw, rh = rect.x(), rect.y(), rect.width(), rect.height()
        fr, fg, fb = c_faint.red(), c_faint.green(), c_faint.blue()
        for k, (sx, sy) in enumerate(self._stars):
            brightness = min(255, max(0, int(50 + 50 * math.sin(t * 3.5 + self._star_phases[k]))))
            painter.setPen(QColor(fr, fg, fb, brightness))
            painter.drawPoint(int(x0 + sx * rw), int(y0 + sy * rh))

    def _draw_overlays(self, painter: QPainter, rect: QRect, t: float):
        w, h = rect.width(), rect.height()
        mx = rect.x() + w * 0.5
        my = rect.y() + h * 0.5

        # 1. Cinematic vignette overlay
        vignette = QRadialGradient(mx, my, max(w, h) * 0.75)
        vignette.setColorAt(0.0, QColor(0, 0, 0, 0))
        vignette.setColorAt(0.5, QColor(0, 0, 0, 30))
        vignette.setColorAt(0.8, QColor(0, 0, 0, 140))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 220))
        painter.setBrush(QBrush(vignette))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)

        # 2. Scrolling holographic scanlines
        sl_color = QColor(255, 255, 255, 7)  # faint white/silver scanlines
        painter.setPen(sl_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        offset = int(t * 18.0) % 10
        for y in range(rect.y() + offset, rect.y() + h, 6):
            painter.drawLine(rect.x(), y, rect.x() + w, y)

        # 3. Dynamic Tiled Film Grain (24 FPS)
        if self._grain_images:
            grain_idx = int(t * 24.0) % len(self._grain_images)
            grain_img = self._grain_images[grain_idx]
            painter.setBrush(QBrush(grain_img))
            painter.drawRect(rect)

    # ──────────────────────────────────────────────────────────────────────────
    #  UTIL HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _alpha_override(self, color: QColor, alpha: int) -> QColor:
        c = QColor(color)
        c.setAlpha(min(255, max(0, alpha)))
        return c
