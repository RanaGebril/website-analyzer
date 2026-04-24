import tkinter as tk
from tkinter import ttk, font as tkfont
import threading
import time
import math
import datetime
from services.analyzer import analyze

# ── Palette ──────────────────────────────────────────────────────────────────
BG          = "#07101f"
SIDEBAR_BG  = "#060d1a"
CARD_BG     = "#0c1829"
BORDER      = "#1a2a42"
ACCENT      = "#1d6ef6"
ACCENT2     = "#0ea5e9"
SUCCESS     = "#10b981"
DANGER      = "#ef4444"
WARNING     = "#f59e0b"
TEXT        = "#e2e8f0"
TEXT_MUTED  = "#64748b"
TEXT_DIM    = "#334155"
HEADER_BG   = "#0a1628"

PROTO_ICONS = {
    "dns":  "⬡",
    "tcp":  "⇌",
    "http": "⊞",
    "ssl":  "⚷",
    "udp":  "⊙",
    "ntp":  "◷",
}


# ── Helper widgets ────────────────────────────────────────────────────────────
class Separator(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BORDER, height=1, **kw)


class RoundedCanvas(tk.Canvas):
    """Canvas with a rounded-rect background drawn each resize."""
    def __init__(self, parent, radius=10, bg_color=CARD_BG, border_color=BORDER, **kw):
        super().__init__(parent, bg=BG, highlightthickness=0, **kw)
        self._r  = radius
        self._bc = bg_color
        self._bo = border_color
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _=None):
        self.delete("bg")
        w, h = self.winfo_width(), self.winfo_height()
        r = self._r
        self.create_polygon(
            r, 0, w-r, 0,
            w, r, w, h-r,
            w-r, h, r, h,
            0, h-r, 0, r,
            smooth=True, fill=self._bc, outline=self._bo, tags="bg"
        )
        self.tag_lower("bg")


class AnimatedBar(tk.Canvas):
    """Slim progress bar with glow animation."""
    def __init__(self, parent, **kw):
        super().__init__(parent, height=6, bg=CARD_BG, highlightthickness=0, **kw)
        self._pct   = 0
        self._target = 0
        self._animating = False

    def set(self, pct, animate=True):
        self._target = max(0, min(100, pct))
        if animate and not self._animating:
            self._animating = True
            self._step()
        else:
            self._pct = self._target
            self._draw()

    def reset(self):
        self._pct = 0
        self._target = 0
        self._animating = False
        self._draw()

    def _step(self):
        diff = self._target - self._pct
        if abs(diff) < 0.5:
            self._pct = self._target
            self._animating = False
            self._draw()
            return
        self._pct += diff * 0.15
        self._draw()
        self.after(16, self._step)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 200
        # track
        self.create_rectangle(0, 1, w, 5, fill=BG, outline="")
        if self._pct > 0:
            fill_w = int(w * self._pct / 100)
            # gradient simulation via two rects
            self.create_rectangle(0, 1, fill_w, 5,
                                  fill=ACCENT, outline="")
            # bright leading edge
            if fill_w > 4:
                self.create_rectangle(fill_w-4, 1, fill_w, 5,
                                      fill=SUCCESS, outline="")


class SparklineCanvas(tk.Canvas):
    """Animated sparkline for response-time history."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=CARD_BG, highlightthickness=0, **kw)
        self._data = []
        self.bind("<Configure>", lambda _: self._draw())

    def add(self, val):
        self._data.append(val)
        if len(self._data) > 40:
            self._data = self._data[-40:]
        self._draw()

    def reset(self):
        self._data = []
        self._draw()

    def _draw(self):
        self.delete("all")
        W = self.winfo_width() or 400
        H = self.winfo_height() or 80
        if len(self._data) < 2:
            self.create_text(W//2, H//2, text="Awaiting data…",
                             fill=TEXT_DIM, font=("Consolas", 9))
            return
        mn, mx = min(self._data), max(self._data)
        spread = max(mx - mn, 1)
        pad = 12

        def px(i): return pad + i * (W - pad*2) // (len(self._data)-1)
        def py(v): return H - pad - int((v - mn) / spread * (H - pad*2))

        pts = [(px(i), py(v)) for i, v in enumerate(self._data)]

        # fill area
        poly = [pad, H] + [c for p in pts for c in p] + [pts[-1][0], H]
        self.create_polygon(poly, fill="#0d2040", outline="")

        # line
        for i in range(len(pts)-1):
            self.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                             fill=ACCENT, width=1.5, smooth=True)

        # dots
        for x, y in pts[-1:]:
            self.create_oval(x-3, y-3, x+3, y+3, fill=ACCENT2, outline="")

        # avg line
        avg = sum(self._data) / len(self._data)
        ay  = py(avg)
        self.create_line(pad, ay, W-pad, ay, fill=TEXT_DIM, dash=(3,4), width=1)
        self.create_text(W-pad-2, ay-6, text=f"avg {avg:.0f}ms",
                         fill=TEXT_DIM, font=("Consolas", 8), anchor="e")


class DonutRing(tk.Canvas):
    """Animated completion donut."""
    def __init__(self, parent, size=110, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=CARD_BG, highlightthickness=0, **kw)
        self._size  = size
        self._pct   = 0
        self._target = 0
        self._arc_id = None
        self._draw()

    def set(self, pct):
        self._target = pct
        self._animate()

    def reset(self):
        self._pct = 0
        self._target = 0
        self._draw()

    def _animate(self):
        diff = self._target - self._pct
        if abs(diff) < 0.5:
            self._pct = self._target
            self._draw()
            return
        self._pct += diff * 0.12
        self._draw()
        self.after(16, self._animate)

    def _draw(self):
        self.delete("all")
        s = self._size
        pad = 12
        # track
        self.create_arc(pad, pad, s-pad, s-pad,
                        start=90, extent=360,
                        outline=BORDER, width=8, style="arc")
        # fill
        if self._pct > 0:
            color = SUCCESS if self._pct >= 99 else ACCENT
            self.create_arc(pad, pad, s-pad, s-pad,
                            start=90, extent=-(self._pct/100*360),
                            outline=color, width=8, style="arc")
        # center text
        pct_i = int(self._pct)
        color = SUCCESS if pct_i >= 100 else TEXT
        self.create_text(s//2, s//2 - 7,
                         text=f"{pct_i}%",
                         fill=color, font=("Consolas", 16, "bold"))
        self.create_text(s//2, s//2 + 10,
                         text="complete",
                         fill=TEXT_MUTED, font=("Consolas", 8))


# ── Main App ──────────────────────────────────────────────────────────────────
class App:
    def reset_ui(self):
      self._running = False  # يوقف التحليل

      self._reset()
      self.entry.delete(0, "end")
      self.entry.insert(0, "google.com")

    # ✅ الحل هنا
      self.analyze_btn.configure(
        text="  ⊕  Analyze  ",
        bg=ACCENT,
        state="normal"
     )

      self.footer_lbl.configure(text="Cleared — ready for new analysis")
    PROTOCOLS = ["DNS", "TCP", "HTTP", "SSL", "UDP", "NTP"]

    def __init__(self, root):
        self.root = root
        self.root.title("Network Analyzer Pro")
        self.root.geometry("1180x700")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)
        self._running = False
        self._start_time = 0
        self._response_times = {}

        self._build_layout()

    # ─────────────────── layout skeleton ────────────────────────────────────
    def _build_layout(self):
        self._build_sidebar()
        self._build_content()

    # ─────────────────── sidebar ─────────────────────────────────────────────
    def _build_sidebar(self):
        sb = tk.Frame(self.root, bg=SIDEBAR_BG, width=190)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # logo
        logo_frame = tk.Frame(sb, bg=SIDEBAR_BG)
        logo_frame.pack(fill="x", padx=16, pady=(22, 12))

        icon_bg = tk.Frame(logo_frame, bg=ACCENT, width=34, height=34)
        icon_bg.pack(side="left")
        icon_bg.pack_propagate(False)
        tk.Label(icon_bg, text="⬡", bg=ACCENT, fg="white",
                 font=("Arial", 14)).place(relx=.5, rely=.5, anchor="center")

        name_frame = tk.Frame(logo_frame, bg=SIDEBAR_BG)
        name_frame.pack(side="left", padx=10)
        tk.Label(name_frame, text="Network",
                 bg=SIDEBAR_BG, fg=TEXT, font=("Arial", 11, "bold")).pack(anchor="w")
        tk.Label(name_frame, text="Analyzer Pro",
                 bg=SIDEBAR_BG, fg=TEXT_MUTED, font=("Arial", 8)).pack(anchor="w")

        Separator(sb).pack(fill="x", padx=12, pady=4)

        nav = [
            ("Analyzer",  "⊞", True),
          
        ]
        for label, icon, active in nav:
            self._nav_btn(sb, icon, label, active)


    def _nav_btn(self, parent, icon, label, active):
        bg   = "#102040" if active else SIDEBAR_BG
        fg   = ACCENT2   if active else TEXT_MUTED
        bar  = ACCENT    if active else SIDEBAR_BG

        row = tk.Frame(parent, bg=bg, cursor="hand2")
        row.pack(fill="x", pady=1)

        tk.Frame(row, bg=bar, width=3).pack(side="left", fill="y")
        tk.Label(row, text=icon, bg=bg, fg=fg,
                 font=("Arial", 12), width=3).pack(side="left", pady=10)
        tk.Label(row, text=label, bg=bg, fg=fg,
                 font=("Arial", 10, "bold" if active else "normal")).pack(side="left")

        def on_enter(e): row.configure(bg="#0d1e35")
        def on_leave(e): row.configure(bg=bg)
        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)

    # ─────────────────── content area ────────────────────────────────────────
    def _build_content(self):
        content = tk.Frame(self.root, bg=BG)
        content.pack(side="right", fill="both", expand=True)

        self._build_topbar(content)
        self._build_proto_strip(content)

        body = tk.Frame(content, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=8)

        self._build_left_panel(body)
        self._build_right_panel(body)

        self._build_footer(content)

    # ─────────────────── top bar ──────────────────────────────────────────────
    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=HEADER_BG, pady=12)
        bar.pack(fill="x", padx=0)

        inner = tk.Frame(bar, bg=HEADER_BG)
        inner.pack(fill="x", padx=14)

        # search frame
        sf = tk.Frame(inner, bg=BORDER, padx=1, pady=1)
        sf.pack(side="left", fill="x", expand=True)

        search_inner = tk.Frame(sf, bg=CARD_BG)
        search_inner.pack(fill="both", expand=True)

        tk.Label(search_inner, text="⊕", bg=CARD_BG, fg=TEXT_MUTED,
                 font=("Arial", 12), padx=8).pack(side="left")

        self.entry = tk.Entry(
            search_inner,
            font=("Consolas", 13),
            bg=CARD_BG, fg=TEXT,
            insertbackground=ACCENT2,
            relief="flat",
            bd=0,
        )
        self.entry.insert(0, "google.com")
        self.entry.pack(side="left", fill="both", expand=True, ipady=8)
        self.entry.bind("<Return>", lambda _: self.start())

        # analyze button
        self.analyze_btn = tk.Button(
            inner,
            text="  ⊕  Analyze  ",
            bg=ACCENT, fg="white",
            activebackground="#1558cc",
            activeforeground="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.start,
        )
        self.analyze_btn.pack(side="left", padx=10, ipady=8, ipadx=4)

        self.clear_btn = tk.Button(
          inner,
          text="  ✕  Clear  ",
          bg="#334155",
          fg="white",
          activebackground="#1f2937",
          activeforeground="white",
          font=("Arial", 11, "bold"),
          relief="flat",
          bd=0,
         cursor="hand2",
         command=self.reset_ui
)
        self.clear_btn.pack(side="left", padx=5, ipady=8, ipadx=4)
        # overall badge
        self.overall_frame = tk.Frame(inner, bg="#071c0e", padx=12, pady=6)
        self.overall_frame.pack(side="right")
        tk.Label(self.overall_frame, text="⊛", bg="#071c0e", fg=SUCCESS,
                 font=("Arial", 11)).pack(side="left")
        tk.Label(self.overall_frame, text="Overall Status",
                 bg="#071c0e", fg=TEXT_MUTED, font=("Arial", 8)).pack(side="left", padx=(6,0))
        self.overall_lbl = tk.Label(self.overall_frame, text="Good",
                                    bg="#071c0e", fg=SUCCESS,
                                    font=("Arial", 11, "bold"))
        self.overall_lbl.pack(side="left", padx=6)



    # ─────────────────── protocol strip ──────────────────────────────────────
    def _build_proto_strip(self, parent):
        strip = tk.Frame(parent, bg=BG)
        strip.pack(fill="x", padx=14, pady=(8, 0))

        self._proto_cards = {}

        for p in self.PROTOCOLS:
            card = tk.Frame(strip, bg=CARD_BG, padx=12, pady=10,
                            highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", expand=True, fill="x", padx=4)

            header = tk.Frame(card, bg=CARD_BG)
            header.pack(fill="x")

            icon_lbl = tk.Label(header, text=PROTO_ICONS[p.lower()],
                                bg=CARD_BG, fg=TEXT_MUTED, font=("Arial", 14))
            icon_lbl.pack(side="left")

            status_dot = tk.Label(header, text="●", bg=CARD_BG, fg=TEXT_DIM,
                                  font=("Arial", 8))
            status_dot.pack(side="right")

            tk.Label(card, text=p, bg=CARD_BG, fg=TEXT,
                     font=("Arial", 10, "bold")).pack(anchor="w", pady=(4, 0))

            sub_lbl = tk.Label(card, text="—",
                               bg=CARD_BG, fg=TEXT_MUTED, font=("Consolas", 8))
            sub_lbl.pack(anchor="w")

            self._proto_cards[p.lower()] = {
                "frame":  card,
                "dot":    status_dot,
                "icon":   icon_lbl,
                "sub":    sub_lbl,
            }

    # ─────────────────── left panel (progress) ───────────────────────────────
    def _build_left_panel(self, parent):
        lf = tk.Frame(parent, bg=CARD_BG, padx=14, pady=14,
                      highlightbackground=BORDER, highlightthickness=1)
        lf.pack(side="left", fill="y", padx=(0, 8))

        tk.Label(lf, text="▸ Progress", bg=CARD_BG, fg=TEXT,
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 10))

        self._bars = {}
        self._bar_pct_lbls = {}

        for p in self.PROTOCOLS:
            row = tk.Frame(lf, bg=CARD_BG)
            row.pack(fill="x", pady=5)

            hdr = tk.Frame(row, bg=CARD_BG)
            hdr.pack(fill="x")

            tk.Label(hdr, text=PROTO_ICONS[p.lower()], bg=CARD_BG,
                     fg=TEXT_MUTED, font=("Arial", 10), width=2).pack(side="left")
            tk.Label(hdr, text=p, bg=CARD_BG, fg=TEXT,
                     font=("Arial", 9, "bold")).pack(side="left", padx=4)

            pct_lbl = tk.Label(hdr, text="0%", bg=CARD_BG, fg=TEXT_DIM,
                               font=("Consolas", 8))
            pct_lbl.pack(side="right")

            bar = AnimatedBar(row, width=190)
            bar.pack(fill="x", pady=(3, 0))

            self._bars[p.lower()] = bar
            self._bar_pct_lbls[p.lower()] = pct_lbl

    # ─────────────────── right panel (results log) ───────────────────────────
    def _build_right_panel(self, parent):
        rf = tk.Frame(parent, bg=CARD_BG, padx=14, pady=14,
                      highlightbackground=BORDER, highlightthickness=1)
        rf.pack(side="right", fill="both", expand=True)

        hdr = tk.Frame(rf, bg=CARD_BG)
        hdr.pack(fill="x", pady=(0, 8))

        tk.Label(hdr, text="▸ Results", bg=CARD_BG, fg=TEXT,
                 font=("Arial", 10, "bold")).pack(side="left")

        

        log_outer = tk.Frame(rf, bg=BG, highlightbackground=BORDER,
                             highlightthickness=1)
        log_outer.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            log_outer,
            bg=BG, fg=TEXT,
            font=("Consolas", 10),
            relief="flat", bd=0,
            padx=10, pady=8,
            state="disabled",
            cursor="arrow",
            wrap="word",
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(log_outer, command=self.log_text.yview)
        sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=sb.set)

        # color tags
        self.log_text.tag_configure("ok",      foreground=SUCCESS)
        self.log_text.tag_configure("fail",     foreground=DANGER)
        self.log_text.tag_configure("key",      foreground=ACCENT2, font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("val",      foreground=TEXT)
        self.log_text.tag_configure("detail",   foreground=TEXT_MUTED, font=("Consolas", 9))
        self.log_text.tag_configure("dim",      foreground=TEXT_DIM,  font=("Consolas", 9))
        self.log_text.tag_configure("section",  foreground=TEXT_DIM,  font=("Consolas", 8))

    
    # ─────────────────── footer ───────────────────────────────────────────────
    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=HEADER_BG, pady=5)
        footer.pack(fill="x", side="bottom")

        self.footer_lbl = tk.Label(footer, text="Ready — enter a domain and press Analyze",
                                   bg=HEADER_BG, fg=TEXT_DIM, font=("Consolas", 8))
        self.footer_lbl.pack(side="left", padx=14)

        tk.Label(footer, text="Built with ♥ using Python",
                 bg=HEADER_BG, fg=TEXT_DIM, font=("Consolas", 8)).pack(side="right", padx=14)

    # ─────────────────── log helpers ─────────────────────────────────────────
    def _log(self, *parts):
        """parts: list of (text, tag) tuples, or just strings."""
        self.log_text.configure(state="normal")
        for item in parts:
            if isinstance(item, tuple):
                self.log_text.insert("end", item[0], item[1])
            else:
                self.log_text.insert("end", item)
        self.log_text.insert("end", "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ─────────────────── reset UI ────────────────────────────────────────────
    def _reset(self):
        self._clear_log()
        for key in [p.lower() for p in self.PROTOCOLS]:
            self._bars[key].reset()
            self._bar_pct_lbls[key].configure(text="0%", fg=TEXT_DIM)
            c = self._proto_cards[key]
            c["dot"].configure(fg=TEXT_DIM)
            c["icon"].configure(fg=TEXT_MUTED)
            c["sub"].configure(text="—")
            c["frame"].configure(highlightbackground=BORDER)
  
        self.overall_lbl.configure(text="Scanning…", fg=WARNING)
        self._response_times = {}

    # ─────────────────── callback from analyzer thread ───────────────────────
    def callback(self, key, value):
        self.root.after(0, self._handle, key, value)

    def _handle(self, key, value):
        if key == "done":
            self._finish()
            return

        ok = "Failed" not in str(value) and "No SSL" not in str(value)
        color  = SUCCESS if ok else DANGER
        dot    = "●"

        # update protocol card
        c = self._proto_cards.get(key)
        if c:
            c["dot"].configure(fg=color)
            c["icon"].configure(fg=color)
            first_line = str(value).split("\n")[0][:28]
            c["sub"].configure(text=first_line, fg=color)
            c["frame"].configure(highlightbackground=color if ok else DANGER)

        # update progress bar
        bar = self._bars.get(key)
        if bar:
            bar.set(100)
            self._bar_pct_lbls[key].configure(text="100%", fg=color)

        # sparkline — extract ms if present
        import re
        m = re.search(r"(\d+)\s*ms", str(value))
        if m:
            ms = int(m.group(1))
            self._response_times[key] = ms
           
            times = list(self._response_times.values())
          
           

        # donut
        done = sum(1 for k in self.PROTOCOLS if self._bars[k.lower()]._pct >= 99)

        # log
        tag = "ok" if ok else "fail"
        marker = "✔" if ok else "✘"
        self._log(
            (f" {marker} ", tag),
            (f"{key.upper():<5}", "key"),
            ("  ", ""),
            (str(value).split("\n")[0], "val"),
        )
        # sub-lines (SSL detail)
        for line in str(value).split("\n")[1:]:
            self._log(("       " + line, "detail"))



    def _finish(self):
        self._running = False
        elapsed = time.time() - self._start_time
        self.analyze_btn.configure(text="  ⊕  Analyze  ", bg=ACCENT, state="normal")
        self.overall_lbl.configure(text="Good", fg=SUCCESS)
        domain = self.entry.get().strip()
        self._sum_vals["domain"].configure(text=domain)
        now = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        self._sum_vals["date"].configure(text=now)
        self.footer_lbl.configure(
            text=f"Last analysis: {now}   ·   {elapsed:.2f}s total"
        )
        self._log(
            ("\n ─────────────────────────────────────", "section"),
        )
        self._log(
            (f"  Analysis complete in {elapsed:.2f}s", "dim"),
        )

    # ─────────────────── start ────────────────────────────────────────────────
    def start(self):
        if self._running:
            return
        domain = self.entry.get().strip()
        if not domain:
            return

        self._running = True
        self._start_time = time.time()
        self._reset()

        self.analyze_btn.configure(text="  ⟳  Scanning…", bg="#0f4eb5", state="disabled")
        self.footer_lbl.configure(text=f"Analyzing {domain}…")

        self._log(
            (f" ⊕  Starting analysis for ", "dim"),
            (domain, "key"),
            ("\n", ""),
        )

        threading.Thread(
            target=lambda: analyze(domain, self.callback),
            daemon=True,
        ).start()



