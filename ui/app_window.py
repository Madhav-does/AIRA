"""
ARIA — A.R.I.A. JARVIS-Style Holographic Interface
Iron Man / JARVIS faithful recreation with:
- Hexagonal background grid
- Animated arc reactor center ring (voice frequency visualizer)
- Rotating outer scan rings
- Holographic data panels (left / right / bottom)
- Real-time CPU / RAM gauges
- Blue layered glow pulses
- Text telemetry streams
"""

import tkinter as tk
import math
import random
import time
import threading
import os
import asyncio
from datetime import datetime

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

# ── JARVIS Colour Palette ──────────────────────────────────────────────────────
BG          = "#010409"     # Near-black background
HEX_GRID    = "#03111E"     # Hex grid line colour
PANEL_EDGE  = "#0A2840"     # Panel border
CYAN_BRIGHT = "#00E5FF"     # Primary bright cyan
CYAN_MID    = "#0099CC"     # Mid cyan
CYAN_DIM    = "#004466"     # Dim structural cyan
CYAN_GLOW   = "#002233"     # Ambient glow
BLUE_RING   = "#0055AA"     # Outer ring blue
BLUE_INNER  = "#003377"     # Inner ring
GOLD        = "#FFB700"     # Stark gold accent
GOLD_DIM    = "#664A00"
TEXT_HI     = "#CCF0FF"     # Bright HUD text
TEXT_MID    = "#5BA8C8"     # Secondary text
TEXT_DIM    = "#1A4A64"     # Muted ambient text
ALERT       = "#FF2244"     # Error/alert red

# Status configs
STATE = {
    'idle': {
        'bright': '#00C5E5', 'mid': '#006B8A', 'dim': '#001E2A',
        'label': 'STANDBY', 'amp': 6, 'speed': 1.0,
        'glow': '#001020', 'ring': '#001C30', 'status': 'AWAITING INPUT',
    },
    'listening': {
        'bright': '#00FF99', 'mid': '#00BB70', 'dim': '#003322',
        'label': 'LISTENING', 'amp': 55, 'speed': 7.0,
        'glow': '#002214', 'ring': '#003322', 'status': 'VOICE ACQUISITION ACTIVE',
    },
    'thinking': {
        'bright': '#FFB700', 'mid': '#BB8800', 'dim': '#442E00',
        'label': 'PROCESSING', 'amp': 30, 'speed': 3.5,
        'glow': '#1A1000', 'ring': '#221800', 'status': 'NEURAL SYNTHESIS IN PROGRESS',
    },
    'speaking': {
        'bright': '#00E5FF', 'mid': '#0088BB', 'dim': '#002A3A',
        'label': 'TRANSMITTING', 'amp': 65, 'speed': 9.0,
        'glow': '#001828', 'ring': '#002233', 'status': 'AUDIO OUTPUT ACTIVE',
    },
    'error': {
        'bright': '#FF2244', 'mid': '#AA1530', 'dim': '#330A12',
        'label': 'FAULT', 'amp': 20, 'speed': 3.0,
        'glow': '#200508', 'ring': '#2A0810', 'status': 'SYSTEM EXCEPTION DETECTED',
    },
}

NUM_BARS  = 128    # Arc reactor frequency bars
FPS       = 40     # Animation frame rate
HEX_SIZE  = 28     # Hexagonal grid cell size


class AppWindow:
    """
    Full JARVIS holographic HUD for ARIA.
    Faithful Iron Man aesthetic with hex grid, arc reactor visualizer,
    scan rings, holographic panels, and live telemetry.
    """

    def __init__(self, config, on_listen_request=None, on_api_key_save=None, on_reset_memory=None):
        self.config = config
        self.on_listen_request = on_listen_request
        self.on_api_key_save = on_api_key_save
        self.on_reset_memory = on_reset_memory

        # Geometry
        self._w = 900
        self._h = 680
        self._cx = self._w / 2
        self._cy = self._h / 2 - 30
        self._base_r = 140
        self._fullscreen = False

        # Animation
        self._status = 'idle'
        self._anim_running = True
        self._rot1 = 0.0     # outer ring rotation
        self._rot2 = 0.0     # inner ring (counter)
        self._rot3 = 0.0     # dashed scan ring
        self._phases = [random.uniform(0, 2 * math.pi) for _ in range(NUM_BARS)]
        self._bar_vals = [0.0] * NUM_BARS
        self._osc_t = 0.0

        # Hardware telemetry
        self._cpu = 0
        self._ram = 0
        self._tel_tick = 0

        # Dialogue
        self._last_text = "ALL SYSTEMS NOMINAL — READY FOR INTERACTION"
        self._last_source = "SYSTEM"
        self._dialogue_scroll = []

        # Root window
        self.root = tk.Tk()
        self.root.title("A.R.I.A. // STARK INDUSTRIES")
        self.root.geometry(f"{self._w}x{self._h}")
        self.root.minsize(700, 520)
        self.root.configure(bg=BG)
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self._exit_fullscreen())

        self._build_ui()
        self._start_animation()

    # ─────────────────────────────────────────────────────────────────────────
    # UI Construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top header bar
        self._build_header()
        # Main canvas (takes all space)
        self._canvas = tk.Canvas(self.root, bg=BG, bd=0, highlightthickness=0)
        self._canvas.pack(fill='both', expand=True)
        self._canvas.bind("<Configure>", self._on_resize)
        self._init_canvas_items()
        # Bottom control bar
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG, height=44)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        # Left: branding
        lf = tk.Frame(hdr, bg=BG)
        lf.pack(side='left', padx=14, fill='y')
        tk.Label(lf, text="◈  STARK INDUSTRIES  ·  A.R.I.A. SYSTEM v4.2",
                 bg=BG, fg=CYAN_BRIGHT, font=('Consolas', 10, 'bold')).pack(anchor='w', pady=(6, 0))
        user = self.config.get('user_name', 'MADHAV').upper()
        self._hdr_user = tk.Label(lf, text=f"OPERATOR: {user}  ·  NEURAL CORE: ONLINE",
                                   bg=BG, fg=TEXT_DIM, font=('Consolas', 7))
        self._hdr_user.pack(anchor='w')

        # Right: buttons
        rf = tk.Frame(hdr, bg=BG)
        rf.pack(side='right', padx=10, fill='y')
        for icon, cmd in [("⛶", self._toggle_fullscreen), ("⟳", self._reset_memory),
                           ("📌", self._toggle_topmost), ("⚙", self._open_settings)]:
            tk.Button(rf, text=icon, command=cmd, bg='#020C18', fg=CYAN_MID,
                      activebackground='#051830', activeforeground=CYAN_BRIGHT,
                      relief='flat', bd=0, font=('Consolas', 11), width=3, cursor='hand2'
                      ).pack(side='right', padx=2, pady=8)

        # Separator line
        tk.Frame(self.root, bg=PANEL_EDGE, height=1).pack(fill='x')

    def _build_footer(self):
        foot = tk.Frame(self.root, bg='#020C18', height=50)
        foot.pack(fill='x', side='bottom')
        foot.pack_propagate(False)

        tk.Frame(foot, bg=PANEL_EDGE, height=1).pack(fill='x')

        inner = tk.Frame(foot, bg='#020C18')
        inner.pack(fill='both', expand=True, padx=16, pady=6)

        hk = self.config.get('hotkey', 'P').upper()
        self._activate_btn = tk.Button(
            inner,
            text=f"◉   ACTIVATE VOICE INTERFACE   [ {hk} ]",
            command=self._on_mic_click,
            bg='#020C18', fg=CYAN_BRIGHT,
            activebackground='#031828', activeforeground='#FFFFFF',
            relief='flat', bd=0,
            font=('Consolas', 11, 'bold'),
            cursor='hand2'
        )
        self._activate_btn.pack(fill='both', expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Canvas Items
    # ─────────────────────────────────────────────────────────────────────────

    def _init_canvas_items(self):
        c = self._canvas

        # ── Layer 0: Hex grid (many polygons) ────────────────────────────────
        # We draw hex grid dynamically in the animation loop using a tag
        # to avoid pre-allocating hundreds of static items here.

        # ── Layer 1: Scan rings (concentric circles) ─────────────────────────
        self._ring_d1 = c.create_oval(0,0,1,1, outline='#001C30', width=1)   # outermost dim
        self._ring_d2 = c.create_oval(0,0,1,1, outline='#002844', width=1)
        self._ring_d3 = c.create_oval(0,0,1,1, outline='#003355', width=1)

        # Degree marks on outer ring
        self._deg_marks = [c.create_text(0,0, text=f"{i*30:03d}°", fill=TEXT_DIM, font=('Consolas',6)) for i in range(12)]

        # ── Layer 2: Rotating arc segments (outer scanner) ───────────────────
        self._outer_arcs = [c.create_arc(0,0,1,1, start=0, extent=20, outline=CYAN_DIM, style='arc', width=2) for _ in range(6)]
        # Inner counter-rotating dashes
        self._inner_arcs = [c.create_arc(0,0,1,1, start=0, extent=8, outline=BLUE_RING, style='arc', width=1) for _ in range(12)]

        # ── Layer 3: Frequency bars (arc reactor) ────────────────────────────
        self._freq_bars = [c.create_line(0,0,1,1, fill=CYAN_DIM, width=2, capstyle='round') for _ in range(NUM_BARS)]

        # ── Layer 4: Core circles ─────────────────────────────────────────────
        self._core_outer_mask = c.create_oval(0,0,1,1, fill=BG, outline='#003050', width=2)
        self._core_glow3 = c.create_oval(0,0,1,1, fill='#000D15', outline='#001825', width=1)
        self._core_glow2 = c.create_oval(0,0,1,1, fill='#001520', outline='#002840', width=1)
        self._core_glow1 = c.create_oval(0,0,1,1, fill='#001C2C', outline='#003C5A', width=2)
        self._core_gold  = c.create_oval(0,0,1,1, outline=GOLD_DIM, width=1)
        self._core_ring  = c.create_oval(0,0,1,1, outline=CYAN_DIM, width=2)

        # ── Layer 5: Center text ──────────────────────────────────────────────
        self._txt_name   = c.create_text(0,0, text="A.R.I.A.", fill=CYAN_BRIGHT, font=('Consolas', 20, 'bold'))
        self._txt_status = c.create_text(0,0, text="STANDBY", fill=CYAN_MID, font=('Consolas', 9, 'bold'))
        self._txt_sub    = c.create_text(0,0, text="AWAITING INPUT", fill=TEXT_DIM, font=('Consolas', 7))

        # ── Layer 6: Left panel — System telemetry ───────────────────────────
        self._lp_title  = c.create_text(0,0, text="◈ SYSTEM TELEMETRY", fill=CYAN_MID, font=('Consolas',8,'bold'), anchor='w')
        self._lp_cpu_l  = c.create_text(0,0, text="CPU  :", fill=TEXT_MID, font=('Consolas',8), anchor='w')
        self._lp_cpu_v  = c.create_text(0,0, text="0%", fill=CYAN_BRIGHT, font=('Consolas',8,'bold'), anchor='w')
        self._lp_ram_l  = c.create_text(0,0, text="RAM  :", fill=TEXT_MID, font=('Consolas',8), anchor='w')
        self._lp_ram_v  = c.create_text(0,0, text="0%", fill=CYAN_MID, font=('Consolas',8,'bold'), anchor='w')
        self._lp_cpu_bg = c.create_rectangle(0,0,1,1, fill='#001828', outline='#002840', width=1)
        self._lp_cpu_fg = c.create_rectangle(0,0,1,1, fill=CYAN_BRIGHT, outline='')
        self._lp_ram_bg = c.create_rectangle(0,0,1,1, fill='#001828', outline='#002840', width=1)
        self._lp_ram_fg = c.create_rectangle(0,0,1,1, fill=CYAN_MID, outline='')
        self._lp_audio  = c.create_text(0,0, text="AUDIO  : 48kHz", fill=TEXT_DIM, font=('Consolas',7), anchor='w')
        self._lp_link   = c.create_text(0,0, text="NEURAL : ONLINE", fill=TEXT_DIM, font=('Consolas',7), anchor='w')
        self._lp_time   = c.create_text(0,0, text="--:--:--", fill=TEXT_DIM, font=('Consolas',7), anchor='w')

        # Panel border lines
        self._lp_border = [c.create_line(0,0,1,1, fill=PANEL_EDGE, width=1) for _ in range(4)]

        # ── Layer 7: Right panel — Neural diagnostics ────────────────────────
        self._rp_title  = c.create_text(0,0, text="NEURAL DIAGNOSTICS ◈", fill=CYAN_MID, font=('Consolas',8,'bold'), anchor='e')
        self._rp_model  = c.create_text(0,0, text="MODEL  : GEMINI-2.0-FLASH", fill=TEXT_MID, font=('Consolas',7), anchor='e')
        self._rp_voice  = c.create_text(0,0, text="VOICE  : RYAN NEURAL", fill=TEXT_MID, font=('Consolas',7), anchor='e')
        self._rp_stt    = c.create_text(0,0, text="STT    : WHISPER / LOCAL", fill=TEXT_MID, font=('Consolas',7), anchor='e')
        self._rp_lat    = c.create_text(0,0, text="LATENCY: <100ms", fill=TEXT_DIM, font=('Consolas',7), anchor='e')
        self._rp_sec    = c.create_text(0,0, text="SECURE : ACTIVE", fill=TEXT_DIM, font=('Consolas',7), anchor='e')
        self._rp_border = [c.create_line(0,0,1,1, fill=PANEL_EDGE, width=1) for _ in range(4)]

        # ── Layer 8: Bottom dialogue panel ───────────────────────────────────
        self._dp_bg     = c.create_rectangle(0,0,1,1, fill='#020B18', outline=PANEL_EDGE, width=1)
        self._dp_src    = c.create_text(0,0, text="● SYSTEM", fill=CYAN_MID, font=('Consolas',8,'bold'), anchor='w')
        self._dp_time   = c.create_text(0,0, text="--:--:--", fill=TEXT_DIM, font=('Consolas',7), anchor='e')
        self._dp_text   = c.create_text(0,0, text="ALL SYSTEMS NOMINAL — READY FOR INTERACTION",
                                        fill=TEXT_HI, font=('Consolas', 9), anchor='w', width=600)
        self._dp_divider = c.create_line(0,0,1,1, fill=PANEL_EDGE, width=1)

        # Corner brackets
        self._corners = [c.create_line(0,0,1,1, fill=CYAN_DIM, width=1) for _ in range(8)]

        # Oscilloscope bottom
        self._osc1 = c.create_line([0,0,1,1], fill=CYAN_DIM, width=1, smooth=True)
        self._osc2 = c.create_line([0,0,1,1], fill='#001828', width=1, smooth=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Resize Handler
    # ─────────────────────────────────────────────────────────────────────────

    def _on_resize(self, event):
        if event.width < 50 or event.height < 50:
            return
        self._w = event.width
        self._h = event.height
        self._cx = self._w / 2
        # Center is slightly above middle to leave room for dialogue panel
        self._cy = self._h * 0.44
        self._base_r = max(90, min(self._w * 0.20, self._h * 0.28))

        # Update dialogue text wrap
        self._canvas.itemconfig(self._dp_text, width=max(300, self._w - 80))

        # Corner brackets
        s = 20
        coords = [
            (8, 8, 8+s, 8), (8, 8, 8, 8+s),
            (self._w-8, 8, self._w-8-s, 8), (self._w-8, 8, self._w-8, 8+s),
            (8, self._h-8, 8+s, self._h-8), (8, self._h-8, 8, self._h-8-s),
            (self._w-8, self._h-8, self._w-8-s, self._h-8), (self._w-8, self._h-8, self._w-8, self._h-8-s),
        ]
        for i, (x1, y1, x2, y2) in enumerate(coords):
            self._canvas.coords(self._corners[i], x1, y1, x2, y2)

    # ─────────────────────────────────────────────────────────────────────────
    # Main Animation Loop
    # ─────────────────────────────────────────────────────────────────────────

    def _start_animation(self):
        self._animate()

    def _animate(self):
        if not self._anim_running:
            return

        t = time.time()
        s = STATE[self._status]
        amp   = s['amp']
        speed = s['speed']
        bright = s['bright']
        mid    = s['mid']
        dim    = s['dim']

        cx, cy, r = self._cx, self._cy, self._base_r
        c = self._canvas

        # ── Draw hex grid ─────────────────────────────────────────────────────
        self._draw_hex_grid(cx, cy, r)

        # ── Frequency bars ────────────────────────────────────────────────────
        bar_inner_r = r * 0.95
        bar_outer_r = r * 0.95
        for i in range(NUM_BARS):
            angle = (2 * math.pi * i / NUM_BARS) - math.pi / 2
            target = amp * (0.35 + 0.65 * abs(math.sin(t * speed * 0.7 + self._phases[i])))
            self._bar_vals[i] += (target - self._bar_vals[i]) * 0.22
            h = self._bar_vals[i]
            inner_r = bar_inner_r
            outer_r = bar_outer_r + h

            x1 = cx + inner_r * math.cos(angle)
            y1 = cy + inner_r * math.sin(angle)
            x2 = cx + outer_r * math.cos(angle)
            y2 = cy + outer_r * math.sin(angle)

            intensity = h / max(amp, 1)
            if intensity > 0.75:
                col = bright
            elif intensity > 0.4:
                col = mid
            else:
                col = dim
            c.coords(self._freq_bars[i], x1, y1, x2, y2)
            c.itemconfig(self._freq_bars[i], fill=col)

        # ── Rotation ──────────────────────────────────────────────────────────
        self._rot1 += 0.008 * speed
        self._rot2 -= 0.005 * speed
        self._rot3 += 0.012 * speed

        # Outer arcs (6 evenly spaced, rotating)
        arc_r = r * 1.32
        for i, aid in enumerate(self._outer_arcs):
            base_angle = (360 / 6) * i + math.degrees(self._rot1)
            c.coords(aid, cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r)
            c.itemconfig(aid, start=base_angle, extent=22, outline=mid)

        # Inner counter-rotating short dashes
        inner_arc_r = r * 1.18
        for i, aid in enumerate(self._inner_arcs):
            base_angle = (360 / 12) * i + math.degrees(self._rot2)
            c.coords(aid, cx - inner_arc_r, cy - inner_arc_r, cx + inner_arc_r, cy + inner_arc_r)
            c.itemconfig(aid, start=base_angle, extent=5, outline=BLUE_RING)

        # ── Concentric static rings ───────────────────────────────────────────
        def oval(ox, oy, rad, item, **kw):
            c.coords(item, ox - rad, oy - rad, ox + rad, oy + rad)
            if kw:
                c.itemconfig(item, **kw)

        oval(cx, cy, r * 1.45, self._ring_d1)
        oval(cx, cy, r * 1.32, self._ring_d2)
        oval(cx, cy, r * 1.18, self._ring_d3)

        # Degree marks on outer ring
        deg_r = r * 1.52
        for i, dm in enumerate(self._deg_marks):
            ang = (2 * math.pi * i / 12) - math.pi / 2
            dx = cx + deg_r * math.cos(ang)
            dy = cy + deg_r * math.sin(ang)
            c.coords(dm, dx, dy)
            c.itemconfig(dm, text=f"{i*30:03d}°")

        # ── Core circles ──────────────────────────────────────────────────────
        core_mask_r = r * 0.68
        oval(cx, cy, core_mask_r, self._core_outer_mask)
        oval(cx, cy, core_mask_r * 0.90, self._core_glow3)
        oval(cx, cy, core_mask_r * 0.76, self._core_glow2)
        oval(cx, cy, core_mask_r * 0.60, self._core_glow1)

        pulse = 0.5 + 0.5 * math.sin(t * speed * 0.4)
        gold_r = core_mask_r * (0.30 + 0.04 * pulse)
        oval(cx, cy, gold_r, self._core_gold)
        oval(cx, cy, core_mask_r * 0.52, self._core_ring, outline=bright if self._status != 'idle' else CYAN_DIM)

        # ── Center text ───────────────────────────────────────────────────────
        name_font_size = max(14, int(r * 0.14))
        c.coords(self._txt_name, cx, cy - r * 0.08)
        c.itemconfig(self._txt_name, font=('Consolas', name_font_size, 'bold'), fill=bright)
        c.coords(self._txt_status, cx, cy + r * 0.10)
        c.itemconfig(self._txt_status, text=s['label'])
        c.coords(self._txt_sub, cx, cy + r * 0.20)
        c.itemconfig(self._txt_sub, text=s['status'])

        # ── Left panel ────────────────────────────────────────────────────────
        self._draw_left_panel(cx, cy, r, t)

        # ── Right panel ───────────────────────────────────────────────────────
        self._draw_right_panel(cx, cy, r)

        # ── Bottom dialogue panel ─────────────────────────────────────────────
        self._draw_dialogue_panel()

        # ── Oscilloscope ──────────────────────────────────────────────────────
        self._draw_oscilloscope(t)

        # ── Telemetry update (every 60 frames) ───────────────────────────────
        self._tel_tick += 1
        if self._tel_tick >= 60 and PSUTIL_AVAILABLE:
            self._tel_tick = 0
            self._cpu = psutil.cpu_percent(interval=None)
            self._ram = psutil.virtual_memory().percent

        # ── Clock update ──────────────────────────────────────────────────────
        now = datetime.now().strftime("%H:%M:%S")
        c.itemconfig(self._lp_time, text=f"TIME   : {now}")
        c.itemconfig(self._dp_time, text=now)

        # Schedule next frame
        self.root.after(1000 // FPS, self._animate)

    def _draw_hex_grid(self, cx, cy, r):
        """Draw a subtle hexagonal grid in the background (static, redrawn each frame for glow)."""
        c = self._canvas
        c.delete("hexgrid")
        # Only draw hexes within canvas bounds
        w, h = self._w, self._h
        hs = HEX_SIZE
        rows = int(h / (hs * 1.5)) + 2
        cols = int(w / (hs * math.sqrt(3))) + 2
        hex_w = hs * math.sqrt(3)

        for row in range(-1, rows):
            for col in range(-1, cols):
                hx = col * hex_w + (hex_w / 2 if row % 2 else 0)
                hy = row * hs * 1.5

                # Distance from center — fade outer hexes
                dist = math.hypot(hx - cx, hy - cy)
                max_dist = r * 2.2
                if dist > max_dist:
                    continue

                alpha_factor = max(0, 1 - dist / max_dist)
                # Colour based on distance: brighter near center
                if dist < r * 0.85:
                    col_hex = "#0A2030"
                elif dist < r * 1.3:
                    col_hex = "#061828"
                else:
                    col_hex = "#040F1A"

                pts = []
                for k in range(6):
                    ang = math.radians(60 * k + 30)
                    pts.extend([hx + hs * 0.95 * math.cos(ang), hy + hs * 0.95 * math.sin(ang)])

                c.create_polygon(*pts, outline=col_hex, fill='', tags="hexgrid", width=1)

        # Keep hex grid below everything else
        c.tag_lower("hexgrid")

    def _draw_left_panel(self, cx, cy, r, t):
        c = self._canvas
        pw = max(140, min(200, (cx - r * 1.55) * 0.9))
        px = 12
        py = max(55, int(cy - r * 0.9))
        ph = int(r * 1.8)

        # Border
        bpts = [(px, py, px + pw, py), (px, py, px, py + ph),
                (px + pw, py, px + pw, py + ph), (px, py + ph, px + pw, py + ph)]
        for i, (x1, y1, x2, y2) in enumerate(bpts):
            c.coords(self._lp_border[i], x1, y1, x2, y2)

        lx = px + 10
        line_h = 16

        c.coords(self._lp_title, lx, py + 10)
        c.coords(self._lp_cpu_l, lx, py + 10 + line_h * 2)
        c.coords(self._lp_cpu_v, lx + 52, py + 10 + line_h * 2)
        c.itemconfig(self._lp_cpu_v, text=f"{self._cpu:.0f}%")

        # CPU bar
        bx1, by1 = lx, py + 10 + line_h * 3
        bx2, by2 = px + pw - 10, by1 + 6
        c.coords(self._lp_cpu_bg, bx1, by1, bx2, by2)
        fill_w = bx1 + (bx2 - bx1) * self._cpu / 100
        c.coords(self._lp_cpu_fg, bx1, by1, fill_w, by2)

        c.coords(self._lp_ram_l, lx, py + 10 + line_h * 4)
        c.coords(self._lp_ram_v, lx + 52, py + 10 + line_h * 4)
        c.itemconfig(self._lp_ram_v, text=f"{self._ram:.0f}%")

        bx1, by1 = lx, py + 10 + line_h * 5
        bx2, by2 = px + pw - 10, by1 + 6
        c.coords(self._lp_ram_bg, bx1, by1, bx2, by2)
        fill_w = bx1 + (bx2 - bx1) * self._ram / 100
        c.coords(self._lp_ram_fg, bx1, by1, fill_w, by2)

        c.coords(self._lp_audio, lx, py + 10 + line_h * 6)
        c.coords(self._lp_link,  lx, py + 10 + line_h * 7)
        c.coords(self._lp_time,  lx, py + 10 + line_h * 8)

    def _draw_right_panel(self, cx, cy, r):
        c = self._canvas
        pw = max(140, min(200, (self._w - cx - r * 1.55) * 0.9))
        px = self._w - 12 - pw
        py = max(55, int(cy - r * 0.9))
        ph = int(r * 1.8)

        bpts = [(px, py, px + pw, py), (px, py, px, py + ph),
                (px + pw, py, px + pw, py + ph), (px, py + ph, px + pw, py + ph)]
        for i, (x1, y1, x2, y2) in enumerate(bpts):
            c.coords(self._rp_border[i], x1, y1, x2, y2)

        rx = self._w - 22
        line_h = 15
        c.coords(self._rp_title, rx, py + 10)
        c.coords(self._rp_model, rx, py + 10 + line_h * 2)
        c.coords(self._rp_voice, rx, py + 10 + line_h * 3)
        c.coords(self._rp_stt,   rx, py + 10 + line_h * 4)
        c.coords(self._rp_lat,   rx, py + 10 + line_h * 5)
        c.coords(self._rp_sec,   rx, py + 10 + line_h * 6)

    def _draw_dialogue_panel(self):
        c = self._canvas
        margin = 12
        px = margin
        pw = self._w - margin * 2
        ph = 70
        py = self._h - ph - 4

        c.coords(self._dp_bg, px, py, px + pw, py + ph)
        c.coords(self._dp_divider, px, py, px + pw, py)
        c.coords(self._dp_src,  px + 12, py + 10)
        c.itemconfig(self._dp_src, text=f"● {self._last_source}")
        c.coords(self._dp_time, px + pw - 12, py + 10)
        c.coords(self._dp_text, px + 12, py + 28)
        c.itemconfig(self._dp_text, text=self._last_text, width=pw - 24)

    def _draw_oscilloscope(self, t):
        c = self._canvas
        s = STATE[self._status]
        pts1, pts2 = [], []
        npts = 60
        oy = self._h - 78
        for i in range(npts):
            x = self._w * i / (npts - 1)
            amp1 = s['amp'] * 0.15
            amp2 = s['amp'] * 0.08
            y1 = oy + amp1 * math.sin(t * s['speed'] * 0.5 + i * 0.25)
            y2 = oy + amp2 * math.sin(t * s['speed'] * 0.3 + i * 0.18 + 1.2)
            pts1.extend([x, y1])
            pts2.extend([x, y2])
        if len(pts1) >= 4:
            c.coords(self._osc1, *pts1)
            c.coords(self._osc2, *pts2)
        c.itemconfig(self._osc1, fill=s['mid'])
        c.itemconfig(self._osc2, fill=s['dim'])

    # ─────────────────────────────────────────────────────────────────────────
    # Public API (called from main.py)
    # ─────────────────────────────────────────────────────────────────────────

    def set_status(self, status: str):
        if status in STATE:
            self._status = status
            # Flash colour on activate button
            if status == 'listening':
                self._activate_btn.configure(fg='#00FF99', text="● LISTENING — SPEAK NOW...")
            elif status == 'thinking':
                self._activate_btn.configure(fg=GOLD, text="◎ PROCESSING NEURAL QUERY...")
            elif status == 'speaking':
                self._activate_btn.configure(fg=CYAN_BRIGHT, text="▶ AUDIO OUTPUT ACTIVE...")
            else:
                hk = self.config.get('hotkey', 'P').upper()
                self._activate_btn.configure(fg=CYAN_BRIGHT, text=f"◉   ACTIVATE VOICE INTERFACE   [ {hk} ]")

    def add_aria_message(self, text: str):
        self._last_source = "ARIA"
        self._last_text = text.upper() if len(text) < 80 else text
        self._canvas.itemconfig(self._dp_src, fill=CYAN_BRIGHT)

    def add_user_message(self, text: str):
        self._last_source = "MADHAV"
        self._last_text = text
        self._canvas.itemconfig(self._dp_src, fill=GOLD)

    def add_system_message(self, text: str):
        self._last_source = "SYSTEM"
        self._last_text = text
        self._canvas.itemconfig(self._dp_src, fill=TEXT_MID)

    def bring_to_front(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.focus_force()

    def toggle_visibility(self):
        if self.root.state() == 'iconic':
            self.root.deiconify()
            self.root.lift()
            self.root.attributes('-topmost', True)
        else:
            self.root.iconify()

    def run(self):
        self.root.mainloop()

    # ─────────────────────────────────────────────────────────────────────────
    # Internal Callbacks
    # ─────────────────────────────────────────────────────────────────────────

    def _on_mic_click(self):
        if self.on_listen_request:
            threading.Thread(target=self.on_listen_request, daemon=True).start()

    def _on_close(self):
        self._anim_running = False
        self.root.destroy()

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.root.attributes('-fullscreen', self._fullscreen)

    def _exit_fullscreen(self):
        self._fullscreen = False
        self.root.attributes('-fullscreen', False)

    def _toggle_topmost(self):
        cur = self.root.attributes('-topmost')
        self.root.attributes('-topmost', not cur)

    def _reset_memory(self):
        if self.on_reset_memory:
            self.on_reset_memory()
        self.add_system_message("Conversation memory cleared — session reset.")

    # ─────────────────────────────────────────────────────────────────────────
    # Settings Modal
    # ─────────────────────────────────────────────────────────────────────────

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("ARIA — SYSTEM CONFIGURATION")
        win.configure(bg=BG)
        win.geometry("520x700")
        win.resizable(False, True)
        win.grab_set()

        # Header
        tk.Label(win, text="◈  SYSTEM CONFIGURATION CONSOLE",
                 bg=BG, fg=CYAN_BRIGHT, font=('Consolas', 11, 'bold')).pack(pady=(14, 2))
        tk.Frame(win, bg=PANEL_EDGE, height=1).pack(fill='x', padx=16)

        # Scrollable content
        outer = tk.Frame(win, bg=BG)
        outer.pack(fill='both', expand=True, padx=16, pady=8)
        canvas_s = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient='vertical', command=canvas_s.yview, bg=BG)
        scroll_frame = tk.Frame(canvas_s, bg=BG)
        scroll_frame.bind("<Configure>", lambda e: canvas_s.configure(scrollregion=canvas_s.bbox("all")))
        canvas_s.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas_s.configure(yscrollcommand=scrollbar.set)
        canvas_s.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        canvas_s.bind("<MouseWheel>", lambda e: canvas_s.yview_scroll(-1 * (e.delta // 120), "units"))

        def section_title(text):
            tk.Frame(scroll_frame, bg=PANEL_EDGE, height=1).pack(fill='x', pady=(12, 4))
            tk.Label(scroll_frame, text=f"◈  {text}", bg=BG, fg=CYAN_MID,
                     font=('Consolas', 8, 'bold')).pack(anchor='w')

        def field(label, var, note="", show=None):
            f = tk.Frame(scroll_frame, bg=BG)
            f.pack(fill='x', pady=3)
            tk.Label(f, text=label, bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')
            e = tk.Entry(f, textvariable=var, bg='#030C1A', fg=CYAN_BRIGHT, insertbackground=CYAN_BRIGHT,
                         relief='flat', bd=0, font=('Consolas', 9), highlightthickness=1,
                         highlightbackground=CYAN_DIM, highlightcolor=CYAN_BRIGHT,
                         show=show or '')
            e.pack(fill='x', ipady=5)
            if note:
                tk.Label(f, text=note, bg=BG, fg=TEXT_DIM, font=('Consolas', 7), wraplength=460).pack(anchor='w')
            return e

        # Variables
        user_var   = tk.StringVar(value=self.config.get('user_name', 'Madhav'))
        api_var    = tk.StringVar(value=self.config.get('gemini_api_key', ''))
        hk_var     = tk.StringVar(value=self.config.get('hotkey', 'P'))
        summon_var = tk.StringVar(value=self.config.get('summon_hotkey', 'ctrl+space'))
        city_var   = tk.StringVar(value=self.config.get('weather_city', ''))
        speed_var  = tk.IntVar(value=self.config.get('voice_speed', 175))
        voice_var  = tk.StringVar(value=self.config.get('voice_name', 'en-GB-RyanNeural'))
        lang_var   = tk.StringVar(value=self.config.get('stt_language', 'en-IN'))

        section_title("OPERATOR PROFILE")
        field("OPERATOR NAME", user_var, "Your name for personalized greetings.")

        section_title("GEMINI NEURAL AI CORE")
        field("GEMINI API KEY", api_var, "Free key from aistudio.google.com/apikey", show='*')

        section_title("NEURAL VOICE MATRIX")
        vf = tk.Frame(scroll_frame, bg=BG)
        vf.pack(fill='x', pady=3)
        tk.Label(vf, text="VOICE PROFILE", bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')
        voice_opts = ["en-GB-RyanNeural", "en-US-GuyNeural", "en-US-ChristopherNeural",
                      "en-US-BrianNeural", "en-US-EricNeural"]
        vm = tk.OptionMenu(vf, voice_var, *voice_opts)
        vm.config(bg='#030C1A', fg=CYAN_BRIGHT, activebackground='#061628',
                  activeforeground=CYAN_BRIGHT, relief='flat', highlightthickness=0,
                  font=('Consolas', 9), cursor='hand2')
        vm["menu"].config(bg='#030C1A', fg=CYAN_BRIGHT, font=('Consolas', 9))
        vm.pack(fill='x', pady=2)

        def _test_voice():
            name = user_var.get().strip() or "Madhav"
            v = voice_var.get()
            txt = f"Hey {name}! ARIA online — all neural systems nominal and ready."
            def _play():
                try:
                    import tempfile as tf
                    with tf.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                        tmp = fp.name
                    async def _gen():
                        await edge_tts.Communicate(txt, voice=v).save(tmp)
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(_gen())
                    loop.close()
                    pygame.mixer.music.load(tmp)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                    pygame.mixer.music.unload()
                    os.remove(tmp)
                except Exception as ex:
                    print(f"[Settings] Voice test error: {ex}")
            threading.Thread(target=_play, daemon=True).start()

        tk.Button(vf, text="🔊  PREVIEW VOICE", command=_test_voice,
                  bg='#002030', fg=CYAN_BRIGHT, activebackground='#003040',
                  relief='flat', bd=0, font=('Consolas', 8, 'bold'), cursor='hand2', pady=5
                  ).pack(anchor='w', pady=(4, 0))

        sf = tk.Frame(scroll_frame, bg=BG)
        sf.pack(fill='x', pady=4)
        tk.Label(sf, text="SPEECH RATE", bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')
        row = tk.Frame(sf, bg=BG)
        row.pack(fill='x')
        tk.Scale(row, variable=speed_var, from_=110, to=240, orient='horizontal',
                 bg=BG, fg=CYAN_BRIGHT, troughcolor='#001828', highlightthickness=0,
                 font=('Consolas', 8), length=340).pack(side='left')
        tk.Label(row, textvariable=speed_var, bg=BG, fg=CYAN_MID, font=('Consolas', 9), width=4).pack(side='left')

        section_title("SPEECH RECOGNITION")
        lf = tk.Frame(scroll_frame, bg=BG)
        lf.pack(fill='x', pady=3)
        tk.Label(lf, text="MICROPHONE LANGUAGE", bg=BG, fg=TEXT_MID, font=('Consolas', 8, 'bold')).pack(anchor='w')
        lang_opts = ["en-IN", "en-US", "en-GB"]
        lm = tk.OptionMenu(lf, lang_var, *lang_opts)
        lm.config(bg='#030C1A', fg=CYAN_BRIGHT, activebackground='#061628',
                  activeforeground=CYAN_BRIGHT, relief='flat', highlightthickness=0,
                  font=('Consolas', 9), cursor='hand2')
        lm["menu"].config(bg='#030C1A', fg=CYAN_BRIGHT, font=('Consolas', 9))
        lm.pack(fill='x', pady=2)

        section_title("HOTKEYS & REGION")
        field("VOICE ACTIVATION HOTKEY", hk_var, "Key to start listening (e.g. P, F2)")
        field("SUMMON WINDOW SHORTCUT", summon_var, "Global toggle shortcut (e.g. ctrl+space)")
        field("WEATHER CITY", city_var, "City for weather queries (e.g. Delhi, Mumbai)")

        # Save button
        tk.Frame(win, bg=PANEL_EDGE, height=1).pack(fill='x', padx=16)
        btn_frame = tk.Frame(win, bg=BG)
        btn_frame.pack(fill='x', padx=16, pady=12)

        def _save():
            self.config['user_name']      = user_var.get().strip() or 'Madhav'
            self.config['gemini_api_key'] = api_var.get().strip()
            self.config['hotkey']         = hk_var.get().strip() or 'P'
            self.config['summon_hotkey']  = summon_var.get().strip() or 'ctrl+space'
            self.config['stt_language']   = lang_var.get().strip() or 'en-IN'
            self.config['weather_city']   = city_var.get().strip()
            self.config['voice_name']     = voice_var.get().strip() or 'en-GB-RyanNeural'
            self.config['voice_speed']    = speed_var.get()

            self._hdr_user.configure(text=f"OPERATOR: {self.config['user_name'].upper()}  ·  NEURAL CORE: ONLINE")
            hk = self.config['hotkey'].upper()
            self._activate_btn.configure(text=f"◉   ACTIVATE VOICE INTERFACE   [ {hk} ]")

            if self.on_api_key_save:
                self.on_api_key_save(self.config)
            win.destroy()
            self.add_system_message("Configuration synchronized — all parameters updated.")

        tk.Button(btn_frame, text="▶  SAVE & SYNCHRONIZE",
                  command=_save, bg='#001828', fg=CYAN_BRIGHT,
                  activebackground='#002840', activeforeground='#FFFFFF',
                  relief='flat', bd=0, font=('Consolas', 10, 'bold'),
                  cursor='hand2', pady=8).pack(fill='x')
