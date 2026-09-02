"""
ARIA — Enhanced JARVIS Holographic Interface v2
Major visual upgrades:
  - Radar sweep scanner line on outer ring
  - Radiating pulse rings (heartbeat effect)
  - Inner geometric hexagon / triangle inside reactor core
  - Animated data stream ticker on side panels
  - Sharper panel design with multi-line corner brackets
  - Dashed separator rings between arcs
  - Status-coloured glow bloom on core
  - Improved typography & spacing
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

# ── Colour palette ─────────────────────────────────────────────────────────────
BG          = "#010509"
PANEL_BG    = "#020B14"
PANEL_EDGE  = "#0B2D45"
CYAN_BRIGHT = "#00EEFF"
CYAN_MID    = "#00AACC"
CYAN_DIM    = "#005577"
CYAN_GRID   = "#031420"
BLUE_ARC    = "#1155BB"
GOLD        = "#FFB800"
GOLD_DIM    = "#5A4000"
TEXT_HI     = "#D0F5FF"
TEXT_MID    = "#4D9FBB"
TEXT_DIM    = "#163850"
ALERT       = "#FF2244"
GREEN_LIT   = "#00FF88"

# ── State configs ──────────────────────────────────────────────────────────────
STATE = {
    'idle': {
        'bright': '#00CCEE', 'mid': '#006688', 'dim': '#001E2C',
        'label': 'STANDBY', 'amp': 5, 'speed': 0.9,
        'status': 'AWAITING COMMAND INPUT',
        'core_fill': '#001018', 'sweep': '#003344',
    },
    'listening': {
        'bright': '#00FF88', 'mid': '#00CC66', 'dim': '#003822',
        'label': 'LISTENING', 'amp': 60, 'speed': 7.5,
        'status': 'VOICE ACQUISITION · ACTIVE',
        'core_fill': '#001A10', 'sweep': '#004422',
    },
    'thinking': {
        'bright': '#FFB800', 'mid': '#CC8800', 'dim': '#3A2A00',
        'label': 'PROCESSING', 'amp': 32, 'speed': 3.8,
        'status': 'NEURAL SYNTHESIS · IN PROGRESS',
        'core_fill': '#120C00', 'sweep': '#221800',
    },
    'speaking': {
        'bright': '#00EEFF', 'mid': '#0099BB', 'dim': '#002A3A',
        'label': 'TRANSMITTING', 'amp': 70, 'speed': 9.5,
        'status': 'AUDIO MATRIX · OUTPUT ACTIVE',
        'core_fill': '#001520', 'sweep': '#002838',
    },
    'error': {
        'bright': '#FF2244', 'mid': '#AA1530', 'dim': '#2A0810',
        'label': 'FAULT', 'amp': 18, 'speed': 3.0,
        'status': 'SYSTEM EXCEPTION · TELEMETRY FAULT',
        'core_fill': '#110005', 'sweep': '#220510',
    },
}

NUM_BARS = 120
FPS      = 42
HEX_R    = 30


class AppWindow:

    def __init__(self, config, on_listen_request=None, on_api_key_save=None, on_reset_memory=None):
        self.config = config
        self.on_listen_request  = on_listen_request
        self.on_api_key_save    = on_api_key_save
        self.on_reset_memory    = on_reset_memory

        # geometry
        self._w = 920
        self._h = 680
        self._cx = self._w / 2
        self._cy = self._h * 0.43
        self._base_r = 145
        self._fullscreen = False

        # animation state
        self._status  = 'idle'
        self._running = True
        self._rot1    = 0.0   # outer arcs CW
        self._rot2    = 0.0   # inner ring CCW
        self._sweep   = 0.0   # radar sweep angle
        self._pulse_r = []    # list of (radius, alpha) for pulse rings
        self._bar_v   = [0.0] * NUM_BARS
        self._phases  = [random.uniform(0, 2*math.pi) for _ in range(NUM_BARS)]
        self._osc_t   = 0.0
        self._ticker  = 0     # frame counter for telemetry update

        # hardware
        self._cpu = 0.0
        self._ram = 0.0

        # data stream (side panel scrolling hex numbers)
        self._stream_l = [f"{random.randint(0,0xFFFF):04X}" for _ in range(20)]
        self._stream_r = [f"{random.randint(0,0xFFFF):04X}" for _ in range(20)]
        self._stream_tick = 0

        # dialogue
        self._diag_text   = "ALL SYSTEMS NOMINAL — READY FOR INTERACTION"
        self._diag_source = "SYSTEM"

        # root window
        self.root = tk.Tk()
        self.root.title("A.R.I.A.  ·  STARK INDUSTRIES")
        self.root.geometry(f"{self._w}x{self._h}")
        self.root.minsize(720, 540)
        self.root.configure(bg=BG)
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<F11>",  lambda e: self._toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self._exit_fullscreen())

        self._build_ui()
        self._animate()

    # ── UI BUILD ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._canvas = tk.Canvas(self.root, bg=BG, bd=0, highlightthickness=0)
        self._canvas.pack(fill='both', expand=True)
        self._canvas.bind("<Configure>", self._on_resize)
        self._init_items()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG, height=46)
        hdr.pack(fill='x')
        hdr.pack_propagate(False)

        lf = tk.Frame(hdr, bg=BG)
        lf.pack(side='left', padx=16, fill='y')

        tk.Label(lf, text="◈  STARK INDUSTRIES  ·  A.R.I.A. SYSTEM  v4.2",
                 bg=BG, fg=CYAN_BRIGHT, font=('Consolas', 10, 'bold')).pack(anchor='w', pady=(8, 0))
        user = self.config.get('user_name', 'MADHAV').upper()
        self._hdr_user = tk.Label(
            lf, text=f"OPERATOR : {user}   ·   NEURAL CORE : ONLINE   ·   WHISPER STT : ACTIVE",
            bg=BG, fg=TEXT_DIM, font=('Consolas', 7)
        )
        self._hdr_user.pack(anchor='w')

        rf = tk.Frame(hdr, bg=BG)
        rf.pack(side='right', padx=10, fill='y')
        for icon, cmd in [("⛶", self._toggle_fullscreen), ("⟳", self._reset_memory),
                           ("📌", self._toggle_topmost), ("⚙", self._open_settings)]:
            tk.Button(rf, text=icon, command=cmd,
                      bg='#020C18', fg=CYAN_MID,
                      activebackground='#041C30', activeforeground=CYAN_BRIGHT,
                      relief='flat', bd=0, font=('Consolas', 12), width=3, cursor='hand2'
                      ).pack(side='right', padx=2, pady=10)

        tk.Frame(self.root, bg=PANEL_EDGE, height=1).pack(fill='x')

    def _build_footer(self):
        foot = tk.Frame(self.root, bg=PANEL_BG, height=52)
        foot.pack(fill='x', side='bottom')
        foot.pack_propagate(False)
        tk.Frame(foot, bg=PANEL_EDGE, height=1).pack(fill='x')

        row = tk.Frame(foot, bg=PANEL_BG)
        row.pack(fill='both', expand=True, padx=16, pady=0)

        hk = self.config.get('hotkey', 'P').upper()
        self._activate_btn = tk.Button(
            row,
            text=f"◉   ACTIVATE VOICE INTERFACE   [ {hk} ]",
            command=self._on_mic_click,
            bg=PANEL_BG, fg=CYAN_BRIGHT,
            activebackground='#031C2C', activeforeground='#FFFFFF',
            relief='flat', bd=0, font=('Consolas', 11, 'bold'), cursor='hand2'
        )
        self._activate_btn.pack(fill='both', expand=True)

    # ── CANVAS ITEMS ────────────────────────────────────────────────────────────

    def _init_items(self):
        c = self._canvas

        # ── Scan rings (static circles) ───────────────────────────────────────
        self._r_outer3 = c.create_oval(0,0,1,1, outline='#001525', width=1)
        self._r_outer2 = c.create_oval(0,0,1,1, outline='#001E33', width=1)
        self._r_outer1 = c.create_oval(0,0,1,1, outline='#002840', width=1)
        self._r_mid    = c.create_oval(0,0,1,1, outline=PANEL_EDGE,  width=1)
        self._r_core   = c.create_oval(0,0,1,1, outline=CYAN_DIM,    width=1)

        # Degree marks around outer ring
        self._deg_marks = [c.create_text(0,0, text="000°", fill=TEXT_DIM, font=('Consolas',6,'bold')) for _ in range(12)]

        # ── Rotating arcs ─────────────────────────────────────────────────────
        self._arcs_outer = [c.create_arc(0,0,1,1, start=0, extent=18, outline=CYAN_DIM,  style='arc', width=2) for _ in range(8)]
        self._arcs_inner = [c.create_arc(0,0,1,1, start=0, extent=6,  outline=BLUE_ARC, style='arc', width=1) for _ in range(16)]

        # ── Radar sweep ───────────────────────────────────────────────────────
        self._sweep_line = c.create_line(0,0,1,1, fill=GREEN_LIT, width=2)
        self._sweep_fade = [c.create_arc(0,0,1,1, start=0, extent=1, outline='#002010', style='arc', width=2) for _ in range(18)]

        # ── Pulse rings (radiating outward) ───────────────────────────────────
        self._pulse_rings = [c.create_oval(0,0,1,1, outline='#001520', width=1) for _ in range(4)]
        self._pulse_radii = [0.0, 0.25, 0.5, 0.75]   # phase offsets

        # ── Frequency bars ────────────────────────────────────────────────────
        self._freq_bars = [c.create_line(0,0,1,1, fill=CYAN_DIM, width=2, capstyle='round') for _ in range(NUM_BARS)]

        # ── Core mask & glow layers ───────────────────────────────────────────
        self._core_mask   = c.create_oval(0,0,1,1, fill=BG,     outline=PANEL_EDGE, width=2)
        self._core_glow3  = c.create_oval(0,0,1,1, fill='#000C14', outline='#001524', width=1)
        self._core_glow2  = c.create_oval(0,0,1,1, fill='#001018', outline='#002030', width=1)
        self._core_glow1  = c.create_oval(0,0,1,1, fill='#001520', outline='#00304A', width=2)

        # Hexagon inside core
        self._core_hex    = [c.create_line(0,0,1,1, fill=CYAN_DIM, width=1) for _ in range(6)]
        # Triangle inside core
        self._core_tri    = [c.create_line(0,0,1,1, fill=GOLD_DIM, width=1) for _ in range(3)]
        # Inner dot
        self._core_dot    = c.create_oval(0,0,1,1, fill=CYAN_DIM, outline='')

        # Gold accent ring & cyan ring
        self._core_gold   = c.create_oval(0,0,1,1, outline=GOLD_DIM, width=1)
        self._core_ring2  = c.create_oval(0,0,1,1, outline=CYAN_DIM, width=2)

        # ── Center text ───────────────────────────────────────────────────────
        self._txt_aria    = c.create_text(0,0, text="A·R·I·A", fill=CYAN_BRIGHT, font=('Consolas',22,'bold'))
        self._txt_label   = c.create_text(0,0, text="STANDBY", fill=CYAN_MID,    font=('Consolas',8,'bold'))
        self._txt_status  = c.create_text(0,0, text="AWAITING COMMAND INPUT", fill=TEXT_DIM, font=('Consolas',7))

        # ── LEFT PANEL ────────────────────────────────────────────────────────
        # Borders (4 sides)
        self._lp_b = [c.create_line(0,0,1,1, fill=PANEL_EDGE, width=1) for _ in range(4)]
        # Corner accents (extra ticks at corners)
        self._lp_c = [c.create_line(0,0,1,1, fill=CYAN_DIM, width=2) for _ in range(8)]

        self._lp_title = c.create_text(0,0, text="◈ SYSTEM TELEMETRY", fill=CYAN_MID, font=('Consolas',8,'bold'), anchor='w')
        self._lp_cpu_l = c.create_text(0,0, text="CPU :", fill=TEXT_MID, font=('Consolas',8), anchor='w')
        self._lp_cpu_v = c.create_text(0,0, text="0%",   fill=CYAN_BRIGHT, font=('Consolas',8,'bold'), anchor='w')
        self._lp_ram_l = c.create_text(0,0, text="RAM :", fill=TEXT_MID, font=('Consolas',8), anchor='w')
        self._lp_ram_v = c.create_text(0,0, text="0%",   fill=CYAN_MID, font=('Consolas',8,'bold'), anchor='w')
        self._lp_cpu_bg = c.create_rectangle(0,0,1,1, fill='#001520', outline=PANEL_EDGE)
        self._lp_cpu_fg = c.create_rectangle(0,0,1,1, fill=CYAN_BRIGHT, outline='')
        self._lp_ram_bg = c.create_rectangle(0,0,1,1, fill='#001520', outline=PANEL_EDGE)
        self._lp_ram_fg = c.create_rectangle(0,0,1,1, fill=CYAN_MID, outline='')
        self._lp_extra  = [c.create_text(0,0, text="", fill=TEXT_DIM, font=('Consolas',7), anchor='w') for _ in range(6)]
        # Data stream
        self._lp_stream = [c.create_text(0,0, text="----", fill=TEXT_DIM, font=('Courier',7), anchor='w') for _ in range(8)]

        # ── RIGHT PANEL ───────────────────────────────────────────────────────
        self._rp_b = [c.create_line(0,0,1,1, fill=PANEL_EDGE, width=1) for _ in range(4)]
        self._rp_c = [c.create_line(0,0,1,1, fill=CYAN_DIM, width=2) for _ in range(8)]

        self._rp_title  = c.create_text(0,0, text="NEURAL DIAGNOSTICS ◈", fill=CYAN_MID, font=('Consolas',8,'bold'), anchor='e')
        self._rp_lines  = [c.create_text(0,0, text="", fill=TEXT_MID, font=('Consolas',7), anchor='e') for _ in range(6)]
        self._rp_stream = [c.create_text(0,0, text="----", fill=TEXT_DIM, font=('Courier',7), anchor='e') for _ in range(8)]

        # ── BOTTOM DIALOGUE PANEL ─────────────────────────────────────────────
        self._dp_bg   = c.create_rectangle(0,0,1,1, fill=PANEL_BG, outline=PANEL_EDGE, width=1)
        self._dp_div  = c.create_line(0,0,1,1, fill=PANEL_EDGE, width=1)
        self._dp_src  = c.create_text(0,0, text="● SYSTEM", fill=TEXT_MID, font=('Consolas',8,'bold'), anchor='w')
        self._dp_clk  = c.create_text(0,0, text="--:--:--", fill=TEXT_DIM, font=('Consolas',7), anchor='e')
        self._dp_txt  = c.create_text(0,0, text=self._diag_text, fill=TEXT_HI, font=('Consolas',9), anchor='w', width=600)

        # ── Corner brackets (4 corners, 2 lines each) ─────────────────────────
        self._corners = [c.create_line(0,0,1,1, fill=CYAN_DIM, width=2) for _ in range(8)]

        # ── Oscilloscope ─────────────────────────────────────────────────────
        self._osc1 = c.create_line([0,0,1,1], fill='#002A3A', width=1, smooth=True)
        self._osc2 = c.create_line([0,0,1,1], fill='#001A28', width=1, smooth=True)

    # ── RESIZE ──────────────────────────────────────────────────────────────────

    def _on_resize(self, event):
        if event.width < 50 or event.height < 50:
            return
        self._w = event.width
        self._h = event.height
        self._cx = self._w / 2
        self._cy = self._h * 0.44
        self._base_r = max(95, min(self._w * 0.21, self._h * 0.30))
        self._canvas.itemconfig(self._dp_txt, width=max(300, self._w - 80))
        self._update_corners()

    def _update_corners(self):
        s, w, h = 22, self._w, self._h
        pts = [
            (8,8, 8+s,8), (8,8, 8,8+s),
            (w-8,8, w-8-s,8), (w-8,8, w-8,8+s),
            (8,h-8, 8+s,h-8), (8,h-8, 8,h-8-s),
            (w-8,h-8, w-8-s,h-8), (w-8,h-8, w-8,h-8-s),
        ]
        for i, (x1,y1,x2,y2) in enumerate(pts):
            self._canvas.coords(self._corners[i], x1,y1,x2,y2)

    # ── ANIMATION ───────────────────────────────────────────────────────────────

    def _animate(self):
        if not self._running:
            return

        t  = time.time()
        s  = STATE[self._status]
        cx, cy, r = self._cx, self._cy, self._base_r
        c  = self._canvas
        bright = s['bright']
        mid    = s['mid']
        dim    = s['dim']
        amp    = s['amp']
        spd    = s['speed']

        # ── Hex grid ──────────────────────────────────────────────────────────
        self._draw_hex_grid(cx, cy, r)

        # ── Pulse rings ───────────────────────────────────────────────────────
        pulse_speed = spd * 0.06
        for i, pr in enumerate(self._pulse_rings):
            self._pulse_radii[i] = (self._pulse_radii[i] + pulse_speed) % 1.0
            fr = self._pulse_radii[i]
            pr_radius = r * (1.0 + fr * 0.8)
            fade_col = self._lerp_colour(mid, BG, fr)
            c.coords(pr, cx-pr_radius, cy-pr_radius, cx+pr_radius, cy+pr_radius)
            c.itemconfig(pr, outline=fade_col)

        # ── Static rings ──────────────────────────────────────────────────────
        def oval(item, rad, **kw):
            c.coords(item, cx-rad, cy-rad, cx+rad, cy+rad)
            if kw: c.itemconfig(item, **kw)

        oval(self._r_outer3, r * 1.60)
        oval(self._r_outer2, r * 1.45)
        oval(self._r_outer1, r * 1.30)
        oval(self._r_mid,    r * 1.15)
        oval(self._r_core,   r * 1.00)

        # ── Degree marks ──────────────────────────────────────────────────────
        dr = r * 1.68
        for i, dm in enumerate(self._deg_marks):
            a = (2*math.pi*i/12) - math.pi/2
            c.coords(dm, cx + dr*math.cos(a), cy + dr*math.sin(a))
            c.itemconfig(dm, text=f"{i*30:03d}°")

        # ── Rotating outer arcs ───────────────────────────────────────────────
        self._rot1 += 0.007 * spd
        ar = r * 1.44
        for i, a in enumerate(self._arcs_outer):
            base = math.degrees(self._rot1) + (360/8)*i
            c.coords(a, cx-ar, cy-ar, cx+ar, cy+ar)
            c.itemconfig(a, start=base, extent=20, outline=mid)

        # Inner counter-rotating
        self._rot2 -= 0.009 * spd
        ir = r * 1.14
        for i, a in enumerate(self._arcs_inner):
            base = math.degrees(self._rot2) + (360/16)*i
            c.coords(a, cx-ir, cy-ir, cx+ir, cy+ir)
            c.itemconfig(a, start=base, extent=5, outline=BLUE_ARC)

        # ── Radar sweep ───────────────────────────────────────────────────────
        self._sweep = (self._sweep + 0.04 * spd) % (2*math.pi)
        sweep_r = r * 1.29
        sx = cx + sweep_r * math.cos(self._sweep)
        sy = cy + sweep_r * math.sin(self._sweep)
        c.coords(self._sweep_line, cx, cy, sx, sy)
        c.itemconfig(self._sweep_line, fill=bright if self._status != 'idle' else CYAN_DIM)

        # Sweep fade trail (ghost arcs behind sweep)
        trail_r = r * 1.28
        for i, fa in enumerate(self._sweep_fade):
            offset = -(i+1) * 5
            fade = max(0, 1.0 - i/len(self._sweep_fade))
            fade_c = self._lerp_colour(mid, BG, 1.0 - fade * 0.6)
            c.coords(fa, cx-trail_r, cy-trail_r, cx+trail_r, cy+trail_r)
            c.itemconfig(fa, start=math.degrees(self._sweep)+offset, extent=5, outline=fade_c)

        # ── Frequency bars ────────────────────────────────────────────────────
        for i, bar in enumerate(self._freq_bars):
            ang = (2*math.pi*i/NUM_BARS) - math.pi/2
            target = amp * (0.3 + 0.7 * abs(math.sin(t*spd*0.65 + self._phases[i])))
            self._bar_v[i] += (target - self._bar_v[i]) * 0.20
            h = self._bar_v[i]
            x1 = cx + r * math.cos(ang)
            y1 = cy + r * math.sin(ang)
            x2 = cx + (r + h) * math.cos(ang)
            y2 = cy + (r + h) * math.sin(ang)
            intensity = h / max(amp, 1)
            col = bright if intensity > 0.72 else mid if intensity > 0.38 else dim
            c.coords(bar, x1,y1, x2,y2)
            c.itemconfig(bar, fill=col)

        # ── Core layers ───────────────────────────────────────────────────────
        cmr = r * 0.70
        oval(self._core_mask,  cmr,  fill=BG, outline=mid)
        oval(self._core_glow3, cmr * 0.93, fill=s['core_fill'])
        oval(self._core_glow2, cmr * 0.78, fill=self._shift_colour(s['core_fill'], 8))
        oval(self._core_glow1, cmr * 0.61, fill=self._shift_colour(s['core_fill'], 16))

        # ── Inner hex ─────────────────────────────────────────────────────────
        hex_r = cmr * 0.42
        for i, hl in enumerate(self._core_hex):
            a1 = (2*math.pi*i/6)     + self._rot1 * 0.3
            a2 = (2*math.pi*(i+1)/6) + self._rot1 * 0.3
            c.coords(hl,
                     cx + hex_r*math.cos(a1), cy + hex_r*math.sin(a1),
                     cx + hex_r*math.cos(a2), cy + hex_r*math.sin(a2))
            c.itemconfig(hl, fill=mid if self._status != 'idle' else CYAN_DIM)

        # ── Inner triangle ────────────────────────────────────────────────────
        tri_r = cmr * 0.28
        for i, tl in enumerate(self._core_tri):
            a1 = (2*math.pi*i/3)     - self._rot2 * 0.4
            a2 = (2*math.pi*(i+1)/3) - self._rot2 * 0.4
            c.coords(tl,
                     cx + tri_r*math.cos(a1), cy + tri_r*math.sin(a1),
                     cx + tri_r*math.cos(a2), cy + tri_r*math.sin(a2))
            c.itemconfig(tl, fill=GOLD_DIM if self._status == 'idle' else GOLD)

        # Core dot
        pulse = 0.5 + 0.5 * math.sin(t * spd * 0.6)
        dot_r = cmr * (0.08 + 0.04 * pulse)
        c.coords(self._core_dot, cx-dot_r, cy-dot_r, cx+dot_r, cy+dot_r)
        c.itemconfig(self._core_dot, fill=bright)

        oval(self._core_gold,  cmr * 0.52, outline=GOLD_DIM)
        oval(self._core_ring2, cmr * 0.60, outline=bright if self._status != 'idle' else CYAN_DIM)

        # ── Center text ───────────────────────────────────────────────────────
        fsize = max(14, int(r * 0.145))
        c.coords(self._txt_aria,   cx, cy - r * 0.06)
        c.itemconfig(self._txt_aria, font=('Consolas', fsize, 'bold'), fill=bright)
        c.coords(self._txt_label,  cx, cy + r * 0.11)
        c.itemconfig(self._txt_label, text=s['label'], fill=mid)
        c.coords(self._txt_status, cx, cy + r * 0.22)
        c.itemconfig(self._txt_status, text=s['status'], fill=TEXT_DIM)

        # ── Left panel ────────────────────────────────────────────────────────
        self._draw_left_panel(cx, cy, r)

        # ── Right panel ───────────────────────────────────────────────────────
        self._draw_right_panel(cx, cy, r)

        # ── Bottom dialogue ───────────────────────────────────────────────────
        self._draw_dialogue(t)

        # ── Oscilloscope ──────────────────────────────────────────────────────
        self._draw_osc(t, spd, mid, dim)

        # ── Clock & telemetry ─────────────────────────────────────────────────
        self._ticker += 1
        if self._ticker % 55 == 0:
            if PSUTIL_AVAILABLE:
                self._cpu = psutil.cpu_percent(interval=None)
                self._ram = psutil.virtual_memory().percent
        if self._ticker % 12 == 0:
            # Scroll data streams
            self._stream_l.pop()
            self._stream_l.insert(0, f"{random.randint(0,0xFFFFFF):06X}")
            self._stream_r.pop()
            self._stream_r.insert(0, f"{random.randint(0,0xFFFF):04X}")

        now = datetime.now().strftime("%H:%M:%S")
        c.itemconfig(self._dp_clk, text=now)

        self.root.after(1000 // FPS, self._animate)

    # ── DRAW HELPERS ─────────────────────────────────────────────────────────

    def _draw_hex_grid(self, cx, cy, r):
        c = self._canvas
        c.delete("hexgrid")
        hw = HEX_R * math.sqrt(3)
        rows = int(self._h / (HEX_R * 1.5)) + 3
        cols = int(self._w / hw) + 3
        for row in range(-1, rows):
            for col in range(-1, cols):
                hx = col * hw + (hw/2 if row % 2 else 0)
                hy = row * HEX_R * 1.5
                dist = math.hypot(hx - cx, hy - cy)
                max_d = r * 2.5
                if dist > max_d:
                    continue
                fade = max(0.0, 1.0 - dist / max_d)
                if dist < r * 0.80:
                    col_h = "#0C2030"
                elif dist < r * 1.20:
                    col_h = "#071828"
                elif dist < r * 1.80:
                    col_h = "#041220"
                else:
                    col_h = "#030C18"

                pts = []
                for k in range(6):
                    a = math.radians(60 * k + 30)
                    pts.extend([hx + HEX_R*0.90*math.cos(a), hy + HEX_R*0.90*math.sin(a)])
                c.create_polygon(*pts, outline=col_h, fill='', tags="hexgrid", width=1)

        c.tag_lower("hexgrid")

    def _draw_left_panel(self, cx, cy, r):
        c = self._canvas
        gap = r * 1.68
        pw  = max(130, min(190, cx - gap - 12))
        px  = 10
        py  = max(50, int(cy - r * 1.05))
        ph  = int(r * 2.10)
        ex  = px + pw   # right edge

        # Panel border
        bpts = [(px,py,ex,py),(px,py,px,py+ph),(ex,py,ex,py+ph),(px,py+ph,ex,py+ph)]
        for i,(x1,y1,x2,y2) in enumerate(bpts):
            c.coords(self._lp_b[i], x1,y1,x2,y2)

        # Corner accents (L-brackets at each corner)
        s2 = 10
        ca = [(px,py,px+s2,py),(px,py,px,py+s2),(ex,py,ex-s2,py),(ex,py,ex,py+s2),
              (px,py+ph,px+s2,py+ph),(px,py+ph,px,py+ph-s2),(ex,py+ph,ex-s2,py+ph),(ex,py+ph,ex,py+ph-s2)]
        for i,(x1,y1,x2,y2) in enumerate(ca):
            c.coords(self._lp_c[i], x1,y1,x2,y2)

        lx = px + 10
        lh = 15

        c.coords(self._lp_title,   lx, py + 10)
        c.coords(self._lp_cpu_l,   lx, py + 10 + lh*2)
        c.coords(self._lp_cpu_v,   lx + 46, py + 10 + lh*2)
        c.itemconfig(self._lp_cpu_v, text=f"{self._cpu:.0f}%")

        # CPU bar
        bx1,by1,bx2,by2 = lx, py+10+lh*3, ex-10, py+10+lh*3+7
        c.coords(self._lp_cpu_bg, bx1,by1,bx2,by2)
        fw = bx1 + (bx2-bx1)*self._cpu/100
        c.coords(self._lp_cpu_fg, bx1,by1,fw,by2)

        c.coords(self._lp_ram_l, lx, py+10+lh*4)
        c.coords(self._lp_ram_v, lx+46, py+10+lh*4)
        c.itemconfig(self._lp_ram_v, text=f"{self._ram:.0f}%")

        bx1,by1,bx2,by2 = lx, py+10+lh*5, ex-10, py+10+lh*5+7
        c.coords(self._lp_ram_bg, bx1,by1,bx2,by2)
        fw = bx1 + (bx2-bx1)*self._ram/100
        c.coords(self._lp_ram_fg, bx1,by1,fw,by2)

        now = datetime.now()
        extras = [
            f"AUDIO  : 48kHz",
            f"NEURAL : ONLINE",
            f"SESSION: {now.strftime('%H:%M')}",
            f"DATE   : {now.strftime('%d %b %Y')}",
        ]
        for i, ex_lbl in enumerate(self._lp_extra[:4]):
            c.coords(ex_lbl, lx, py+10+lh*(7+i))
            c.itemconfig(ex_lbl, text=extras[i])

        # Data stream
        for i, sl in enumerate(self._lp_stream):
            c.coords(sl, lx, py+10+lh*(12+i))
            c.itemconfig(sl, text=self._stream_l[i] if i < len(self._stream_l) else "")

    def _draw_right_panel(self, cx, cy, r):
        c = self._canvas
        gap = r * 1.68
        pw  = max(130, min(190, self._w - cx - gap - 12))
        px  = int(self._w - 10 - pw)
        py  = max(50, int(cy - r * 1.05))
        ph  = int(r * 2.10)
        ex  = self._w - 10
        rx  = ex - 10   # text right anchor x

        bpts = [(px,py,ex,py),(px,py,px,py+ph),(ex,py,ex,py+ph),(px,py+ph,ex,py+ph)]
        for i,(x1,y1,x2,y2) in enumerate(bpts):
            c.coords(self._rp_b[i], x1,y1,x2,y2)

        s2 = 10
        ca = [(px,py,px+s2,py),(px,py,px,py+s2),(ex,py,ex-s2,py),(ex,py,ex,py+s2),
              (px,py+ph,px+s2,py+ph),(px,py+ph,px,py+ph-s2),(ex,py+ph,ex-s2,py+ph),(ex,py+ph,ex,py+ph-s2)]
        for i,(x1,y1,x2,y2) in enumerate(ca):
            c.coords(self._rp_c[i], x1,y1,x2,y2)

        lh = 15
        c.coords(self._rp_title, rx, py+10)

        voice = self.config.get('voice_name', 'en-GB-RyanNeural').split('-')[-1].replace('Neural','')
        rlines = [
            f"MODEL   : GEMINI-2.0",
            f"VOICE   : {voice.upper()}",
            f"STT     : WHISPER",
            f"LATENCY : <100ms",
            f"ENCRYPT : AES-256",
            f"STATUS  : SECURE",
        ]
        for i, rl in enumerate(self._rp_lines):
            c.coords(rl, rx, py+10+lh*(2+i))
            c.itemconfig(rl, text=rlines[i])

        for i, sl in enumerate(self._rp_stream):
            c.coords(sl, rx, py+10+lh*(10+i))
            c.itemconfig(sl, text=self._stream_r[i] if i < len(self._stream_r) else "")

    def _draw_dialogue(self, t):
        c = self._canvas
        mg = 12
        ph = 72
        py = self._h - ph - 4
        pw = self._w - mg*2

        c.coords(self._dp_bg,  mg, py, mg+pw, py+ph)
        c.coords(self._dp_div, mg, py, mg+pw, py)
        c.coords(self._dp_src, mg+14, py+11)
        c.itemconfig(self._dp_src, text=f"● {self._diag_source}")
        c.coords(self._dp_clk, mg+pw-14, py+11)
        c.coords(self._dp_txt, mg+14, py+30)
        c.itemconfig(self._dp_txt, text=self._diag_text, width=pw-28)

    def _draw_osc(self, t, spd, mid, dim):
        c = self._canvas
        n = 70
        oy = self._h - 82
        pts1, pts2 = [], []
        for i in range(n):
            x = self._w * i / (n-1)
            a1 = t * spd * 0.4 + i * 0.22
            a2 = t * spd * 0.25 + i * 0.15 + 1.1
            pts1.extend([x, oy + STATE[self._status]['amp'] * 0.12 * math.sin(a1)])
            pts2.extend([x, oy + STATE[self._status]['amp'] * 0.07 * math.sin(a2)])
        if len(pts1) >= 4:
            c.coords(self._osc1, *pts1)
            c.coords(self._osc2, *pts2)
        c.itemconfig(self._osc1, fill=mid)
        c.itemconfig(self._osc2, fill=dim)

    # ── COLOUR HELPERS ───────────────────────────────────────────────────────

    @staticmethod
    def _lerp_colour(c1: str, c2: str, t: float) -> str:
        """Linear interpolate between two hex colour strings."""
        try:
            r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
            r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
            t = max(0.0, min(1.0, t))
            return f"#{int(r1+(r2-r1)*t):02X}{int(g1+(g2-g1)*t):02X}{int(b1+(b2-b1)*t):02X}"
        except Exception:
            return c1

    @staticmethod
    def _shift_colour(c1: str, offset: int) -> str:
        """Brighten a hex colour by adding offset to each channel."""
        try:
            r,g,b = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
            return f"#{min(r+offset,255):02X}{min(g+offset,255):02X}{min(b+offset,255):02X}"
        except Exception:
            return c1

    # ── PUBLIC API ───────────────────────────────────────────────────────────

    def set_status(self, status: str):
        if status in STATE:
            self._status = status
        if status == 'listening':
            self._activate_btn.configure(fg=GREEN_LIT, text="● LISTENING — SPEAK NOW...")
        elif status == 'thinking':
            self._activate_btn.configure(fg=GOLD, text="◎ NEURAL SYNTHESIS IN PROGRESS...")
        elif status == 'speaking':
            self._activate_btn.configure(fg=CYAN_BRIGHT, text="▶ AUDIO MATRIX TRANSMITTING...")
        else:
            hk = self.config.get('hotkey', 'P').upper()
            self._activate_btn.configure(fg=CYAN_BRIGHT, text=f"◉   ACTIVATE VOICE INTERFACE   [ {hk} ]")

    def add_aria_message(self, text: str):
        self._diag_source = "A.R.I.A."
        self._diag_text = text
        self._canvas.itemconfig(self._dp_src, fill=CYAN_BRIGHT)

    def add_user_message(self, text: str):
        self._diag_source = self.config.get('user_name', 'MADHAV').upper()
        self._diag_text = text
        self._canvas.itemconfig(self._dp_src, fill=GOLD)

    def add_system_message(self, text: str):
        self._diag_source = "SYSTEM"
        self._diag_text = text
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

    # ── INTERNAL ─────────────────────────────────────────────────────────────

    def _on_mic_click(self):
        if self.on_listen_request:
            threading.Thread(target=self.on_listen_request, daemon=True).start()

    def _on_close(self):
        self._running = False
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
        self.add_system_message("Conversation memory cleared — session reset complete.")

    # ── SETTINGS MODAL ───────────────────────────────────────────────────────

    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("ARIA — SYSTEM CONFIGURATION")
        win.configure(bg=BG)
        win.geometry("520x720")
        win.resizable(False, True)
        win.grab_set()

        tk.Label(win, text="◈  SYSTEM CONFIGURATION CONSOLE",
                 bg=BG, fg=CYAN_BRIGHT, font=('Consolas', 11, 'bold')).pack(pady=(14, 2))
        tk.Frame(win, bg=PANEL_EDGE, height=1).pack(fill='x', padx=16)

        outer = tk.Frame(win, bg=BG)
        outer.pack(fill='both', expand=True, padx=16, pady=8)
        cs = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient='vertical', command=cs.yview, bg=BG)
        sf = tk.Frame(cs, bg=BG)
        sf.bind("<Configure>", lambda e: cs.configure(scrollregion=cs.bbox("all")))
        cs.create_window((0,0), window=sf, anchor='nw')
        cs.configure(yscrollcommand=sb.set)
        cs.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        cs.bind("<MouseWheel>", lambda e: cs.yview_scroll(-1*(e.delta//120), "units"))

        def section(text):
            tk.Frame(sf, bg=PANEL_EDGE, height=1).pack(fill='x', pady=(12,4))
            tk.Label(sf, text=f"◈  {text}", bg=BG, fg=CYAN_MID, font=('Consolas',8,'bold')).pack(anchor='w')

        def field(label, var, note="", show=None):
            f = tk.Frame(sf, bg=BG); f.pack(fill='x', pady=3)
            tk.Label(f, text=label, bg=BG, fg=TEXT_MID, font=('Consolas',8,'bold')).pack(anchor='w')
            e = tk.Entry(f, textvariable=var, bg='#030D1A', fg=CYAN_BRIGHT,
                         insertbackground=CYAN_BRIGHT, relief='flat', bd=0,
                         font=('Consolas',9), highlightthickness=1,
                         highlightbackground=CYAN_DIM, highlightcolor=CYAN_BRIGHT, show=show or '')
            e.pack(fill='x', ipady=5)
            if note:
                tk.Label(f, text=note, bg=BG, fg=TEXT_DIM, font=('Consolas',7), wraplength=460).pack(anchor='w')

        user_v  = tk.StringVar(value=self.config.get('user_name','Madhav'))
        api_v   = tk.StringVar(value=self.config.get('gemini_api_key',''))
        hk_v    = tk.StringVar(value=self.config.get('hotkey','P'))
        sum_v   = tk.StringVar(value=self.config.get('summon_hotkey','ctrl+space'))
        city_v  = tk.StringVar(value=self.config.get('weather_city',''))
        spd_v   = tk.IntVar(value=self.config.get('voice_speed',175))
        voice_v = tk.StringVar(value=self.config.get('voice_name','en-GB-RyanNeural'))
        lang_v  = tk.StringVar(value=self.config.get('stt_language','en-IN'))

        section("OPERATOR PROFILE")
        field("OPERATOR NAME", user_v, "Your name for personalized ARIA interactions.")

        section("GEMINI NEURAL AI CORE")
        field("GEMINI API KEY", api_v, "Free key from aistudio.google.com/apikey", show='*')

        section("NEURAL VOICE MATRIX")
        vf = tk.Frame(sf, bg=BG); vf.pack(fill='x', pady=3)
        tk.Label(vf, text="VOICE PROFILE", bg=BG, fg=TEXT_MID, font=('Consolas',8,'bold')).pack(anchor='w')
        vm = tk.OptionMenu(vf, voice_v, "en-GB-RyanNeural", "en-US-GuyNeural",
                           "en-US-ChristopherNeural", "en-US-BrianNeural", "en-US-EricNeural")
        vm.config(bg='#030D1A', fg=CYAN_BRIGHT, activebackground='#061828',
                  activeforeground=CYAN_BRIGHT, relief='flat', highlightthickness=0,
                  font=('Consolas',9), cursor='hand2')
        vm["menu"].config(bg='#030D1A', fg=CYAN_BRIGHT, font=('Consolas',9))
        vm.pack(fill='x', pady=2)

        def _test_voice():
            name = user_v.get().strip() or "Madhav"
            v    = voice_v.get()
            txt  = f"Hey {name}, ARIA online. All systems nominal and ready."
            def _play():
                try:
                    import tempfile as tf
                    with tf.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                        tmp = fp.name
                    async def _g():
                        await edge_tts.Communicate(txt, voice=v).save(tmp)
                    lp = asyncio.new_event_loop(); lp.run_until_complete(_g()); lp.close()
                    pygame.mixer.music.load(tmp)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                    pygame.mixer.music.unload()
                    os.remove(tmp)
                except Exception as ex:
                    print(f"[Settings] Voice test error: {ex}")
            threading.Thread(target=_play, daemon=True).start()

        tk.Button(vf, text="🔊  PREVIEW VOICE SAMPLE", command=_test_voice,
                  bg='#001C2C', fg=CYAN_BRIGHT, activebackground='#002C3C',
                  relief='flat', bd=0, font=('Consolas',8,'bold'), cursor='hand2', pady=6
                  ).pack(anchor='w', pady=(4,2))

        sf2 = tk.Frame(sf, bg=BG); sf2.pack(fill='x', pady=4)
        tk.Label(sf2, text="SPEECH RATE", bg=BG, fg=TEXT_MID, font=('Consolas',8,'bold')).pack(anchor='w')
        row = tk.Frame(sf2, bg=BG); row.pack(fill='x')
        tk.Scale(row, variable=spd_v, from_=100, to=240, orient='horizontal',
                 bg=BG, fg=CYAN_BRIGHT, troughcolor='#001828', highlightthickness=0,
                 font=('Consolas',8), length=340).pack(side='left')
        tk.Label(row, textvariable=spd_v, bg=BG, fg=CYAN_MID, font=('Consolas',9), width=4).pack(side='left')

        section("SPEECH RECOGNITION")
        lf = tk.Frame(sf, bg=BG); lf.pack(fill='x', pady=3)
        tk.Label(lf, text="MICROPHONE LANGUAGE", bg=BG, fg=TEXT_MID, font=('Consolas',8,'bold')).pack(anchor='w')
        lm = tk.OptionMenu(lf, lang_v, "en-IN", "en-US", "en-GB")
        lm.config(bg='#030D1A', fg=CYAN_BRIGHT, activebackground='#061828',
                  activeforeground=CYAN_BRIGHT, relief='flat', highlightthickness=0,
                  font=('Consolas',9), cursor='hand2')
        lm["menu"].config(bg='#030D1A', fg=CYAN_BRIGHT, font=('Consolas',9))
        lm.pack(fill='x', pady=2)

        section("HOTKEYS & REGION")
        field("VOICE ACTIVATION KEY", hk_v, "Key to start listening (e.g. P, F2, Space)")
        field("SUMMON WINDOW SHORTCUT", sum_v, "Global toggle (e.g. ctrl+space)")
        field("WEATHER CITY", city_v, "City name for weather queries (e.g. Delhi)")

        tk.Frame(win, bg=PANEL_EDGE, height=1).pack(fill='x', padx=16)
        bf = tk.Frame(win, bg=BG); bf.pack(fill='x', padx=16, pady=12)

        def _save():
            self.config['user_name']      = user_v.get().strip() or 'Madhav'
            self.config['gemini_api_key'] = api_v.get().strip()
            self.config['hotkey']         = hk_v.get().strip() or 'P'
            self.config['summon_hotkey']  = sum_v.get().strip() or 'ctrl+space'
            self.config['stt_language']   = lang_v.get().strip() or 'en-IN'
            self.config['weather_city']   = city_v.get().strip()
            self.config['voice_name']     = voice_v.get().strip() or 'en-GB-RyanNeural'
            self.config['voice_speed']    = spd_v.get()
            u = self.config['user_name'].upper()
            self._hdr_user.configure(
                text=f"OPERATOR : {u}   ·   NEURAL CORE : ONLINE   ·   WHISPER STT : ACTIVE")
            hk = self.config['hotkey'].upper()
            self._activate_btn.configure(text=f"◉   ACTIVATE VOICE INTERFACE   [ {hk} ]")
            if self.on_api_key_save:
                self.on_api_key_save(self.config)
            win.destroy()
            self.add_system_message("Configuration synchronized — all parameters updated.")

        tk.Button(bf, text="▶  SAVE & SYNCHRONIZE",
                  command=_save, bg='#001828', fg=CYAN_BRIGHT,
                  activebackground='#002840', activeforeground='#FFFFFF',
                  relief='flat', bd=0, font=('Consolas',10,'bold'),
                  cursor='hand2', pady=9).pack(fill='x')
