"""
Net Monitor Pro — شريط مراقبة سرعة الإنترنت الاحترافي
======================================================
شريط مراقبة أنيق شبه شفاف يشبه أدوات مراقبة الأداء في شاشات الألعاب
(FPS/Network Overlays)، يعرض سرعة الرفع والتنزيل + رسم بياني متحرك
(Sparkline) لكل منهما، مع زرّي إغلاق وتصغير واضحين على الشريط نفسه.

المتطلبات:
    pip install psutil

التشغيل:
    python net_monitor.py

الميزات:
- شريط علوي بحواف مدورة وخلفية داكنة واضحة (شفافية معتدلة قابلة للتحكم
  بعجلة الفأرة، وليست شفافية شديدة تُصعّب القراءة).
- زر تصغير (–) وزر إغلاق (×) ثابتان في أعلى يمين الشريط، مرئيان دائمًا.
- رسم بياني (Sparkline) متحرك لكل من الرفع والتنزيل بألوان مميزة.
- عرض السرعة الحالية + أعلى سرعة مسجلة (Peak) لكل اتجاه.
- إجمالي البيانات المستهلكة في الجلسة الحالية (رفع/تنزيل) بوحدات ذكية
  (KB/MB/GB).
- تلوين ديناميكي يتغير حسب شدة الحمل (رمادي -> اللون الأساسي -> أصفر -> أحمر).
- سحب الشريط بالفأرة لأي مكان على الشاشة، مع حفظ آخر موضع ومستوى الشفافية
  تلقائيًا بين مرات التشغيل.
- وضع مصغّر (شريط رفيع بسطر واحد) يمكن الرجوع منه للوضع الكامل بنقرة على
  زر التكبير.
- عجلة الفأرة فوق الشريط لضبط مستوى الشفافية (Opacity) مباشرة.
"""

import tkinter as tk
from collections import deque
import psutil
import time
import json
import os
import sys

# =========================================================
# الإعدادات العامة
# =========================================================
BG = "#0e0e14"
BG_MIN = "#0e0e14"
BORDER = "#2b2b3d"
ACCENT = "#3a3a52"
UP_COLOR = "#ff3b5c"
DOWN_COLOR = "#2fa8ff"
TEXT_DIM = "#9a9ab0"
TEXT_BRIGHT = "#e8e8f0"
BTN_HOVER = "#2a2a3f"
CLOSE_HOVER = "#7a1f30"

FONT_MAIN = ("Segoe UI", 10, "bold")
FONT_SMALL = ("Segoe UI", 8)
FONT_TINY = ("Segoe UI", 7)

GRAPH_H = 24
HISTORY_LEN = 40
UPDATE_MS = 500

MIN_ALPHA = 0.55
MAX_ALPHA = 1.0
DEFAULT_ALPHA = 0.97   # شفافية معتدلة افتراضيًا (كانت 0.90 شديدة الشفافية)

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".net_monitor_pro.json")


def speed_color(mbps, base_color):
    if mbps < 1:
        return TEXT_DIM
    if mbps < 20:
        return base_color
    if mbps < 80:
        return "#ffd23f"
    return "#ff4747"


def format_bytes(n):
    """تحويل عدد البايتات إلى وحدة مقروءة (KB/MB/GB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


class NetMonitor:
    def __init__(self):
        self.config = load_config()
        self.alpha = float(self.config.get("alpha", DEFAULT_ALPHA))
        self.alpha = max(MIN_ALPHA, min(MAX_ALPHA, self.alpha))

        self.root = tk.Tk()
        self.root.title("Net Monitor Pro")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)

        try:
            self.root.attributes("-alpha", self.alpha)
        except Exception:
            pass

        # الشفافية "الحقيقية" (اختفاء الخلفية تمامًا خلف لون معيّن) متاحة على
        # ويندوز فقط، وهي معطّلة افتراضيًا الآن لتسهيل قراءة الشريط ورؤية
        # زرّي التصغير والإغلاق بوضوح. يمكن تفعيلها من true_transparency_enabled.
        self.true_transparency_enabled = False

        self.width_full = 360
        self.height_full = 66
        self.height_min = 26

        self.minimized = bool(self.config.get("minimized", False))
        self.width = self.width_full
        self.height = self.height_min if self.minimized else self.height_full

        self.canvas = tk.Canvas(
            self.root, width=self.width, height=self.height,
            bg=BG, highlightthickness=0, bd=0
        )
        self.canvas.pack()

        self.down_history = deque([0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.up_history = deque([0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.peak_down = 0.0
        self.peak_up = 0.0
        self.total_down_bytes = 0
        self.total_up_bytes = 0

        self.last_counters = psutil.net_io_counters()
        self.last_time = time.monotonic()

        self._dragging = False
        self._drag_x = 0
        self._drag_y = 0

        self._build_layout()
        self._bind_events()
        self._restore_position()

        self.update_speed()

    # ---------------------------------------------------
    # أدوات رسم مساعدة
    # ---------------------------------------------------
    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, x1 + r, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    # ---------------------------------------------------
    # بناء الواجهة (كاملة أو مصغّرة)
    # ---------------------------------------------------
    def _build_layout(self):
        self.canvas.delete("all")
        self.canvas.config(width=self.width, height=self.height)
        self.root.geometry(f"{self.width}x{self.height}")

        if self.minimized:
            self._build_minimized_layout()
        else:
            self._build_full_layout()

        self._build_title_buttons()

    def _build_title_buttons(self):
        """زر التصغير (–) وزر الإغلاق (×) ثابتان أعلى يمين الشريط."""
        btn_y = 9 if not self.minimized else self.height // 2
        close_x = self.width - 14
        min_x = self.width - 34

        self.min_btn_bg = self.canvas.create_oval(
            min_x - 9, btn_y - 9, min_x + 9, btn_y + 9,
            fill="", outline=""
        )
        self.min_btn_icon = self.canvas.create_text(
            min_x, btn_y, text=("▢" if self.minimized else "–"),
            fill=TEXT_BRIGHT, font=FONT_SMALL
        )

        self.close_btn_bg = self.canvas.create_oval(
            close_x - 9, btn_y - 9, close_x + 9, btn_y + 9,
            fill="", outline=""
        )
        self.close_btn_icon = self.canvas.create_text(
            close_x, btn_y, text="×",
            fill=TEXT_BRIGHT, font=("Segoe UI", 10, "bold")
        )

        for item in (self.min_btn_bg, self.min_btn_icon):
            self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.itemconfig(self.min_btn_bg, fill=BTN_HOVER))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.itemconfig(self.min_btn_bg, fill=""))
            self.canvas.tag_bind(item, "<Button-1>", self._toggle_minimize)

        for item in (self.close_btn_bg, self.close_btn_icon):
            self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.itemconfig(self.close_btn_bg, fill=CLOSE_HOVER))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.itemconfig(self.close_btn_bg, fill=""))
            self.canvas.tag_bind(item, "<Button-1>", self._close)

    def _build_full_layout(self):
        self._rounded_rect(1, 1, self.width - 1, self.height - 1, 14,
                            fill=BG, outline=BORDER, width=1)
        self.canvas.create_line(self.width // 2, 8, self.width // 2, self.height - 8, fill=BORDER)

        pad = 12
        gx_down = pad
        gx_up = self.width // 2 + pad

        self.canvas.create_text(gx_down, 8, anchor="nw", text="↓ DOWN", fill=TEXT_DIM, font=FONT_SMALL)
        self.down_text = self.canvas.create_text(gx_down, 21, anchor="nw", text="0.00 Mbps", fill=DOWN_COLOR, font=FONT_MAIN)
        self.down_peak_text = self.canvas.create_text(gx_down, 40, anchor="nw", text="Peak 0.00", fill=TEXT_DIM, font=FONT_TINY)
        self.down_total_text = self.canvas.create_text(gx_down, 52, anchor="nw", text="Total: 0 B", fill=TEXT_DIM, font=FONT_TINY)

        self.canvas.create_text(gx_up, 8, anchor="nw", text="↑ UP", fill=TEXT_DIM, font=FONT_SMALL)
        self.up_text = self.canvas.create_text(gx_up, 21, anchor="nw", text="0.00 Mbps", fill=UP_COLOR, font=FONT_MAIN)
        self.up_peak_text = self.canvas.create_text(gx_up, 40, anchor="nw", text="Peak 0.00", fill=TEXT_DIM, font=FONT_TINY)
        self.up_total_text = self.canvas.create_text(gx_up, 52, anchor="nw", text="Total: 0 B", fill=TEXT_DIM, font=FONT_TINY)

        # مساحة صغيرة للرسم البياني أسفل يمين كل قسم (بجانر النص الرئيسي)
        self.graph_y0 = 20
        self.graph_y1 = 20 + GRAPH_H
        gw = 70
        self.down_graph_x1 = self.width // 2 - pad
        self.down_graph_x0 = self.down_graph_x1 - gw
        self.up_graph_x1 = self.width - pad - 26  # تفادي أزرار التصغير/الإغلاق
        self.up_graph_x0 = self.up_graph_x1 - gw

    def _build_minimized_layout(self):
        self._rounded_rect(1, 1, self.width - 1, self.height - 1, self.height // 2,
                            fill=BG, outline=BORDER, width=1)
        pad = 14
        self.down_text = self.canvas.create_text(
            pad, self.height // 2, anchor="w", text="↓ 0.00", fill=DOWN_COLOR, font=FONT_SMALL
        )
        self.up_text = self.canvas.create_text(
            self.width // 2 + pad - 10, self.height // 2, anchor="w", text="↑ 0.00", fill=UP_COLOR, font=FONT_SMALL
        )
        # لا يوجد رسم بياني أو Peak في الوضع المصغّر
        self.down_peak_text = self.up_peak_text = None
        self.down_total_text = self.up_total_text = None
        self.down_graph_x0 = self.down_graph_x1 = self.up_graph_x0 = self.up_graph_x1 = None

    # ---------------------------------------------------
    # الأحداث: سحب، تصغير/تكبير، إغلاق، شفافية بعجلة الفأرة
    # ---------------------------------------------------
    def _bind_events(self):
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        # عجلة الفأرة لضبط الشفافية (ويندوز/ماك)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        # لينكس: زر التمرير لأعلى/أسفل يأتي كأحداث منفصلة
        self.canvas.bind("<Button-4>", lambda e: self._change_alpha(0.03))
        self.canvas.bind("<Button-5>", lambda e: self._change_alpha(-0.03))

    def _start_drag(self, event):
        item = self.canvas.find_withtag("current")
        if item and item[0] in (self.min_btn_bg, self.min_btn_icon, self.close_btn_bg, self.close_btn_icon):
            self._dragging = False
            return
        self._dragging = True
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag(self, event):
        if self._dragging:
            self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _end_drag(self, event):
        if self._dragging:
            self._dragging = False
            self._save_state()

    def _on_scroll(self, event):
        delta = 0.03 if event.delta > 0 else -0.03
        self._change_alpha(delta)

    def _change_alpha(self, delta):
        self.alpha = max(MIN_ALPHA, min(MAX_ALPHA, self.alpha + delta))
        try:
            self.root.attributes("-alpha", self.alpha)
        except Exception:
            pass
        self._save_state()

    def _toggle_minimize(self, event=None):
        self.minimized = not self.minimized
        self.height = self.height_min if self.minimized else self.height_full
        self._build_layout()
        self._save_state()

    def _close(self, event=None):
        self._save_state()
        self.root.destroy()

    def _restore_position(self):
        x = self.config.get("x")
        y = self.config.get("y")
        self.root.update_idletasks()
        if x is None or y is None:
            x = (self.root.winfo_screenwidth() - self.width) // 2
            y = 4
        self.root.geometry(f"+{x}+{y}")

    def _save_state(self):
        save_config({
            "x": self.root.winfo_x(),
            "y": self.root.winfo_y(),
            "alpha": self.alpha,
            "minimized": self.minimized,
        })

    # ---------------------------------------------------
    # رسم الـ Sparkline
    # ---------------------------------------------------
    def _draw_sparkline(self, tag, history, x0, y0, x1, y1, color):
        self.canvas.delete(tag)
        if x0 is None:
            return
        max_val = max(max(history), 1.0)
        n = len(history)
        step = (x1 - x0) / max(n - 1, 1)

        points = []
        for i, v in enumerate(history):
            x = x0 + i * step
            y = y1 - (v / max_val) * (y1 - y0)
            points.extend([x, y])

        if len(points) >= 4:
            self.canvas.create_line(
                *points, fill=color, width=2, smooth=True,
                tag=tag, capstyle="round", joinstyle="round"
            )
            fill_points = points + [x1, y1, x0, y1]
            self.canvas.create_polygon(
                *fill_points, fill=color, outline="", stipple="gray25", tag=tag
            )

    # ---------------------------------------------------
    # التحديث الدوري
    # ---------------------------------------------------
    def update_speed(self):
        current = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(now - self.last_time, 0.001)

        down_delta = max(current.bytes_recv - self.last_counters.bytes_recv, 0)
        up_delta = max(current.bytes_sent - self.last_counters.bytes_sent, 0)

        down_mbps = down_delta * 8 / elapsed / 1_000_000
        up_mbps = up_delta * 8 / elapsed / 1_000_000

        self.total_down_bytes += down_delta
        self.total_up_bytes += up_delta
        self.peak_down = max(self.peak_down, down_mbps)
        self.peak_up = max(self.peak_up, up_mbps)

        self.down_history.append(down_mbps)
        self.up_history.append(up_mbps)

        if self.minimized:
            self.canvas.itemconfig(self.down_text, text=f"↓ {down_mbps:.2f}", fill=speed_color(down_mbps, DOWN_COLOR))
            self.canvas.itemconfig(self.up_text, text=f"↑ {up_mbps:.2f}", fill=speed_color(up_mbps, UP_COLOR))
        else:
            self.canvas.itemconfig(self.down_text, text=f"{down_mbps:6.2f} Mbps", fill=speed_color(down_mbps, DOWN_COLOR))
            self.canvas.itemconfig(self.up_text, text=f"{up_mbps:6.2f} Mbps", fill=speed_color(up_mbps, UP_COLOR))
            self.canvas.itemconfig(self.down_peak_text, text=f"Peak {self.peak_down:.2f}")
            self.canvas.itemconfig(self.up_peak_text, text=f"Peak {self.peak_up:.2f}")
            self.canvas.itemconfig(self.down_total_text, text=f"Total: {format_bytes(self.total_down_bytes)}")
            self.canvas.itemconfig(self.up_total_text, text=f"Total: {format_bytes(self.total_up_bytes)}")

            self._draw_sparkline("down_graph", self.down_history,
                                  self.down_graph_x0, self.graph_y0, self.down_graph_x1, self.graph_y1, DOWN_COLOR)
            self._draw_sparkline("up_graph", self.up_history,
                                  self.up_graph_x0, self.graph_y0, self.up_graph_x1, self.graph_y1, UP_COLOR)

        self.last_counters = current
        self.last_time = now
        self.root.after(UPDATE_MS, self.update_speed)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = NetMonitor()
    app.run()
