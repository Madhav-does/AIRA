"""
ARIA — Tony Stark JARVIS Scientific HUD Interface
Fully responsive, fullscreen-adaptive Arc Reactor holographic console.
Features real-time dynamic frequency visualizer, concentric rotating telemetry rings,
live CPU/RAM hardware diagnostics, dual-channel oscilloscope, and a practical settings HUD.
"""

import tkinter as tk
from tkinter import ttk
import math
import random
import time
import threading
import os
import asyncio
from datetime import datetime

# Suppress Pygame welcome banner
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# ── Color Palette (Tony Stark JARVIS / Arc Reactor Holographic Palette) ──────
BG          = "#010308"     # Deep space carbon black
PANEL_BG    = "#020814"     # Holographic panel dark
CYAN_CORE   = "#00F0FF"     # Arc Reactor bright cyan
CYAN_NEON   = "#00C8FF"     # Vibrant electric cyan
CYAN_MID    = "#0088B8"     # Mid-tone holographic cyan
CYAN_DARK   = "#002C40"     # Dim structural lines
CYAN_GRID   = "#001420"     # Ambient background grid
GOLD_ARC    = "#FFB800"     # Stark gold accent
GOLD_DIM    = "#664800"     # Dim gold
TEXT_BRIGHT = "#E6FAFF"     # High-contrast holographic text
TEXT_MID    = "#70B8D8"     # Secondary telemetry text
TEXT_MUTED  = "#204860"     # Ambient background text
ALERT_RED   = "#FF3344"     # Error alert

# State configurations
STATE_CFG = {
    'idle': {
        'bright': '#00C8FF', 'mid': '#0077A0', 'dim': '#002838',
        'label': 'SYSTEM STANDBY', 'amp': 10, 'speed': 1.2,
        'core_color': '#004060', 'glow': '#001828',
        'sub_status': 'AWAITING COMMAND',
    },
    'listening': {
        'bright': '#00FF99', 'mid': '#00BB70', 'dim': '#004428',
        'label': 'VOICE INPUT ACTIVE', 'amp': 48, 'speed': 6.5,
        'core_color': '#00AA60', 'glow': '#003318',
        'sub_status': 'ANALYZING ACOUSTIC STREAM',
    },
    'thinking': {
        'bright': '#FFB800', 'mid': '#CC8800', 'dim': '#553300',
        'label': 'NEURAL SYNTHESIS', 'amp': 32, 'speed': 4.0,
        'core_color': '#CC8800', 'glow': '#332000',
        'sub_status': 'QUERYING GEMINI CORE',
    },
    'speaking': {
        'bright': '#00F0FF', 'mid': '#00A0E0', 'dim': '#003050',
        'label': 'AUDIO OUTPUT ACTIVE', 'amp': 56, 'speed': 8.5,
        'core_color': '#0088CC', 'glow': '#002038',
        'sub_status': 'TRANSMITTING VOCAL MATRIX',
    },
    'error': {
        'bright': '#FF3344', 'mid': '#AA2230', 'dim': '#441018',
        'label': 'SYSTEM EXCEPTION', 'amp': 18, 'speed': 3.0,
        'core_color': '#AA2230', 'glow': '#30080C',
        'sub_status': 'TELEMETRY FAULT',
    },
}

NUM_BARS  = 96     # Number of frequency bars in the Arc Reactor
FPS       = 35     # Animation frame rate


class AppWindow:
    """
    JARVIS Scientific HUD for ARIA.
    100% Responsive and fullscreen-adaptive canvas with dynamic geometry,
    live hardware telemetry, and an intuitive settings console.
    """

    def __init__(
        self,
        config: dict,
        on_listen_request=None,
        on_api_key_save=None,
        on_reset_memory=None,
    ):
        self.config = config
        self.on_listen_request = on_listen_request
        self.on_api_key_save = on_api_key_save
        self.on_reset_memory = on_reset_memory

        # Dynamic canvas geometry
        self._w = 640
        self._h = 560
        self._cx = self._w / 2
        self._cy = self._h / 2
        self._base_r = 110

        # Animation states
        self._status = 'idle'
        self._anim_running = True
        self._rot_outer = 0.0
        self._rot_inner = 0.0
        self._bars = []
        self._phases = [random.uniform(0, 2 * math.pi) for _ in range(NUM_BARS)]
        self._osc_points = 80
        self._fullscreen = False

        # Live telemetry metrics
        self._cpu_val = 0
        self._ram_val = 0
        self._last_telemetry_check = 0

        # Root window setup
        self.root = tk.Tk()
        self.root.title("A.R.I.A. // STARK INDUSTRIES HUD")
        self.root.geometry("640x760")
        self.root.minsize(500, 580)
        self.root.configure(bg=BG)
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Bind fullscreen and resize events
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self._exit_fullscreen())

        self._build_ui()
        self._start_animation()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # 1. Top HUD Status Bar
        self._build_header()

        # 2. Fully Expanding Holographic Canvas
        self._canvas_frame = tk.Frame(self.root, bg=BG)
        self._canvas_frame.pack(fill='both', expand=True)

        self._canvas = tk.Canvas(
            self._canvas_frame,
            bg=BG, bd=0, highlightthickness=0
        )
        self._canvas.pack(fill='both', expand=True)
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        # Create all canvas display objects
        self._init_canvas_objects()

        # 3. Bottom Dialogue HUD Readout
        self._build_dialogue_hud()

        # 4. Bottom Activate Button
        self._build_footer()

    def _build_header(self):
        """Top Stark Industries header with status pills and controls."""
        hdr = tk.Frame(self.root, bg=BG, height=48)
        hdr.pack(fill='x', padx=16, pady=(8, 2))
        hdr.pack_propagate(False)

        # Left branding
        left_box = tk.Frame(hdr, bg=BG)
        left_box.pack(side='left', fill='y')

        tk.Label(
            left_box, text="◈ STARK INDUSTRIES // ARIA OS v4.2",
            bg=BG, fg=CYAN_NEON,
            font=('Consolas', 11, 'bold')
        ).pack(anchor='w')

        user_name = self.config.get('user_name', 'Madhav').upper()
        self._header_user_lbl = tk.Label(
            left_box, text=f"OPERATOR: {user_name}  |  QUANTUM NEURAL CORE: ONLINE",
            bg=BG, fg=TEXT_MUTED,
            font=('Consolas', 8)
        )
        self._header_user_lbl.pack(anchor='w')

        # Right utility buttons
        btn_box = tk.Frame(hdr, bg=BG)
        btn_box.pack(side='right', fill='y')

        for icon, cmd, tip in [
            ("⛶", self._toggle_fullscreen, "Toggle Fullscreen (F11)"),
            ("⟳", self._reset_memory, "Reset Memory"),
            ("📌", self._toggle_topmost, "Toggle Always On Top"),
            ("⚙", self._open_settings, "Settings Console"),
        ]:
            b = tk.Button(
                btn_box, text=icon, command=cmd,
                bg='#030B18', fg=CYAN_MID,
                activebackground='#081830', activeforeground=CYAN_CORE,
                relief='flat', bd=0, font=('Consolas', 11),
                width=3, cursor='hand2'
            )
            b.pack(side='right', padx=3, pady=4)

        # Tech divider line
        tk.Frame(self.root, bg=CYAN_DARK, height=1).pack(fill='x', padx=12, pady=(2, 0))

    def _init_canvas_objects(self):
        """Pre-allocate all canvas elements for high-performance coordinate updates."""
        # 1. Background grid elements
        self._bg_lines = []
        for _ in range(8):
            self._bg_lines.append(self._canvas.create_line(0, 0, 0, 0, fill=CYAN_GRID, width=1))

        # 2. Corner HUD brackets (8 line IDs)
        self._corner_lines = [self._canvas.create_line(0, 0, 0, 0, fill=CYAN_DARK, width=1) for _ in range(8)]

        # 3. Concentric Telemetry Circles
        self._ring_outer_border = self._canvas.create_oval(0, 0, 0, 0, outline='#001420', width=1)
        self._ring_degree_track = self._canvas.create_oval(0, 0, 0, 0, outline='#002234', width=1)
        self._ring_inner_track  = self._canvas.create_oval(0, 0, 0, 0, outline='#001828', width=1)

        # Degree Labels
        self._deg_000 = self._canvas.create_text(0, 0, text="000°", fill=TEXT_MUTED, font=('Consolas', 7))
        self._deg_090 = self._canvas.create_text(0, 0, text="090°", fill=TEXT_MUTED, font=('Consolas', 7))
        self._deg_180 = self._canvas.create_text(0, 0, text="180°", fill=TEXT_MUTED, font=('Consolas', 7))
        self._deg_270 = self._canvas.create_text(0, 0, text="270°", fill=TEXT_MUTED, font=('Consolas', 7))

        # 4. Dynamic Rotating Outer Arcs
        self._outer_arcs = [self._canvas.create_line(0, 0, 0, 0, fill=CYAN_DARK, width=2, capstyle='round') for _ in range(4)]

        # 5. Dynamic Counter-Rotating Ticks
        self._inner_ticks = [self._canvas.create_line(0, 0, 0, 0, fill='#003850', width=1) for _ in range(16)]

        # 6. Equalizer Frequency Bars
        self._bars = [self._canvas.create_line(0, 0, 0, 0, fill=CYAN_DARK, width=2, capstyle='round') for _ in range(NUM_BARS)]

        # 7. Arc Reactor Core Housings & Masks
        self._core_mask_outer = self._canvas.create_oval(0, 0, 0, 0, fill=BG, outline='#002840', width=2)
        self._core_ring_gold  = self._canvas.create_oval(0, 0, 0, 0, outline=GOLD_DIM, width=1)
        self._core_ring_cyan  = self._canvas.create_oval(0, 0, 0, 0, outline='#004060', width=1)

        # Core Glow Layers
        self._core_glow_3 = self._canvas.create_oval(0, 0, 0, 0, fill='#001018', outline='#002030', width=1)
        self._core_glow_2 = self._canvas.create_oval(0, 0, 0, 0, fill='#001824', outline='#003048', width=1)
        self._core_glow_1 = self._canvas.create_oval(0, 0, 0, 0, fill='#002838', outline='#004868', width=1)

        # Central Titles
        self._center_title = self._canvas.create_text(0, 0, text="A.R.I.A.", fill=CYAN_CORE, font=('Consolas', 18, 'bold'))
        self._center_status = self._canvas.create_text(0, 0, text="STANDBY", fill=CYAN_MID, font=('Consolas', 8, 'bold'))

        # 8. Left Live Telemetry & Hardware Gauges
        self._tel_left_box = [
            self._canvas.create_text(0, 0, text="[ SYSTEM TELEMETRY ]", fill=CYAN_MID, font=('Consolas', 8, 'bold'), anchor='w'),
            self._canvas.create_text(0, 0, text="CPU: 0%", fill=TEXT_MID, font=('Consolas', 8), anchor='w'),
            self._canvas.create_text(0, 0, text="RAM: 0%", fill=TEXT_MID, font=('Consolas', 8), anchor='w'),
            self._canvas.create_text(0, 0, text="AUDIO: 48kHz 24-BIT", fill=TEXT_MUTED, font=('Consolas', 7), anchor='w'),
            self._canvas.create_text(0, 0, text="LINK: NOMINAL", fill=TEXT_MUTED, font=('Consolas', 7), anchor='w'),
        ]
        # CPU/RAM gauge bar backgrounds & fills
        self._gauge_cpu_bg   = self._canvas.create_line(0, 0, 0, 0, fill='#001828', width=4)
        self._gauge_cpu_fill = self._canvas.create_line(0, 0, 0, 0, fill=CYAN_NEON, width=4)
        self._gauge_ram_bg   = self._canvas.create_line(0, 0, 0, 0, fill='#001828', width=4)
        self._gauge_ram_fill = self._canvas.create_line(0, 0, 0, 0, fill=CYAN_MID, width=4)

        # 9. Right Diagnostics Box
        self._tel_right_box = [
            self._canvas.create_text(0, 0, text="[ NEURAL DIAGNOSTICS ]", fill=CYAN_MID, font=('Consolas', 8, 'bold'), anchor='e'),
            self._canvas.create_text(0, 0, text="MODEL: GEMINI-2.0-FLASH", fill=TEXT_MID, font=('Consolas', 8), anchor='e'),
            self._canvas.create_text(0, 0, text="VOICE: GUY NEURAL", fill=TEXT_MID, font=('Consolas', 8), anchor='e'),
            self._canvas.create_text(0, 0, text="LATENCY: 12ms", fill=TEXT_MUTED, font=('Consolas', 7), anchor='e'),
            self._canvas.create_text(0, 0, text="SECURITY: ACTIVE", fill=TEXT_MUTED, font=('Consolas', 7), anchor='e'),
        ]

        # 10. Bottom Dual Oscilloscope Wave
        self._osc_line_1 = self._canvas.create_line([0, 0, 0, 0], fill=CYAN_DARK, width=1, smooth=True)
        self._osc_line_2 = self._canvas.create_line([0, 0, 0, 0], fill='#001828', width=1, smooth=True)

    def _build_dialogue_hud(self):
        """Single sleek high-tech dialogue & telemetry subtitle banner."""
        dialogue_frame = tk.Frame(self.root, bg=PANEL_BG, height=68)
        dialogue_frame.pack(fill='x', padx=18, pady=(2, 6))
        dialogue_frame.pack_propagate(False)

        # Border line
        tk.Frame(dialogue_frame, bg=CYAN_DARK, height=1).pack(fill='x')

        inner_box = tk.Frame(dialogue_frame, bg=PANEL_BG)
        inner_box.pack(fill='both', expand=True, padx=14, pady=6)

        # Status indicator row
        top_row = tk.Frame(inner_box, bg=PANEL_BG)
        top_row.pack(fill='x')

        self._hud_tag = tk.Label(
            top_row, text="● TELEMETRY STREAM",
            bg=PANEL_BG, fg=CYAN_MID,
            font=('Consolas', 8, 'bold')
        )
        self._hud_tag.pack(side='left')

        self._hud_time = tk.Label(
            top_row, text=datetime.now().strftime("%H:%M:%S"),
            bg=PANEL_BG, fg=TEXT_MUTED,
            font=('Consolas', 8)
        )
        self._hud_time.pack(side='right')

        # Main response readout
        self._dialogue_lbl = tk.Label(
            inner_box,
            text="All systems nominal. Ready for interaction.",
            bg=PANEL_BG, fg=TEXT_BRIGHT,
            font=('Consolas', 9),
            anchor='w', justify='left',
            wraplength=580
        )
        self._dialogue_lbl.pack(fill='x', pady=(2, 0))

    def _build_footer(self):
        """Bottom HUD activation trigger button."""
        footer = tk.Frame(self.root, bg=BG, height=58)
        footer.pack(fill='x', padx=18, pady=(0, 10))
        footer.pack_propagate(False)

        hotkey = self.config.get('hotkey', 'F2').upper()
        self._activate_btn = tk.Button(
            footer,
            text=f"◉  ACTIVATE VOICE INTERFACE  [{hotkey}]",
            command=self._on_mic_click,
            bg='#020B1A', fg=CYAN_CORE,
            activebackground='#041530', activeforeground='#FFFFFF',
            relief='flat', bd=0,
            font=('Consolas', 11, 'bold'),
            cursor='hand2',
            height=2,
        )
        self._activate_btn.pack(fill='both', expand=True)

    # ── Canvas Resize & Coordinate Calculation ────────────────────────────────

    def _on_canvas_resize(self, event):
        """Dynamically recompute geometry when window is resized or maximized."""
        if event.width < 50 or event.height < 50:
            return

        self._w = event.width
        self._h = event.height
        self._cx = self._w / 2
        self._cy = self._h / 2
        # Dynamic base radius: smoothly scales from windowed (~90px) to full screen (~200px+)
        self._base_r = max(80, min(self._w * 0.22, self._h * 0.30))

        # Update dialogue label wrap width
        self._dialogue_lbl.configure(wraplength=max(400, self._w - 60))

        # Update corner brackets
        size = 24
        coords = [
            (20, 20, 20 + size, 20), (20, 20, 20, 20 + size),
            (self._w - 20, 20, self._w - 20 - size, 20), (self._w - 20, 20, self._w - 20, 20 + size),
            (20, self._h - 20, 20 + size, self._h - 20), (20, self._h - 20, 20, self._h - 20 - size),
            (self._w - 20, self._h - 20, self._w - 20 - size, self._h - 20), (self._w - 20, self._h - 20, self._w - 20, self._h - 20 - size)
        ]
        for idx, (x1, y1, x2, y2) in enumerate(coords):
            self._canvas.coords(self._corner_lines[idx], x1, y1, x2, y2)

        # Update background grid lines
        grid_margin = 40
        self._canvas.coords(self._bg_lines[0], 0, self._cy, self._w, self._cy)
        self._canvas.coords(self._bg_lines[1], self._cx, 0, self._cx, self._h)
        self._canvas.coords(self._bg_lines[2], grid_margin, 0, grid_margin, self._h)
        self._canvas.coords(self._bg_lines[3], self._w - grid_margin, 0, self._w - grid_margin, self._h)
        self._canvas.coords(self._bg_lines[4], 0, grid_margin, self._w, grid_margin)
        self._canvas.coords(self._bg_lines[5], 0, self._h - grid_margin, self._w, self._h - grid_margin)

    # ── Real-Time Animation Loop ──────────────────────────────────────────────

    def _start_animation(self):
        self._animate()

    def _animate(self):
        """Update visualizer telemetry, Arc Reactor rotation, and frequency bars."""
        if not self._anim_running:
            return

        t = time.time()
        cfg = STATE_CFG[self._status]
        color_bright = cfg['bright']
        amp = cfg['amp']
        speed = cfg['speed']

        cx, cy, br = self._cx, self._cy, self._base_r
        max_h = br * 0.45

        # ── 1. Telemetry Rings & Degrees ──
        r_outer = br * 1.85
        r_deg   = br * 1.68
        r_inner = br * 1.48

        self._canvas.coords(self._ring_outer_border, cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer)
        self._canvas.coords(self._ring_degree_track, cx - r_deg, cy - r_deg, cx + r_deg, cy + r_deg)
        self._canvas.coords(self._ring_inner_track,  cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner)

        self._canvas.coords(self._deg_000, cx, cy - r_deg - 7)
        self._canvas.coords(self._deg_090, cx + r_deg + 14, cy)
        self._canvas.coords(self._deg_180, cx, cy + r_deg + 7)
        self._canvas.coords(self._deg_270, cx - r_deg - 14, cy)

        # ── 2. Rotating Outer Segmented Arcs ──
        self._rot_outer += 0.018
        arc_r = br * 1.62
        for j, arc_id in enumerate(self._outer_arcs):
            base_ang = self._rot_outer + j * (math.pi / 2)
            span = 0.52
            pts = []
            steps = 8
            for s in range(steps + 1):
                ang = base_ang + (s / steps) * span
                pts.append(cx + arc_r * math.cos(ang))
                pts.append(cy + arc_r * math.sin(ang))
            self._canvas.coords(arc_id, *pts)
            self._canvas.itemconfig(arc_id, fill=cfg['dim'])

        # ── 3. Counter-Rotating Inner Ticks ──
        self._rot_inner -= 0.014
        tick_r1 = br * 1.44
        tick_r2 = br * 1.50
        for k, tick_id in enumerate(self._inner_ticks):
            ang = self._rot_inner + k * (2 * math.pi / 16)
            self._canvas.coords(
                tick_id,
                cx + tick_r1 * math.cos(ang), cy + tick_r1 * math.sin(ang),
                cx + tick_r2 * math.cos(ang), cy + tick_r2 * math.sin(ang)
            )
            self._canvas.itemconfig(tick_id, fill='#003850')

        # ── 4. Equalizer Frequency Bars ──
        for i, bar_id in enumerate(self._bars):
            ang = (i / NUM_BARS) * 2 * math.pi - math.pi / 2
            phase = self._phases[i]

            if self._status == 'speaking':
                h = amp * abs(
                    0.50 * math.sin(t * speed + phase) +
                    0.28 * math.sin(t * speed * 1.82 + phase * 1.3) +
                    0.14 * math.sin(t * speed * 3.14 + phase * 0.7) +
                    0.08 * math.sin(t * speed * 4.88 + phase * 2.1)
                ) + random.uniform(0, 5)
            elif self._status == 'listening':
                h = amp * abs(
                    0.65 * math.sin(t * speed + phase) +
                    0.35 * math.sin(t * speed * 2.4 + phase * 1.5)
                ) + random.uniform(0, 14)
            elif self._status == 'thinking':
                bar_ang = (i / NUM_BARS) * 2 * math.pi
                sweep = (t * speed) % (2 * math.pi)
                diff = abs(bar_ang - sweep) % (2 * math.pi)
                if diff > math.pi:
                    diff = 2 * math.pi - diff
                h = amp * max(0.0, 1.0 - diff / 0.85) + 6 * abs(math.sin(t * 1.8 + phase))
            else:
                h = amp * abs(math.sin(t * speed + phase))

            h = max(2, min(h, max_h))
            cos_a = math.cos(ang)
            sin_a = math.sin(ang)

            self._canvas.coords(
                bar_id,
                cx + br * cos_a, cy + br * sin_a,
                cx + (br + h) * cos_a, cy + (br + h) * sin_a
            )
            intensity = h / max_h
            self._canvas.itemconfig(bar_id, fill=self._lerp_color(cfg['dim'], color_bright, intensity))

        # ── 5. Arc Reactor Core Rings & Nucleus Glow ──
        ir = br - 4
        self._canvas.coords(self._core_mask_outer, cx - ir, cy - ir, cx + ir, cy + ir)
        self._canvas.coords(self._core_ring_gold,  cx - (br * 0.88), cy - (br * 0.88), cx + (br * 0.88), cy + (br * 0.88))
        self._canvas.coords(self._core_ring_cyan,  cx - (br * 0.76), cy - (br * 0.76), cx + (br * 0.76), cy + (br * 0.76))

        # Core Glow Nucleus
        pulse = 0.5 + 0.5 * math.sin(t * 2.8)
        glow_r1 = br * 0.58
        glow_r2 = br * 0.44
        glow_r3 = br * 0.30
        self._canvas.coords(self._core_glow_3, cx - glow_r1, cy - glow_r1, cx + glow_r1, cy + glow_r1)
        self._canvas.coords(self._core_glow_2, cx - glow_r2, cy - glow_r2, cx + glow_r2, cy + glow_r2)
        self._canvas.coords(self._core_glow_1, cx - glow_r3, cy - glow_r3, cx + glow_r3, cy + glow_r3)

        self._canvas.itemconfig(self._core_glow_1, fill=self._lerp_color('#000A14', cfg['core_color'], pulse * 0.75))
        self._canvas.itemconfig(self._core_glow_2, fill=self._lerp_color('#00060E', cfg['glow'], pulse * 0.50))

        # Center typography
        self._canvas.coords(self._center_title, cx, cy - (br * 0.10))
        self._canvas.coords(self._center_status, cx, cy + (br * 0.12))

        # ── 6. Update Live Telemetry & Hardware Gauges ──
        if t - self._last_telemetry_check > 1.8:
            self._last_telemetry_check = t
            if PSUTIL_AVAILABLE:
                try:
                    self._cpu_val = psutil.cpu_percent()
                    self._ram_val = psutil.virtual_memory().percent
                except Exception:
                    pass

        # Left Telemetry Coordinates
        left_x = 42
        top_y  = max(55, cy - (br * 0.9))
        self._canvas.coords(self._tel_left_box[0], left_x, top_y)
        self._canvas.coords(self._tel_left_box[1], left_x, top_y + 20)
        self._canvas.coords(self._tel_left_box[2], left_x, top_y + 46)
        self._canvas.coords(self._tel_left_box[3], left_x, top_y + 72)
        self._canvas.coords(self._tel_left_box[4], left_x, top_y + 88)

        self._canvas.itemconfig(self._tel_left_box[1], text=f"CPU: {self._cpu_val:.0f}%")
        self._canvas.itemconfig(self._tel_left_box[2], text=f"RAM: {self._ram_val:.0f}%")

        # CPU/RAM mini progress bars
        gauge_w = 90
        self._canvas.coords(self._gauge_cpu_bg, left_x, top_y + 32, left_x + gauge_w, top_y + 32)
        self._canvas.coords(self._gauge_cpu_fill, left_x, top_y + 32, left_x + (gauge_w * (self._cpu_val / 100)), top_y + 32)

        self._canvas.coords(self._gauge_ram_bg, left_x, top_y + 58, left_x + gauge_w, top_y + 58)
        self._canvas.coords(self._gauge_ram_fill, left_x, top_y + 58, left_x + (gauge_w * (self._ram_val / 100)), top_y + 58)

        # Right Diagnostics Coordinates
        right_x = self._w - 42
        self._canvas.coords(self._tel_right_box[0], right_x, top_y)
        self._canvas.coords(self._tel_right_box[1], right_x, top_y + 20)
        self._canvas.coords(self._tel_right_box[2], right_x, top_y + 36)
        self._canvas.coords(self._tel_right_box[3], right_x, top_y + 54)
        self._canvas.coords(self._tel_right_box[4], right_x, top_y + 70)

        # ── 7. Update Dual Oscilloscope Waves ──
        osc_w = min(self._w * 0.72, 600)
        start_x = cx - osc_w / 2
        base_y  = self._h - 32
        pts_1, pts_2 = [], []
        for p in range(self._osc_points):
            px = start_x + p * (osc_w / (self._osc_points - 1))
            val_1 = math.sin(t * speed * 1.3 + p * 0.24) * (amp * 0.24)
            val_2 = math.cos(t * speed * 0.8 + p * 0.18) * (amp * 0.14)
            pts_1.extend([px, base_y + val_1])
            pts_2.extend([px, base_y + 6 + val_2])

        self._canvas.coords(self._osc_line_1, *pts_1)
        self._canvas.coords(self._osc_line_2, *pts_2)
        self._canvas.itemconfig(self._osc_line_1, fill=cfg['mid'])

        # Update clock
        self._hud_time.configure(text=datetime.now().strftime("%H:%M:%S"))

        # Schedule next animation frame
        self.root.after(1000 // FPS, self._animate)

    @staticmethod
    def _lerp_color(hex1: str, hex2: str, t: float) -> str:
        """Linear interpolate between two hex color codes."""
        t = max(0.0, min(1.0, t))
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f'#{r:02x}{g:02x}{b:02x}'

    # ── Window Mode & Controls ────────────────────────────────────────────────

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.root.attributes('-fullscreen', self._fullscreen)
        self.add_system_message(f"Display Mode: {'FULLSCREEN MATRIX' if self._fullscreen else 'WINDOWED CONSOLE'}")

    def _exit_fullscreen(self):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes('-fullscreen', False)

    def _toggle_topmost(self):
        current = self.root.attributes('-topmost')
        self.root.attributes('-topmost', not current)
        self.add_system_message(f"HUD Pin Mode: {'ENGAGED' if not current else 'RELEASED'}")

    def bring_to_front(self):
        """Restore, deiconify, and lift ARIA window into active focus (thread-safe)."""
        def _lift():
            try:
                self.root.deiconify()
                self.root.attributes('-topmost', True)
                self.root.lift()
                self.root.focus_force()
            except Exception:
                pass
        self.root.after(0, _lift)

    def toggle_visibility(self):
        """Toggle window show/hide from global shortcut (thread-safe)."""
        def _toggle():
            try:
                if self.root.state() == 'withdrawn' or self.root.state() == 'iconic':
                    self.root.deiconify()
                    self.root.attributes('-topmost', True)
                    self.root.lift()
                    self.root.focus_force()
                elif self.root.winfo_viewable() and self.root.focus_displayof():
                    self.root.iconify()
                else:
                    self.root.deiconify()
                    self.root.attributes('-topmost', True)
                    self.root.lift()
                    self.root.focus_force()
            except Exception:
                pass
        self.root.after(0, _toggle)

    # ── Public State & Message API (Thread-Safe) ──────────────────────────────

    def set_status(self, status: str, custom_text: str = None):
        """Update system state — drives Arc Reactor frequency animation."""
        self._status = status
        cfg = STATE_CFG.get(status, STATE_CFG['idle'])
        label = custom_text or cfg['label']
        hotkey = self.config.get('hotkey', 'F2').upper()

        btn_labels = {
            'idle':      f"◉  ACTIVATE VOICE INTERFACE  [{hotkey}]",
            'listening': "◎  LISTENING... (SPEAK COMMAND)",
            'thinking':  "◈  NEURAL SYNTHESIS IN PROGRESS...",
            'speaking':  "◉  TRANSMITTING VOCAL MATRIX...",
            'error':     "⚠  TELEMETRY FAULT — RETRY",
        }
        btn_txt = btn_labels.get(status, f"◉  ACTIVATE VOICE INTERFACE  [{hotkey}]")

        btn_colors = {
            'idle':      ('#020B1A', CYAN_CORE),
            'listening': ('#001810', '#00FF99'),
            'thinking':  ('#1A1200', '#FFB800'),
            'speaking':  ('#001524', '#00F0FF'),
            'error':     ('#1C0508', ALERT_RED),
        }
        btn_bg, btn_fg = btn_colors.get(status, ('#020B1A', CYAN_CORE))

        def _update():
            self._canvas.itemconfig(self._center_status, text=label, fill=cfg['bright'])
            self._activate_btn.configure(text=btn_txt, bg=btn_bg, fg=btn_fg)
            self._hud_tag.configure(text=f"● {cfg['sub_status']}", fg=cfg['bright'])

        self.root.after(0, _update)

    def add_user_message(self, text: str):
        """Display user voice command in the dialogue HUD."""
        def _update():
            user_name = self.config.get('user_name', 'Madhav').upper()
            self._dialogue_lbl.configure(text=f"{user_name}: \"{text}\"", fg=CYAN_NEON)
        self.root.after(0, _update)

    def add_aria_message(self, text: str):
        """Display ARIA vocal response in the dialogue HUD."""
        def _update():
            self._dialogue_lbl.configure(text=f"ARIA: {text}", fg=TEXT_BRIGHT)
        self.root.after(0, _update)

    def add_system_message(self, text: str):
        """Display telemetry system alert in the dialogue HUD."""
        def _update():
            self._dialogue_lbl.configure(text=f"SYSTEM // {text}", fg=TEXT_MID)
        self.root.after(0, _update)

    # ── Practical & Intuitive Settings Console ────────────────────────────────

    def _open_settings(self):
        """Practical, intuitive JARVIS system settings console with live voice testing."""
        win = tk.Toplevel(self.root)
        win.title("SYSTEM CONFIGURATION // ARIA")
        win.geometry("520x620")
        win.minsize(480, 540)
        win.configure(bg=BG)
        win.attributes('-topmost', True)
        win.grab_set()

        # Modal Header
        top_hdr = tk.Frame(win, bg=BG)
        top_hdr.pack(fill='x', padx=24, pady=(18, 4))

        tk.Label(
            top_hdr, text="⚙  STARK INDUSTRIES // SYSTEM CONFIGURATION",
            bg=BG, fg=CYAN_CORE, font=('Consolas', 12, 'bold')
        ).pack(anchor='w')
        tk.Label(
            top_hdr, text="Configure Operator Identity, Gemini Neural Keys, and Voice Profiles.",
            bg=BG, fg=TEXT_MUTED, font=('Consolas', 8)
        ).pack(anchor='w')

        tk.Frame(win, bg=CYAN_DARK, height=1).pack(fill='x', padx=20, pady=8)

        # Scrollable Settings Container
        canvas_settings = tk.Canvas(win, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas_settings.yview, bg=BG)
        scroll_frame = tk.Frame(canvas_settings, bg=BG)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas_settings.configure(scrollregion=canvas_settings.bbox("all"))
        )
        canvas_settings.create_window((0, 0), window=scroll_frame, anchor="nw", width=470)
        canvas_settings.configure(yscrollcommand=scrollbar.set)

        canvas_settings.pack(side="left", fill="both", expand=True, padx=(20, 0))
        scrollbar.pack(side="right", fill="y", padx=(0, 10))

        # ── Form Helper Functions ──
        def section_title(text):
            f = tk.Frame(scroll_frame, bg=BG)
            f.pack(fill='x', pady=(12, 4))
            tk.Label(f, text=f"◈ {text}", bg=BG, fg=CYAN_NEON, font=('Consolas', 9, 'bold')).pack(anchor='w')
            tk.Frame(f, bg='#001E2E', height=1).pack(fill='x', pady=2)

        def input_field(label_text, var, show=None, note=""):
            f = tk.Frame(scroll_frame, bg=BG)
            f.pack(fill='x', pady=4)
            tk.Label(f, text=label_text, bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')
            e = tk.Entry(
                f, textvariable=var,
                bg='#030C1A', fg=CYAN_CORE,
                insertbackground=CYAN_CORE,
                relief='flat', font=('Consolas', 10),
                show=show or ''
            )
            e.pack(fill='x', ipady=4, pady=2)
            if note:
                tk.Label(f, text=note, bg=BG, fg=TEXT_MUTED, font=('Consolas', 7)).pack(anchor='w')
            return e

        # Form Variables
        user_var    = tk.StringVar(value=self.config.get('user_name', 'Madhav'))
        api_var     = tk.StringVar(value=self.config.get('gemini_api_key', ''))
        hotkey_var  = tk.StringVar(value=self.config.get('hotkey', 'P'))
        summon_var  = tk.StringVar(value=self.config.get('summon_hotkey', 'ctrl+space'))
        city_var    = tk.StringVar(value=self.config.get('weather_city', ''))
        speed_var   = tk.IntVar(value=self.config.get('voice_speed', 175))
        voice_var   = tk.StringVar(value=self.config.get('voice_name', 'en-US-GuyNeural'))
        lang_var    = tk.StringVar(value=self.config.get('stt_language', 'en-IN'))

        # ── 1. Operator Identity ──
        section_title("OPERATOR PROFILE")
        input_field("OPERATOR NAME", user_var, note="Your name for personalized voice greetings & interactions.")

        # ── 2. Neural AI Engine ──
        section_title("GEMINI NEURAL AI CORE")
        api_entry = input_field("GEMINI API KEY", api_var, show='*', note="Free API key from aistudio.google.com/apikey")

        # ── 3. Voice Matrix & Audio Profile ──
        section_title("MALE NEURAL VOICE MATRIX")
        vf = tk.Frame(scroll_frame, bg=BG)
        vf.pack(fill='x', pady=4)
        tk.Label(vf, text="SELECT VOICE PROFILE", bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')

        voice_options = [
            ("en-US-GuyNeural", "Guy (American Male - Warm & Charismatic Best Friend)"),
            ("en-US-ChristopherNeural", "Christopher (American Male - Smooth & Confident)"),
            ("en-GB-RyanNeural", "Ryan (British Male - Classic Jarvis Style)"),
            ("en-US-BrianNeural", "Brian (American Male - Casual & Friendly)"),
            ("en-US-EricNeural", "Eric (American Male - Crisp & Clear)"),
        ]

        voice_menu = tk.OptionMenu(vf, voice_var, *[v[0] for v in voice_options])
        voice_menu.config(
            bg='#030C1A', fg=CYAN_NEON,
            activebackground='#061628', activeforeground=CYAN_CORE,
            relief='flat', highlightthickness=0,
            font=('Consolas', 9), cursor='hand2'
        )
        voice_menu["menu"].config(bg='#030C1A', fg=CYAN_NEON, font=('Consolas', 9))
        voice_menu.pack(fill='x', pady=2)

        # Voice Test Button
        def _test_voice_sample():
            chosen_voice = voice_var.get().strip() or "en-US-GuyNeural"
            name = user_var.get().strip() or "Madhav"
            sample_text = f"Hey {name}! This is how my voice sounds. All neural systems are ready to roll!"

            def _play_sample():
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                        temp_path = f.name
                    async def _gen():
                        comm = edge_tts.Communicate(sample_text, voice=chosen_voice)
                        await comm.save(temp_path)
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(_gen())
                    loop.close()
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                    pygame.mixer.music.unload()
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as ex:
                    print(f"[Settings] Test voice error: {ex}")

            threading.Thread(target=_play_sample, daemon=True).start()

        test_btn = tk.Button(
            vf, text="🔊  LISTEN TO VOICE SAMPLE",
            command=_test_voice_sample,
            bg='#002438', fg=CYAN_CORE,
            activebackground='#003C58', activeforeground='#FFFFFF',
            relief='flat', bd=0, font=('Consolas', 8, 'bold'),
            cursor='hand2', pady=4
        )
        test_btn.pack(anchor='w', pady=(3, 6))

        # Speed Slider
        sf = tk.Frame(scroll_frame, bg=BG)
        sf.pack(fill='x', pady=4)
        tk.Label(sf, text="VOCAL SPEED CADENCE", bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')
        slider_row = tk.Frame(sf, bg=BG)
        slider_row.pack(fill='x')
        tk.Scale(
            slider_row, variable=speed_var, from_=110, to=240,
            orient='horizontal', bg=BG, fg=CYAN_CORE,
            troughcolor='#001A2A', highlightthickness=0,
            font=('Consolas', 8), length=350
        ).pack(side='left')
        tk.Label(slider_row, textvariable=speed_var, bg=BG, fg=CYAN_MID, font=('Consolas', 9), width=4).pack(side='left')

        # ── 4. Speech Recognition Language ──
        section_title("SPEECH RECOGNITION (STT)")
        lf = tk.Frame(scroll_frame, bg=BG)
        lf.pack(fill='x', pady=4)
        tk.Label(lf, text="MICROPHONE ACCENT / LANGUAGE", bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')
        lang_options = [
            ("en-IN", "Indian English / Hinglish (en-IN - Recommended)"),
            ("en-US", "American English (en-US)"),
            ("en-GB", "British English (en-GB)"),
        ]
        lang_menu = tk.OptionMenu(lf, lang_var, *[l[0] for l in lang_options])
        lang_menu.config(
            bg='#030C1A', fg=CYAN_NEON,
            activebackground='#061628', activeforeground=CYAN_CORE,
            relief='flat', highlightthickness=0,
            font=('Consolas', 9), cursor='hand2'
        )
        lang_menu["menu"].config(bg='#030C1A', fg=CYAN_NEON, font=('Consolas', 9))
        lang_menu.pack(fill='x', pady=2)

        # ── 5. Input Triggers & Regional Telemetry ──
        section_title("HOTKEYS & LOCATION")
        input_field("VOICE ACTIVATION HOTKEY", hotkey_var, note="Press to speak immediately (e.g. P, F2, Space)")
        input_field("SUMMON / TOGGLE WINDOW SHORTCUT", summon_var, note="Global shortcut to show/hide ARIA from anywhere (e.g. ctrl+space, alt+space)")
        input_field("DEFAULT WEATHER REGION", city_var, note="City name for live atmospheric updates (e.g. Delhi, Mumbai)")

        # ── Bottom Action Buttons ──
        btn_action_frame = tk.Frame(win, bg=BG)
        btn_action_frame.pack(fill='x', padx=20, pady=12)

        def _save():
            self.config['user_name']      = user_var.get().strip() or 'Madhav'
            self.config['gemini_api_key'] = api_var.get().strip()
            self.config['hotkey']         = hotkey_var.get().strip() or 'P'
            self.config['summon_hotkey']  = summon_var.get().strip() or 'ctrl+space'
            self.config['stt_language']   = lang_var.get().strip() or 'en-IN'
            self.config['weather_city']   = city_var.get().strip()
            self.config['voice_name']     = voice_var.get().strip() or 'en-US-GuyNeural'
            self.config['voice_speed']    = speed_var.get()

            # Update header display
            self._header_user_lbl.configure(text=f"OPERATOR: {self.config['user_name'].upper()}  |  QUANTUM NEURAL CORE: ONLINE")
            self._activate_btn.configure(text=f"◉  ACTIVATE VOICE INTERFACE  [{self.config['hotkey'].upper()}]")

            if self.on_api_key_save:
                self.on_api_key_save(self.config)

            win.destroy()
            self.add_system_message("Configuration synchronized successfully.")

        tk.Button(
            btn_action_frame, text="▶  SAVE & SYNCHRONIZE",
            command=_save,
            bg='#002840', fg=CYAN_CORE,
            activebackground='#004870', activeforeground='#FFFFFF',
            relief='flat', bd=0, font=('Consolas', 10, 'bold'),
            cursor='hand2', pady=8
        ).pack(side='left', fill='x', expand=True, padx=(0, 6))

        tk.Button(
            btn_action_frame, text="✕  CANCEL",
            command=win.destroy,
            bg='#030B18', fg=TEXT_MUTED,
            activebackground='#081828', activeforeground=TEXT_MID,
            relief='flat', bd=0, font=('Consolas', 10),
            cursor='hand2', pady=8, width=10
        ).pack(side='right')

    def _on_mic_click(self):
        if self.on_listen_request:
            threading.Thread(target=self.on_listen_request, daemon=True).start()

    def _reset_memory(self):
        if self.on_reset_memory:
            self.on_reset_memory()
        self.add_system_message("Neural conversation history cleared.")

    def _on_close(self):
        self._anim_running = False
        self.root.destroy()

    # ── Event Loop ────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()

    def destroy(self):
        self._anim_running = False
        try:
            self.root.destroy()
        except Exception:
            pass
