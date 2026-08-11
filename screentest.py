#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScreenTest Desktop - 屏幕测试工具
参考 https://screentest.cc/ 实现的本地桌面版

功能：
  - 坏点/亮点检测（纯色全屏）
  - 自定义纯色显示
  - 灰度与亮度测试
  - 渐变与色带测试
  - 网格/棋盘/彩条等图案
  - 屏保特效（暗屏、弹跳 Logo、矩阵雨）
  - 纯色图片导出
"""

from __future__ import annotations

import random
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Callable, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    print("请先安装 Pillow: pip install pillow")
    sys.exit(1)


APP_TITLE = "ScreenTest - 屏幕测试工具"
APP_VERSION = "1.2.5"
SITE_URL = "https://www.xiaopengking.site"
SITE_DISPLAY = "xiaopengking.site"


def setup_dpi_awareness() -> None:
    """在创建任何窗口前启用 Per-Monitor DPI，保证分辨率/坐标正确。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 多显示器枚举（Windows）
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Monitor:
    """一块物理显示器：虚拟桌面坐标 + 真实分辨率。"""

    index: int
    x: int
    y: int
    width: int          # 用于铺窗的矩形宽（物理像素）
    height: int         # 用于铺窗的矩形高（物理像素）
    primary: bool
    name: str = ""
    mode_width: int = 0   # EnumDisplaySettings 真实模式宽
    mode_height: int = 0  # EnumDisplaySettings 真实模式高
    dpi: int = 96
    refresh_hz: int = 0

    @property
    def display_width(self) -> int:
        return self.mode_width or self.width

    @property
    def display_height(self) -> int:
        return self.mode_height or self.height

    @property
    def scale_percent(self) -> int:
        return int(round(self.dpi / 96 * 100))

    @property
    def label(self) -> str:
        tag = "主屏" if self.primary else "外接"
        name = f" · {self.name}" if self.name else ""
        scale = f" · 缩放{self.scale_percent}%" if self.dpi and self.dpi != 96 else ""
        hz = f" · {self.refresh_hz}Hz" if self.refresh_hz else ""
        return (
            f"显示器 {self.index + 1}（{tag}）"
            f"{self.display_width}×{self.display_height}{hz}{scale}{name}"
        )


def enumerate_monitors() -> List[Monitor]:
    """枚举所有显示器。Windows 用 Win32 API；其他平台回退为单屏。"""
    if sys.platform == "win32":
        try:
            return _enumerate_monitors_win32()
        except Exception:
            pass

    root = tk._default_root
    if root is not None:
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    else:
        w, h = 1920, 1080
    return [Monitor(0, 0, 0, w, h, True, mode_width=w, mode_height=h)]


def _enumerate_monitors_win32() -> List[Monitor]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    shcore = ctypes.windll.shcore

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", wintypes.DWORD),
            ("szDevice", wintypes.WCHAR * 32),
        ]

    # DEVMODEW：用明确字段布局读取 dmPelsWidth/Height/Position/Frequency
    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", wintypes.WCHAR * 32),
            ("dmSpecVersion", wintypes.WORD),
            ("dmDriverVersion", wintypes.WORD),
            ("dmSize", wintypes.WORD),
            ("dmDriverExtra", wintypes.WORD),
            ("dmFields", wintypes.DWORD),
            ("dmPosition_x", ctypes.c_long),
            ("dmPosition_y", ctypes.c_long),
            ("dmDisplayOrientation", wintypes.DWORD),
            ("dmDisplayFixedOutput", wintypes.DWORD),
            ("dmColor", wintypes.SHORT),
            ("dmDuplex", wintypes.SHORT),
            ("dmYResolution", wintypes.SHORT),
            ("dmTTOption", wintypes.SHORT),
            ("dmCollate", wintypes.SHORT),
            ("dmFormName", wintypes.WCHAR * 32),
            ("dmLogPixels", wintypes.WORD),
            ("dmBitsPerPel", wintypes.DWORD),
            ("dmPelsWidth", wintypes.DWORD),
            ("dmPelsHeight", wintypes.DWORD),
            ("dmDisplayFlags", wintypes.DWORD),
            ("dmDisplayFrequency", wintypes.DWORD),
            ("dmICMMethod", wintypes.DWORD),
            ("dmICMIntent", wintypes.DWORD),
            ("dmMediaType", wintypes.DWORD),
            ("dmDitherType", wintypes.DWORD),
            ("dmReserved1", wintypes.DWORD),
            ("dmReserved2", wintypes.DWORD),
            ("dmPanningWidth", wintypes.DWORD),
            ("dmPanningHeight", wintypes.DWORD),
        ]

    MONITORINFOF_PRIMARY = 0x00000001
    ENUM_CURRENT_SETTINGS = -1
    raw: List[tuple] = []

    def _callback(hmonitor, hdc, lprect, lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if not user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            return 1

        r = info.rcMonitor
        device = info.szDevice
        x, y = int(r.left), int(r.top)
        rw, rh = int(r.right - r.left), int(r.bottom - r.top)
        primary = bool(info.dwFlags & MONITORINFOF_PRIMARY)

        # 真实分辨率（不受 DPI 缩放影响）
        mode_w, mode_h, hz = rw, rh, 0
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if user32.EnumDisplaySettingsW(device, ENUM_CURRENT_SETTINGS, ctypes.byref(dm)):
            if dm.dmPelsWidth and dm.dmPelsHeight:
                mode_w, mode_h = int(dm.dmPelsWidth), int(dm.dmPelsHeight)
            hz = int(dm.dmDisplayFrequency or 0)
            # 位置以当前显示模式为准更可靠
            if dm.dmFields & 0x00000020:  # DM_POSITION
                x, y = int(dm.dmPosition_x), int(dm.dmPosition_y)

        dpi = 96
        try:
            dx = ctypes.c_uint(96)
            dy = ctypes.c_uint(96)
            # MDT_EFFECTIVE_DPI = 0
            shcore.GetDpiForMonitor(hmonitor, 0, ctypes.byref(dx), ctypes.byref(dy))
            dpi = int(dx.value or 96)
        except Exception:
            pass

        # 铺窗矩形：优先用 GetMonitorInfo 的 rcMonitor（与虚拟桌面一致）
        # 宽高若与真实模式不一致（旧 DPI 感知），改用真实模式尺寸
        width, height = rw, rh
        if abs(rw - mode_w) > 2 or abs(rh - mode_h) > 2:
            # 在 Per-Monitor DPI 下 rc 应已是物理像素；若仍不一致则用 mode
            width, height = mode_w, mode_h

        raw.append((x, y, width, height, primary, device, mode_w, mode_h, dpi, hz))
        return 1

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(RECT),
        wintypes.LPARAM,
    )
    cb = MonitorEnumProc(_callback)
    if not user32.EnumDisplayMonitors(0, 0, cb, 0):
        raise OSError("EnumDisplayMonitors failed")

    raw.sort(key=lambda m: (not m[4], m[0], m[1]))
    monitors: List[Monitor] = []
    for i, (x, y, w, h, primary, device, mw, mh, dpi, hz) in enumerate(raw):
        short = (device or "").replace("\\\\.\\", "")
        monitors.append(
            Monitor(
                index=i,
                x=x,
                y=y,
                width=w,
                height=h,
                primary=primary,
                name=short,
                mode_width=mw,
                mode_height=mh,
                dpi=dpi,
                refresh_hz=hz,
            )
        )
    if not monitors:
        raise OSError("no monitors")
    return monitors


def win32_set_window_rect(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """用 SetWindowPos 精确铺满目标显示器，避免 Tk geometry 在多 DPI 下偏移。"""
    if sys.platform != "win32" or not hwnd:
        return
    import ctypes

    HWND_TOPMOST = -1
    SWP_SHOWWINDOW = 0x0040
    ctypes.windll.user32.SetWindowPos(
        int(hwnd), HWND_TOPMOST, int(x), int(y), int(w), int(h), SWP_SHOWWINDOW
    )

# 预设纯色 (名称, RGB)
SOLID_COLORS: List[Tuple[str, Tuple[int, int, int]]] = [
    ("黑色", (0, 0, 0)),
    ("白色", (255, 255, 255)),
    ("红色", (255, 0, 0)),
    ("绿色", (0, 255, 0)),
    ("蓝色", (0, 0, 255)),
    ("青色", (0, 255, 255)),
    ("品红", (255, 0, 255)),
    ("黄色", (255, 255, 0)),
    ("灰色 50%", (128, 128, 128)),
    ("深灰 25%", (64, 64, 64)),
    ("浅灰 75%", (192, 192, 192)),
    ("橙色", (255, 128, 0)),
    ("紫色", (128, 0, 255)),
    ("粉色", (255, 105, 180)),
]

GRAY_LEVELS = [0, 16, 32, 48, 64, 96, 128, 160, 192, 224, 240, 255]


# ---------------------------------------------------------------------------
# 全屏测试窗口
# ---------------------------------------------------------------------------
class FullscreenTest(tk.Toplevel):
    """全屏测试画布：纯色、图案、渐变、特效。支持指定显示器。"""

    def __init__(
        self,
        master: tk.Tk,
        mode: str,
        colors: Optional[List[Tuple[int, int, int]]] = None,
        auto_interval: float = 0,
        custom_color: Optional[Tuple[int, int, int]] = None,
        gray_level: Optional[int] = None,
        pattern: str = "solid",
        effect: str = "",
        monitor: Optional[Monitor] = None,
    ):
        super().__init__(master)
        self.mode = mode
        self.colors = colors or [(0, 0, 0)]
        self.auto_interval = auto_interval
        self.custom_color = custom_color
        self.gray_level = gray_level
        self.pattern = pattern
        self.effect = effect
        self.monitor = monitor
        self.master_app = master

        self.index = 0
        self.running = True
        self._photo = None
        self._anim_id = None
        self._auto_id = None
        self._render_job = None
        self._effect_state = {}
        self._hint_hide_id = None
        self._last_size = (0, 0)
        self._rendering = False
        self._solid_only = mode in ("solid", "dead_pixel", "gray", "custom")

        self.configure(bg="black", cursor="none")
        # 无边框；不用 -fullscreen（只会落到主屏且与多 DPI 冲突）
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            self, highlightthickness=0, bg="black", cursor="none", bd=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        mon_tip = ""
        if self.monitor:
            mon_tip = (
                f"  |  显示器 {self.monitor.index + 1} "
                f"{self.monitor.display_width}×{self.monitor.display_height}"
            )
        self.hint = tk.Label(
            self,
            text=f"Esc 退出  |  空格/点击 下一页  |  ← → 切换  |  A 自动循环{mon_tip}",
            font=("Microsoft YaHei UI", 11),
            fg="#ffffff",
            bg="#000000",
        )
        self.hint.place(relx=0.5, rely=0.97, anchor="s")
        self._hint_hide_id = self.after(3500, self._hide_hint)

        # 键鼠只绑一次：原先窗口+画布各绑一遍，点击会冒泡触发两次 → 序号变成 1/3/5/7
        self._nav_lock_until = 0.0
        self.bind("<Escape>", self._on_escape)
        self.bind("<F11>", self._on_escape)
        self.bind("<space>", self._on_next)
        self.bind("<Right>", self._on_next)
        self.bind("<Left>", self._on_prev)
        self.bind("<a>", self._on_toggle_auto)
        self.bind("<A>", self._on_toggle_auto)
        self.canvas.bind("<Button-1>", self._on_next)
        self.canvas.bind("<Button-3>", self._on_prev)
        self.canvas.bind("<Escape>", self._on_escape)
        # 画布获得焦点时也能用键盘
        self.canvas.bind("<space>", self._on_next)
        self.canvas.bind("<Right>", self._on_next)
        self.canvas.bind("<Left>", self._on_prev)
        self.canvas.bind("<a>", self._on_toggle_auto)
        self.canvas.bind("<A>", self._on_toggle_auto)
        self.protocol("WM_DELETE_WINDOW", self.close)
        # 注意：不要在 Configure 里无条件 re-render，否则会与改尺寸互相触发卡死

        # 先定位再绘制；不用 grab_set（外接屏焦点异常时会锁死整个程序）
        self.update_idletasks()
        self._apply_monitor_geometry()
        self.lift()
        self.focus_force()
        # 全局 Esc 兜底，避免焦点不在测试窗时无法退出
        self.master_app.bind_all("<Escape>", self._on_escape, add="+")

        self.after(20, self._ensure_focus)
        self.after(40, self._safe_render)

        if self.auto_interval > 0:
            self._schedule_auto()

    def _on_escape(self, event=None):
        # 一次 Esc 退出全部叠开的测试窗，而不是只关最上层
        try:
            if hasattr(self.master_app, "close_all_tests"):
                self.master_app.close_all_tests()
            else:
                self.close()
        except Exception:
            self.close()
        return "break"

    def _nav_allowed(self) -> bool:
        """防止同一操作被绑定/冒泡处理两次。"""
        now = time.monotonic()
        if now < self._nav_lock_until:
            return False
        self._nav_lock_until = now + 0.12
        return True

    def _on_next(self, event=None):
        if self._nav_allowed():
            self.next_item()
        return "break"

    def _on_prev(self, event=None):
        if self._nav_allowed():
            self.prev_item()
        return "break"

    def _on_toggle_auto(self, event=None):
        if self._nav_allowed():
            self.toggle_auto()
        return "break"

    def _target_size(self) -> Tuple[int, int]:
        if self.monitor is not None:
            return max(1, self.monitor.width), max(1, self.monitor.height)
        try:
            w = max(self.winfo_width(), 1)
            h = max(self.winfo_height(), 1)
            if w < 50 or h < 50:
                return self.winfo_screenwidth(), self.winfo_screenheight()
            return w, h
        except tk.TclError:
            return 1920, 1080

    def _apply_monitor_geometry(self):
        """把无边框窗口铺满指定显示器（支持外接屏 / 多 DPI）。"""
        if self.monitor is not None:
            m = self.monitor
            x, y, w, h = m.x, m.y, m.width, m.height
        else:
            x = y = 0
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight()

        # Tk geometry 先设一遍
        try:
            self.geometry(f"{w}x{h}+{x}+{y}")
        except tk.TclError:
            pass
        self.update_idletasks()

        # Win32 再强制一次，避免 DPI 缩放导致位置/尺寸错误
        try:
            self.update()
            if sys.platform == "win32":
                import ctypes

                user32 = ctypes.windll.user32
                GA_ROOT = 2
                hwnd = int(self.winfo_id())
                root_hwnd = user32.GetAncestor(hwnd, GA_ROOT) or hwnd
                win32_set_window_rect(int(root_hwnd), x, y, w, h)
        except Exception:
            pass
        self._last_size = (w, h)

    def _ensure_focus(self):
        if not self.running:
            return
        try:
            self.lift()
            self.focus_force()
            self.canvas.focus_set()
        except tk.TclError:
            pass

    def _hide_hint(self):
        try:
            self.hint.place_forget()
        except tk.TclError:
            pass

    def _show_hint(self, text: str, ms: int = 2000):
        try:
            self.hint.config(text=text)
            self.hint.place(relx=0.5, rely=0.97, anchor="s")
        except tk.TclError:
            return
        if self._hint_hide_id:
            try:
                self.after_cancel(self._hint_hide_id)
            except Exception:
                pass
        self._hint_hide_id = self.after(ms, self._hide_hint)

    def _safe_render(self):
        if not self.running:
            return
        try:
            self.render()
        except Exception as exc:
            # 渲染异常不应卡死进程
            try:
                self._show_hint(f"渲染错误: {exc}", 5000)
            except Exception:
                pass

    def close(self):
        if not self.running:
            return
        self.running = False
        for job in (self._anim_id, self._auto_id, self._render_job, self._hint_hide_id):
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
        self._anim_id = self._auto_id = self._render_job = None
        # 从主程序注销
        try:
            if getattr(self.master_app, "_active_test", None) is self:
                self.master_app._active_test = None
        except Exception:
            pass
        try:
            self.destroy()
        except tk.TclError:
            pass

    def toggle_auto(self):
        if self.auto_interval > 0:
            self.auto_interval = 0
            if self._auto_id:
                try:
                    self.after_cancel(self._auto_id)
                except Exception:
                    pass
                self._auto_id = None
            self._show_hint("自动循环：关")
        else:
            self.auto_interval = 2.0
            self._schedule_auto()
            self._show_hint("自动循环：开（每 2 秒）")

    def _schedule_auto(self):
        if not self.running or self.auto_interval <= 0:
            return
        self._auto_id = self.after(int(self.auto_interval * 1000), self._auto_tick)

    def _auto_tick(self):
        if not self.running:
            return
        self.next_item()
        self._schedule_auto()

    def next_item(self):
        if self.mode in ("solid", "dead_pixel", "gray"):
            self.index = (self.index + 1) % max(1, self._item_count())
            self.render()
        elif self.mode == "pattern":
            patterns = self._pattern_list()
            idx = patterns.index(self.pattern) if self.pattern in patterns else 0
            self.pattern = patterns[(idx + 1) % len(patterns)]
            self.render()

    def prev_item(self):
        if self.mode in ("solid", "dead_pixel", "gray"):
            n = max(1, self._item_count())
            self.index = (self.index - 1) % n
            self.render()
        elif self.mode == "pattern":
            patterns = self._pattern_list()
            idx = patterns.index(self.pattern) if self.pattern in patterns else 0
            self.pattern = patterns[(idx - 1) % len(patterns)]
            self.render()

    def _item_count(self) -> int:
        if self.mode == "gray":
            return len(GRAY_LEVELS)
        if self.mode in ("solid", "dead_pixel"):
            return len(self.colors)
        return 1

    def _pattern_list(self) -> List[str]:
        return [
            "checker",
            "grid",
            "hline",
            "vline",
            "crosshatch",
            "colorbars",
            "gradient_h",
            "gradient_v",
            "gradient_gray",
            "dots",
            "text_focus",
        ]

    def render(self):
        if not self.running or self._rendering:
            return
        self._rendering = True
        try:
            w, h = self._target_size()
            if w < 10 or h < 10:
                return

            # 纯色模式：只改背景色，绝不改 canvas 尺寸，避免 Configure 死循环
            if self.mode == "effect":
                self.canvas.delete("all")
                self._start_effect(w, h)
                return

            if self.mode == "custom":
                color = self.custom_color or (0, 0, 0)
                self._fill_solid(w, h, color)
                return

            if self.mode == "gray":
                g = GRAY_LEVELS[self.index % len(GRAY_LEVELS)]
                self._fill_solid(w, h, (g, g, g))
                self._draw_label(f"灰度 {g}/255", w, h)
                return

            if self.mode in ("solid", "dead_pixel"):
                color = self.colors[self.index % len(self.colors)]
                name = self._color_name(color)
                self._fill_solid(w, h, color)
                self._draw_label(
                    f"{name}  ({self.index + 1}/{len(self.colors)})", w, h
                )
                return

            if self.mode == "pattern":
                self.canvas.delete("all")
                self._draw_pattern(w, h, self.pattern)
                return

            self._fill_solid(w, h, (0, 0, 0))
        finally:
            self._rendering = False

    def _color_name(self, rgb: Tuple[int, int, int]) -> str:
        for name, c in SOLID_COLORS:
            if c == rgb:
                return name
        return f"RGB{rgb}"

    def _rgb(self, color: Tuple[int, int, int]) -> str:
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"

    def _fill_solid(self, w: int, h: int, color: Tuple[int, int, int]):
        """纯色填充：仅设置背景，不创建海量图元，不改控件尺寸。"""
        hexc = self._rgb(color)
        try:
            self.configure(bg=hexc)
            self.canvas.delete("all")
            self.canvas.configure(bg=hexc)
        except tk.TclError:
            return
        lum = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
        fg = "#000000" if lum > 140 else "#ffffff"
        try:
            self.hint.config(fg=fg, bg=hexc)
        except tk.TclError:
            pass

    def _draw_label(self, text: str, w: int, h: int):
        # 角落小标签（仅一个 text 图元）
        bg = self.canvas["bg"]
        try:
            r = int(bg[1:3], 16)
            g = int(bg[3:5], 16)
            b = int(bg[5:7], 16)
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            fg = "#000000" if lum > 140 else "#ffffff"
        except Exception:
            fg = "#ffffff"
        self.canvas.create_text(
            20, 20, text=text, anchor="nw", fill=fg,
            font=("Microsoft YaHei UI", 14, "bold"), tags=("label",),
        )

    def _draw_pattern(self, w: int, h: int, name: str):
        self.canvas.config(bg="black")
        self.hint.config(fg="#ffffff", bg="#000000")

        if name == "checker":
            # 用图片生成棋盘，避免 4K 下数千个矩形卡死
            cell = 40
            cw = max(1, (w + cell - 1) // cell)
            ch = max(1, (h + cell - 1) // cell)
            small = Image.new("RGB", (cw, ch))
            px = small.load()
            for j in range(ch):
                for i in range(cw):
                    px[i, j] = (255, 255, 255) if (i + j) % 2 == 0 else (0, 0, 0)
            img = small.resize((w, h), Image.NEAREST)
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
            self._draw_label("棋盘格 (几何/清晰度)", w, h)

        elif name == "grid":
            step = 50
            for x in range(0, w, step):
                self.canvas.create_line(x, 0, x, h, fill="#00ff00", width=1)
            for y in range(0, h, step):
                self.canvas.create_line(0, y, w, y, fill="#00ff00", width=1)
            # 中心十字
            self.canvas.create_line(w // 2, 0, w // 2, h, fill="#ff0000", width=2)
            self.canvas.create_line(0, h // 2, w, h // 2, fill="#ff0000", width=2)
            self._draw_label("网格 (几何/对齐)", w, h)

        elif name == "hline":
            # 逐行生成 1px 黑白水平细线（勿用 1×2 小图拉伸：高 DPI 下会变成上下两大块+左右黑边）
            self._show_line_pattern(w, h, horizontal=True)
            self._draw_label("水平线 (1px 黑白交替)", w, h)

        elif name == "vline":
            # 逐列生成 1px 黑白垂直细线
            self._show_line_pattern(w, h, horizontal=False)
            self._draw_label("垂直线 (1px 黑白交替)", w, h)

        elif name == "crosshatch":
            for i in range(-h, w, 20):
                self.canvas.create_line(i, 0, i + h, h, fill="#888888")
                self.canvas.create_line(i, h, i + h, 0, fill="#888888")
            self._draw_label("交叉线", w, h)

        elif name == "colorbars":
            bars = [
                (255, 255, 255),
                (255, 255, 0),
                (0, 255, 255),
                (0, 255, 0),
                (255, 0, 255),
                (255, 0, 0),
                (0, 0, 255),
                (0, 0, 0),
            ]
            bw = w // len(bars)
            for i, c in enumerate(bars):
                hexc = self._rgb(c)
                self.canvas.create_rectangle(
                    i * bw, 0, (i + 1) * bw if i < len(bars) - 1 else w, h,
                    fill=hexc, outline=hexc,
                )
            self._draw_label("彩条 (SMPTE 风格)", w, h)

        elif name in ("gradient_h", "gradient_v", "gradient_gray"):
            self._draw_gradient_image(w, h, name)
            labels = {
                "gradient_h": "水平 RGB 渐变 (色带/色阶)",
                "gradient_v": "垂直 RGB 渐变",
                "gradient_gray": "灰度渐变 (色带/伽马)",
            }
            self._draw_label(labels.get(name, name), w, h)

        elif name == "dots":
            step = 30
            img = Image.new("RGB", (w, h), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            r = 3
            for y in range(step // 2, h, step):
                for x in range(step // 2, w, step):
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255))
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
            self._draw_label("点阵", w, h)

        elif name == "text_focus":
            self.canvas.config(bg="white")
            self.hint.config(fg="#000000", bg="#ffffff")
            sample = (
                "Aa Bb Cc  清晰度测试  The quick brown fox jumps over the lazy dog\n"
                "0123456789  !@#$%^&*()  中文测试：永和九年岁在癸丑\n"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ  abcdefghijklmnopqrstuvwxyz"
            )
            sizes = [10, 12, 14, 16, 20, 24, 32, 48]
            y = 40
            for s in sizes:
                self.canvas.create_text(
                    w // 2, y, text=sample.split("\n")[0],
                    fill="black", font=("Consolas", s),
                    anchor="n",
                )
                y += s + 18
            self.canvas.create_text(
                w // 2, h - 80,
                text="文字清晰度 / 锐度测试",
                fill="#333333", font=("Microsoft YaHei UI", 18),
            )

        else:
            self._fill_solid(w, h, (0, 0, 0))

    def _show_line_pattern(self, w: int, h: int, horizontal: bool) -> None:
        """
        1px 黑白交替细线。
        使用全尺寸位图按行/列填充（不用 1×2 小图拉伸，避免高 DPI 下变成
        「上下两大块 + 左右黑边」）。
        """
        w, h = max(1, int(w)), max(1, int(h))
        try:
            cw = int(self.winfo_width() or 0)
            ch = int(self.winfo_height() or 0)
            if cw >= 50 and ch >= 50:
                w, h = cw, ch
        except tk.TclError:
            pass

        self.configure(bg="black")
        self.canvas.configure(bg="black")

        if horizontal:
            row_w = bytes((255, 255, 255)) * w
            row_b = bytes((0, 0, 0)) * w
            buf = bytearray()
            for y in range(h):
                buf += row_w if (y & 1) == 0 else row_b
            img = Image.frombytes("RGB", (w, h), bytes(buf))
        else:
            pair = bytes((255, 255, 255, 0, 0, 0))
            row = pair * (w // 2) + (bytes((255, 255, 255)) if (w & 1) else b"")
            img = Image.frombytes("RGB", (w, h), row * h)

        # 禁止 PhotoImage 再做额外缩放
        self._photo = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo, tags=("pattern",))

    def _draw_gradient_image(self, w: int, h: int, kind: str):
        """快速渐变：先做 1 行/列再缩放，避免 4K 逐像素卡死。"""
        w, h = max(1, w), max(1, h)
        if kind == "gradient_gray":
            strip = Image.new("RGB", (256, 1))
            px = strip.load()
            for x in range(256):
                px[x, 0] = (x, x, x)
            img = strip.resize((w, h), Image.BILINEAR)
        elif kind == "gradient_h":
            strip = Image.new("RGB", (768, 1))
            px = strip.load()
            for x in range(768):
                if x < 256:
                    t = x / 255
                    c = (255, int(255 * t), 0)
                elif x < 512:
                    t = (x - 256) / 255
                    c = (int(255 * (1 - t)), 255, int(255 * t))
                else:
                    t = (x - 512) / 255
                    c = (0, int(255 * (1 - t)), 255)
                px[x, 0] = c
            img = strip.resize((w, h), Image.BILINEAR)
        else:  # gradient_v
            strip = Image.new("RGB", (1, 256))
            px = strip.load()
            for y in range(256):
                t = y / 255
                r = int(255 * (1 - t))
                g = int(255 * abs(0.5 - t) * 2)
                b = int(255 * t)
                px[0, y] = (r, g, b)
            img = strip.resize((w, h), Image.BILINEAR)

        self._photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

    # ---- 特效 ----
    def _start_effect(self, w: int, h: int):
        if self._anim_id:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

        if self.effect == "dim":
            self._fill_solid(w, h, (0, 0, 0))
            self.hint.config(fg="#333333", bg="#000000")
            self._draw_label("暗屏屏保（Esc 退出）", w, h)
            return

        if self.effect == "bouncing":
            self._effect_state = {
                "x": w // 4,
                "y": h // 4,
                "dx": 4,
                "dy": 3,
                "color_i": 0,
                "w": w,
                "h": h,
            }
            self._anim_bounce()
            return

        if self.effect == "matrix":
            cols = w // 16
            self._effect_state = {
                "drops": [random.randint(0, h // 16) for _ in range(cols)],
                "w": w,
                "h": h,
                "cols": cols,
            }
            self.canvas.config(bg="#000000")
            self._anim_matrix()
            return

        if self.effect == "noise":
            self._effect_state = {"w": w, "h": h, "frame": 0}
            self._anim_noise()
            return

        self._fill_solid(w, h, (0, 0, 0))

    def _anim_bounce(self):
        if not self.running or self.effect != "bouncing":
            return
        st = self._effect_state
        w, h = st["w"], st["h"]
        self.canvas.delete("all")
        self.canvas.config(bg="#111111")

        colors = ["#ff0000", "#00ff00", "#00aaff", "#ffaa00", "#ff00ff", "#ffffff"]
        text = "ScreenTest"
        # 简单估算文字尺寸
        tw, th = 180, 40
        st["x"] += st["dx"]
        st["y"] += st["dy"]
        if st["x"] <= 0 or st["x"] + tw >= w:
            st["dx"] *= -1
            st["color_i"] = (st["color_i"] + 1) % len(colors)
            st["x"] = max(0, min(st["x"], w - tw))
        if st["y"] <= 0 or st["y"] + th >= h:
            st["dy"] *= -1
            st["color_i"] = (st["color_i"] + 1) % len(colors)
            st["y"] = max(0, min(st["y"], h - th))

        self.canvas.create_text(
            st["x"] + tw // 2, st["y"] + th // 2,
            text=text, fill=colors[st["color_i"]],
            font=("Segoe UI", 28, "bold"),
        )
        self._anim_id = self.after(16, self._anim_bounce)

    def _anim_matrix(self):
        if not self.running or self.effect != "matrix":
            return
        st = self._effect_state
        w, h, cols = st["w"], st["h"], st["cols"]
        # 半透明拖尾：叠一层半透明黑
        self.canvas.create_rectangle(0, 0, w, h, fill="#000000", stipple="gray50", outline="")
        chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ01アイウエオﾊﾋﾌﾍﾎ"
        font = ("Consolas", 12)
        for i, drop in enumerate(st["drops"]):
            x = i * 16
            y = drop * 16
            ch = random.choice(chars)
            self.canvas.create_text(x, y, text=ch, fill="#00ff66", font=font, anchor="nw")
            if y > h and random.random() > 0.975:
                st["drops"][i] = 0
            else:
                st["drops"][i] = drop + 1
        self._anim_id = self.after(50, self._anim_matrix)

    def _anim_noise(self):
        if not self.running or self.effect != "noise":
            return
        st = self._effect_state
        w, h = st["w"], st["h"]
        # 极小分辨率随机噪声再放大，避免 4K 下卡死
        sw, sh = 160, 90
        raw = bytes(random.getrandbits(8) for _ in range(sw * sh))
        img = Image.frombytes("L", (sw, sh), raw).convert("RGB")
        img = img.resize((w, h), Image.NEAREST)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        st["frame"] += 1
        self._anim_id = self.after(50, self._anim_noise)


# ---------------------------------------------------------------------------
# 主应用
# ---------------------------------------------------------------------------
class ScreenTestApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("920x720")
        self.minsize(800, 600)
        self.configure(bg="#0f1115")

        self.custom_color = (255, 255, 255)
        self.auto_interval = tk.DoubleVar(value=0)
        self.export_w = tk.IntVar(value=1920)
        self.export_h = tk.IntVar(value=1080)
        self.monitors: List[Monitor] = []
        self.monitor_var = tk.StringVar(value="")
        # 同时只允许一个全屏测试；切换颜色时先关旧窗，避免 Esc 要按多次
        self._active_test: Optional["FullscreenTest"] = None
        # 可滚动标签页区域：(shell, canvas)，供全局滚轮路由
        self._scroll_regions: List[Tuple[tk.Widget, tk.Canvas]] = []

        self._setup_style()
        self._build_ui()
        self._refresh_monitors()
        self._center_window()
        # 全局滚轮：指针落在哪个滚动区就滚哪个
        self.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#0f1115"
        card = "#1a1d24"
        accent = "#3b82f6"
        text = "#e8eaed"
        muted = "#9aa0a6"

        style.configure(".", background=bg, foreground=text, fieldbackground=card)
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card)
        style.configure("TLabel", background=bg, foreground=text, font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", background=bg, foreground=text,
                        font=("Microsoft YaHei UI", 20, "bold"))
        style.configure("Sub.TLabel", background=bg, foreground=muted,
                        font=("Microsoft YaHei UI", 9))
        style.configure("Card.TLabel", background=card, foreground=text,
                        font=("Microsoft YaHei UI", 10))
        style.configure("CardTitle.TLabel", background=card, foreground=text,
                        font=("Microsoft YaHei UI", 12, "bold"))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=card, foreground=text,
                        padding=[16, 8], font=("Microsoft YaHei UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", accent)],
                  foreground=[("selected", "#ffffff")])
        style.configure("TLabelframe", background=card, foreground=text)
        style.configure("TLabelframe.Label", background=card, foreground=text,
                        font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TSpinbox", fieldbackground=card, foreground=text)
        style.configure("TEntry", fieldbackground=card, foreground=text)
        style.configure("Horizontal.TScale", background=bg)

    def _center_window(self):
        self.update_idletasks()
        w, h = 920, 680
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        # 顶栏
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill=tk.X, padx=24, pady=(20, 8))

        ttk.Label(header, text="ScreenTest", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            header,
            text="  本地屏幕测试 · 坏点 · 色彩 · 屏保 · 纯色导出",
            style="Sub.TLabel",
        ).pack(side=tk.LEFT, pady=(8, 0))

        ttk.Label(
            header,
            text=f"v{APP_VERSION}",
            style="Sub.TLabel",
        ).pack(side=tk.RIGHT, pady=(8, 0))

        # 快捷说明
        tip = ttk.Label(
            self,
            text="提示：进入全屏后按 Esc 退出 · 空格/左键下一页 · 右键/← 上一页 · A 开关自动循环",
            style="Sub.TLabel",
        )
        tip.pack(fill=tk.X, padx=24, pady=(0, 8))

        # 目标显示器选择（多屏核心）
        mon_bar = tk.Frame(self, bg="#1a1d24", highlightthickness=0)
        mon_bar.pack(fill=tk.X, padx=24, pady=(0, 12))
        mon_inner = tk.Frame(mon_bar, bg="#1a1d24")
        mon_inner.pack(fill=tk.X, padx=14, pady=10)

        tk.Label(
            mon_inner, text="测试目标显示器",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 10, "bold"),
        ).pack(side=tk.LEFT)

        self.monitor_combo = ttk.Combobox(
            mon_inner, textvariable=self.monitor_var, state="readonly", width=48,
            font=("Microsoft YaHei UI", 10),
        )
        self.monitor_combo.pack(side=tk.LEFT, padx=12)

        tk.Button(
            mon_inner, text="刷新", command=self._refresh_monitors,
            bg="#2d3340", fg="#e8eaed", relief="flat", padx=10, pady=4,
            font=("Microsoft YaHei UI", 9), cursor="hand2",
            activebackground="#3b82f6", activeforeground="white",
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            mon_inner, text="识别显示器", command=self._identify_monitors,
            bg="#3b82f6", fg="white", relief="flat", padx=12, pady=4,
            font=("Microsoft YaHei UI", 9, "bold"), cursor="hand2",
            activebackground="#2563eb", activeforeground="white",
        ).pack(side=tk.LEFT, padx=4)

        tk.Label(
            mon_inner, text="外接屏请在此选择后再开始测试",
            bg="#1a1d24", fg="#9aa0a6",
            font=("Microsoft YaHei UI", 9),
        ).pack(side=tk.LEFT, padx=10)

        # 选项卡
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))

        self.tab_dead = ttk.Frame(nb, style="TFrame")
        self.tab_color = ttk.Frame(nb, style="TFrame")
        self.tab_pattern = ttk.Frame(nb, style="TFrame")
        self.tab_effect = ttk.Frame(nb, style="TFrame")
        self.tab_export = ttk.Frame(nb, style="TFrame")

        nb.add(self.tab_dead, text="  坏点检测  ")
        nb.add(self.tab_color, text="  纯色 / 灰度  ")
        nb.add(self.tab_pattern, text="  图案测试  ")
        nb.add(self.tab_effect, text="  屏保特效  ")
        nb.add(self.tab_export, text="  纯色图片  ")

        self._build_dead_tab()
        self._build_color_tab()
        self._build_pattern_tab()
        self._build_effect_tab()
        self._build_export_tab()

        # 底部
        footer = ttk.Frame(self, style="TFrame")
        footer.pack(fill=tk.X, padx=24, pady=(0, 16))
        foot_left = ttk.Frame(footer, style="TFrame")
        foot_left.pack(side=tk.LEFT)
        ttk.Label(foot_left, text="个人网站：", style="Sub.TLabel").pack(side=tk.LEFT)
        site_lbl = tk.Label(
            foot_left,
            text=SITE_DISPLAY,
            bg="#0f1115",
            fg="#3b82f6",
            cursor="hand2",
            font=("Microsoft YaHei UI", 9, "underline"),
        )
        site_lbl.pack(side=tk.LEFT)
        site_lbl.bind("<Button-1>", lambda e: self._open_site())
        ttk.Label(
            foot_left,
            text="  ·  本程序完全本地运行，无需联网",
            style="Sub.TLabel",
        ).pack(side=tk.LEFT)

        auto_fr = ttk.Frame(footer)
        auto_fr.pack(side=tk.RIGHT)
        ttk.Label(auto_fr, text="自动切换间隔(秒，0=手动):", style="Sub.TLabel").pack(side=tk.LEFT)
        sp = ttk.Spinbox(
            auto_fr, from_=0, to=30, increment=0.5, width=6,
            textvariable=self.auto_interval, format="%.1f",
        )
        sp.pack(side=tk.LEFT, padx=6)

    # ---- 可滚动内容区 ----
    def _widget_is_under(self, widget: Optional[tk.Widget], ancestor: tk.Widget) -> bool:
        w = widget
        while w is not None:
            if w == ancestor:
                return True
            try:
                parent_name = w.winfo_parent()
                w = w.nametowidget(parent_name) if parent_name else None
            except (tk.TclError, KeyError):
                break
        return False

    def _on_global_mousewheel(self, event):
        """指针在哪个标签页滚动区内，就滚动哪个区域。"""
        delta = int(getattr(event, "delta", 0) or 0)
        if delta == 0 or not self._scroll_regions:
            return
        try:
            x, y = self.winfo_pointerxy()
            target = self.winfo_containing(x, y)
        except tk.TclError:
            return
        if target is None:
            return
        for shell, canvas in self._scroll_regions:
            try:
                if not shell.winfo_ismapped():
                    continue
            except tk.TclError:
                continue
            if self._widget_is_under(target, shell):
                canvas.yview_scroll(int(-delta / 120), "units")
                return "break"

    def _make_scrollable_card(self, parent, bg: str = "#1a1d24") -> tk.Frame:
        """
        在标签页内创建可滚轮滚动的卡片区域。
        返回用于放置内容的 inner frame；窗口不够高时可用鼠标滚轮查看下方内容。
        """
        shell = tk.Frame(parent, bg=bg, highlightthickness=0)
        shell.pack(fill=tk.BOTH, expand=True, padx=4, pady=8)

        canvas = tk.Canvas(shell, bg=bg, highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(shell, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        card = tk.Frame(canvas, bg=bg, highlightthickness=0)
        win_id = canvas.create_window((0, 0), window=card, anchor="nw")

        def _sync_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _sync_width(event):
            # 内容区宽度跟随可视区域，避免横向裁切
            canvas.itemconfigure(win_id, width=max(1, event.width))

        card.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _sync_width)

        self._scroll_regions.append((shell, canvas))
        return card

    # ---- 坏点检测 ----
    def _build_dead_tab(self):
        fr = self.tab_dead
        card = self._make_scrollable_card(fr)

        tk.Label(
            card, text="坏点 / 亮点检测",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 6))

        tk.Label(
            card,
            text="全屏依次显示纯色背景，仔细观察是否有固定颜色的异常像素点。\n"
                 "黑色上找亮点 · 白色上找黑点 · RGB 上找卡死子像素。",
            bg="#1a1d24", fg="#9aa0a6", justify="left",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        # 颜色预览按钮
        colors_fr = tk.Frame(card, bg="#1a1d24")
        colors_fr.pack(fill=tk.X, padx=20, pady=8)

        for i, (name, rgb) in enumerate(SOLID_COLORS[:8]):
            self._color_chip(colors_fr, name, rgb, lambda c=rgb: self._start_solid([c]))

        btn_row = tk.Frame(card, bg="#1a1d24")
        btn_row.pack(fill=tk.X, padx=20, pady=20)

        self._big_btn(
            btn_row, "开始坏点检测（全色循环）",
            self._start_dead_pixel, primary=True,
        ).pack(side=tk.LEFT, padx=(0, 12))

        self._big_btn(
            btn_row, "仅 RGB + 黑白",
            lambda: self._start_solid([
                (0, 0, 0), (255, 255, 255),
                (255, 0, 0), (0, 255, 0), (0, 0, 255),
            ]),
        ).pack(side=tk.LEFT)

        tk.Label(
            card,
            text="建议：在较暗环境、屏幕干净时测试；逐页检查每个角落与边缘。",
            bg="#1a1d24", fg="#6b7280",
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", padx=20, pady=(8, 20))

    def _color_chip(self, parent, name: str, rgb: Tuple[int, int, int], cmd: Callable):
        hexc = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        border = "#3b82f6"
        outer = tk.Frame(parent, bg=border, padx=2, pady=2)
        outer.pack(side=tk.LEFT, padx=6, pady=4)
        inner = tk.Frame(outer, bg=hexc, width=72, height=56)
        inner.pack()
        inner.pack_propagate(False)
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        fg = "#000000" if lum > 140 else "#ffffff"
        lbl = tk.Label(inner, text=name, bg=hexc, fg=fg, font=("Microsoft YaHei UI", 9))
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        for w in (outer, inner, lbl):
            w.bind("<Button-1>", lambda e, c=cmd: c())
            w.configure(cursor="hand2")

    # ---- 纯色 / 灰度 ----
    def _build_color_tab(self):
        fr = self.tab_color
        card = self._make_scrollable_card(fr)

        tk.Label(
            card, text="纯色显示 & 灰度亮度",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 6))

        tk.Label(
            card,
            text="用于对比度、亮度均匀性、背光漏光（纯黑）和色彩表现评估。",
            bg="#1a1d24", fg="#9aa0a6",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        # 自定义颜色
        row = tk.Frame(card, bg="#1a1d24")
        row.pack(fill=tk.X, padx=20, pady=8)

        self.color_preview = tk.Frame(row, bg="#ffffff", width=48, height=48,
                                      highlightbackground="#3b82f6", highlightthickness=2)
        self.color_preview.pack(side=tk.LEFT, padx=(0, 12))
        self.color_preview.pack_propagate(False)

        self.color_label = tk.Label(
            row, text="自定义颜色: #FFFFFF  RGB(255,255,255)",
            bg="#1a1d24", fg="#e8eaed", font=("Microsoft YaHei UI", 10),
        )
        self.color_label.pack(side=tk.LEFT, padx=8)

        tk.Button(
            row, text="选取颜色…", command=self._pick_color,
            bg="#2d3340", fg="#e8eaed", relief="flat", padx=12, pady=6,
            font=("Microsoft YaHei UI", 10), cursor="hand2",
            activebackground="#3b82f6", activeforeground="white",
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            row, text="全屏显示此颜色", command=self._start_custom,
            bg="#3b82f6", fg="white", relief="flat", padx=14, pady=6,
            font=("Microsoft YaHei UI", 10, "bold"), cursor="hand2",
            activebackground="#2563eb", activeforeground="white",
        ).pack(side=tk.LEFT, padx=8)

        # RGB 滑条
        sliders = tk.Frame(card, bg="#1a1d24")
        sliders.pack(fill=tk.X, padx=20, pady=12)

        self.r_var = tk.IntVar(value=255)
        self.g_var = tk.IntVar(value=255)
        self.b_var = tk.IntVar(value=255)
        for label, var, color in (("R", self.r_var, "#ef4444"),
                                  ("G", self.g_var, "#22c55e"),
                                  ("B", self.b_var, "#3b82f6")):
            lf = tk.Frame(sliders, bg="#1a1d24")
            lf.pack(fill=tk.X, pady=4)
            tk.Label(lf, text=label, bg="#1a1d24", fg=color, width=3,
                     font=("Consolas", 12, "bold")).pack(side=tk.LEFT)
            sc = tk.Scale(
                lf, from_=0, to=255, orient=tk.HORIZONTAL, variable=var,
                bg="#1a1d24", fg="#e8eaed", highlightthickness=0,
                troughcolor="#2d3340", activebackground=color,
                command=lambda v: self._sync_rgb_from_sliders(),
            )
            sc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        # 灰度快捷
        tk.Label(
            card, text="灰度等级快速测试",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w", padx=20, pady=(16, 8))

        gray_fr = tk.Frame(card, bg="#1a1d24")
        gray_fr.pack(fill=tk.X, padx=20, pady=4)

        for g in GRAY_LEVELS:
            hexc = f"#{g:02x}{g:02x}{g:02x}"
            fg = "#000" if g > 140 else "#fff"
            b = tk.Button(
                gray_fr, text=str(g), bg=hexc, fg=fg, width=4, relief="flat",
                font=("Consolas", 9), cursor="hand2",
                command=lambda gv=g: self._start_gray_single(gv),
            )
            b.pack(side=tk.LEFT, padx=3, pady=4)

        tk.Button(
            card, text="开始灰度循环测试",
            command=self._start_gray_cycle,
            bg="#2d3340", fg="#e8eaed", relief="flat", padx=16, pady=8,
            font=("Microsoft YaHei UI", 10), cursor="hand2",
            activebackground="#3b82f6", activeforeground="white",
        ).pack(anchor="w", padx=20, pady=16)

        # 预设纯色网格
        tk.Label(
            card, text="预设纯色",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(anchor="w", padx=20, pady=(4, 8))

        grid = tk.Frame(card, bg="#1a1d24")
        grid.pack(fill=tk.X, padx=20, pady=(0, 20))
        for name, rgb in SOLID_COLORS:
            self._color_chip(grid, name, rgb, lambda c=rgb: self._start_solid([c]))

    # ---- 图案 ----
    def _build_pattern_tab(self):
        fr = self.tab_pattern
        card = self._make_scrollable_card(fr)

        tk.Label(
            card, text="图案与几何测试",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 6))

        tk.Label(
            card,
            text="检测几何失真、清晰度、色带（banding）、收敛与面板均匀性。",
            bg="#1a1d24", fg="#9aa0a6",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        patterns = [
            ("checker", "棋盘格", "几何与清晰度"),
            ("grid", "网格", "对齐与畸变"),
            ("hline", "水平细线", "水平解析力"),
            ("vline", "垂直细线", "垂直解析力"),
            ("crosshatch", "交叉线", "综合几何"),
            ("colorbars", "彩条", "色彩还原"),
            ("gradient_h", "水平渐变", "色带检测"),
            ("gradient_v", "垂直渐变", "垂直色阶"),
            ("gradient_gray", "灰度渐变", "伽马/色带"),
            ("dots", "点阵", "像素均匀性"),
            ("text_focus", "文字锐度", "清晰度"),
        ]

        grid = tk.Frame(card, bg="#1a1d24")
        grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)

        for i, (key, title, desc) in enumerate(patterns):
            r, c = divmod(i, 3)
            btn = tk.Frame(grid, bg="#252a34", padx=12, pady=12, cursor="hand2")
            btn.grid(row=r, column=c, padx=8, pady=8, sticky="nsew")
            tk.Label(btn, text=title, bg="#252a34", fg="#e8eaed",
                     font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w")
            tk.Label(btn, text=desc, bg="#252a34", fg="#9aa0a6",
                     font=("Microsoft YaHei UI", 9)).pack(anchor="w")
            for w in (btn, *btn.winfo_children()):
                w.bind("<Button-1>", lambda e, k=key: self._start_pattern(k))
                w.configure(cursor="hand2")

        for i in range(3):
            grid.columnconfigure(i, weight=1)

        tk.Button(
            card, text="依次浏览全部图案",
            command=lambda: self._start_pattern("checker"),
            bg="#3b82f6", fg="white", relief="flat", padx=16, pady=10,
            font=("Microsoft YaHei UI", 10, "bold"), cursor="hand2",
            activebackground="#2563eb",
        ).pack(anchor="w", padx=20, pady=16)

    # ---- 屏保特效 ----
    def _build_effect_tab(self):
        fr = self.tab_effect
        card = self._make_scrollable_card(fr)

        tk.Label(
            card, text="屏保与特效",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 6))

        tk.Label(
            card,
            text="不关显示器时降低亮度或展示动画，保护屏幕并放松眼睛。",
            bg="#1a1d24", fg="#9aa0a6",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        effects = [
            ("dim", "暗屏屏保", "全黑低干扰，适合休息"),
            ("bouncing", "弹跳 Logo", "经典弹跳文字屏保"),
            ("matrix", "矩阵雨", "绿色数字雨特效"),
            ("noise", "静态雪花", "电视雪花噪点效果"),
        ]

        for key, title, desc in effects:
            row = tk.Frame(card, bg="#252a34", cursor="hand2")
            row.pack(fill=tk.X, padx=20, pady=6)
            inner = tk.Frame(row, bg="#252a34")
            inner.pack(fill=tk.X, padx=16, pady=14)
            tk.Label(inner, text=title, bg="#252a34", fg="#e8eaed",
                     font=("Microsoft YaHei UI", 12, "bold")).pack(side=tk.LEFT)
            tk.Label(inner, text=f"  —  {desc}", bg="#252a34", fg="#9aa0a6",
                     font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
            tk.Label(inner, text="启动 ›", bg="#252a34", fg="#3b82f6",
                     font=("Microsoft YaHei UI", 10, "bold")).pack(side=tk.RIGHT)

            def make_cmd(k=key):
                return lambda e: self._start_effect(k)

            for w in (row, inner, *inner.winfo_children()):
                w.bind("<Button-1>", make_cmd())
                try:
                    w.configure(cursor="hand2")
                except tk.TclError:
                    pass

        tk.Label(
            card,
            text="OLED 用户提示：长时间显示静态高亮内容可能造成烙印，建议使用暗屏或动态特效。",
            bg="#1a1d24", fg="#6b7280",
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", padx=20, pady=20)

    # ---- 导出 ----
    def _build_export_tab(self):
        fr = self.tab_export
        card = self._make_scrollable_card(fr)

        tk.Label(
            card, text="纯色图片生成与下载",
            bg="#1a1d24", fg="#e8eaed",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 6))

        tk.Label(
            card,
            text="生成指定分辨率的纯色 PNG，可用于壁纸、设计素材或测试图。",
            bg="#1a1d24", fg="#9aa0a6",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        # 分辨率
        res_fr = tk.Frame(card, bg="#1a1d24")
        res_fr.pack(fill=tk.X, padx=20, pady=8)

        tk.Label(res_fr, text="宽度", bg="#1a1d24", fg="#e8eaed",
                 font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT)
        tk.Spinbox(
            res_fr, from_=1, to=7680, textvariable=self.export_w, width=8,
            font=("Consolas", 11), bg="#2d3340", fg="#e8eaed",
            buttonbackground="#3b82f6",
        ).pack(side=tk.LEFT, padx=8)

        tk.Label(res_fr, text="高度", bg="#1a1d24", fg="#e8eaed",
                 font=("Microsoft YaHei UI", 10)).pack(side=tk.LEFT, padx=(16, 0))
        tk.Spinbox(
            res_fr, from_=1, to=4320, textvariable=self.export_h, width=8,
            font=("Consolas", 11), bg="#2d3340", fg="#e8eaed",
            buttonbackground="#3b82f6",
        ).pack(side=tk.LEFT, padx=8)

        presets = [
            ("1080p", 1920, 1080),
            ("1440p", 2560, 1440),
            ("4K", 3840, 2160),
            ("720p", 1280, 720),
            ("正方形", 1080, 1080),
        ]
        for name, w, h in presets:
            tk.Button(
                res_fr, text=name,
                command=lambda ww=w, hh=h: (self.export_w.set(ww), self.export_h.set(hh)),
                bg="#2d3340", fg="#e8eaed", relief="flat", padx=10, pady=4,
                font=("Microsoft YaHei UI", 9), cursor="hand2",
            ).pack(side=tk.LEFT, padx=4)

        # 颜色选择
        row = tk.Frame(card, bg="#1a1d24")
        row.pack(fill=tk.X, padx=20, pady=16)

        self.export_preview = tk.Frame(
            row, bg="#ffffff", width=64, height=64,
            highlightbackground="#3b82f6", highlightthickness=2,
        )
        self.export_preview.pack(side=tk.LEFT, padx=(0, 12))

        self.export_color = (255, 255, 255)
        self.export_color_lbl = tk.Label(
            row, text="导出颜色: #FFFFFF",
            bg="#1a1d24", fg="#e8eaed", font=("Microsoft YaHei UI", 10),
        )
        self.export_color_lbl.pack(side=tk.LEFT)

        tk.Button(
            row, text="选取颜色…", command=self._pick_export_color,
            bg="#2d3340", fg="#e8eaed", relief="flat", padx=12, pady=6,
            font=("Microsoft YaHei UI", 10), cursor="hand2",
        ).pack(side=tk.LEFT, padx=12)

        # 快捷色
        quick = tk.Frame(card, bg="#1a1d24")
        quick.pack(fill=tk.X, padx=20, pady=4)
        for name, rgb in SOLID_COLORS[:8]:
            hexc = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            b = tk.Button(
                quick, text="  ", bg=hexc, width=3, relief="flat", cursor="hand2",
                command=lambda c=rgb: self._set_export_color(c),
            )
            b.pack(side=tk.LEFT, padx=3)

        tk.Button(
            card, text="生成并保存 PNG…",
            command=self._export_image,
            bg="#3b82f6", fg="white", relief="flat", padx=20, pady=12,
            font=("Microsoft YaHei UI", 11, "bold"), cursor="hand2",
            activebackground="#2563eb",
        ).pack(anchor="w", padx=20, pady=24)

        # 当前屏幕分辨率
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        tk.Label(
            card,
            text=f"当前主屏幕分辨率: {sw} × {sh}",
            bg="#1a1d24", fg="#6b7280",
            font=("Microsoft YaHei UI", 9),
        ).pack(anchor="w", padx=20, pady=(0, 20))

    def _big_btn(self, parent, text, command, primary=False):
        bg = "#3b82f6" if primary else "#2d3340"
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg="white", relief="flat", padx=18, pady=10,
            font=("Microsoft YaHei UI", 11, "bold" if primary else "normal"),
            cursor="hand2", activebackground="#2563eb", activeforeground="white",
        )

    # ---- 动作 ----
    def _open_site(self):
        """打开个人网站。"""
        import webbrowser

        try:
            webbrowser.open(SITE_URL)
        except Exception as exc:
            messagebox.showinfo("个人网站", f"{SITE_URL}\n\n（无法自动打开浏览器：{exc}）")

    def _interval(self) -> float:
        try:
            return max(0.0, float(self.auto_interval.get()))
        except (tk.TclError, ValueError):
            return 0.0

    def _refresh_monitors(self):
        """重新枚举显示器并刷新下拉列表。"""
        prev_label = self.monitor_var.get()
        self.monitors = enumerate_monitors()
        labels = [m.label for m in self.monitors]
        self.monitor_combo["values"] = labels
        if not labels:
            self.monitor_var.set("")
            return
        # 尽量保持原选择；否则优先非主屏（外接），再退回第一项
        if prev_label in labels:
            self.monitor_var.set(prev_label)
        else:
            external = next((m for m in self.monitors if not m.primary), None)
            pick = external or self.monitors[0]
            self.monitor_var.set(pick.label)

    def _selected_monitor(self) -> Optional[Monitor]:
        label = self.monitor_var.get()
        for m in self.monitors:
            if m.label == label:
                return m
        return self.monitors[0] if self.monitors else None

    def close_all_tests(self) -> None:
        """关闭所有全屏测试窗口（含意外叠开的多窗口）。"""
        # 先关登记的活动窗
        active = self._active_test
        self._active_test = None
        if active is not None:
            try:
                active.close()
            except Exception:
                pass
        # 再扫一遍子窗口，防止残留叠层
        for child in list(self.winfo_children()):
            if isinstance(child, FullscreenTest):
                try:
                    child.close()
                except Exception:
                    pass
        try:
            self.unbind_all("<Escape>")
        except Exception:
            pass

    def _open_test(self, **kwargs):
        """统一入口：带上当前选中的目标显示器。开新测试前先关掉旧的。"""
        self.close_all_tests()
        mon = self._selected_monitor()
        test = FullscreenTest(self, monitor=mon, **kwargs)
        self._active_test = test

    def _identify_monitors(self):
        """在每块屏幕上短暂显示编号，方便确认哪块是外接屏。"""
        self._refresh_monitors()
        if not self.monitors:
            messagebox.showwarning("提示", "未检测到显示器")
            return

        overlays: List[tk.Toplevel] = []
        for m in self.monitors:
            win = tk.Toplevel(self)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.geometry(f"{m.width}x{m.height}+{m.x}+{m.y}")
            win.configure(bg="#0b1220")
            tag = "主屏" if m.primary else "外接"
            frame = tk.Frame(win, bg="#0b1220")
            frame.place(relx=0.5, rely=0.5, anchor="center")
            tk.Label(
                frame, text=str(m.index + 1),
                bg="#0b1220", fg="#3b82f6",
                font=("Segoe UI", 120, "bold"),
            ).pack()
            tk.Label(
                frame,
                text=f"显示器 {m.index + 1}（{tag}）\n{m.width} × {m.height}",
                bg="#0b1220", fg="#e8eaed",
                font=("Microsoft YaHei UI", 22),
                justify="center",
            ).pack(pady=8)
            if m.name:
                tk.Label(
                    frame, text=m.name, bg="#0b1220", fg="#9aa0a6",
                    font=("Consolas", 12),
                ).pack()
            overlays.append(win)

        def _close_all():
            for w in overlays:
                try:
                    w.destroy()
                except tk.TclError:
                    pass

        self.after(2500, _close_all)

    def _start_dead_pixel(self):
        colors = [c for _, c in SOLID_COLORS]
        self._open_test(
            mode="dead_pixel", colors=colors, auto_interval=self._interval()
        )

    def _start_solid(self, colors: List[Tuple[int, int, int]]):
        self._open_test(
            mode="solid", colors=colors, auto_interval=self._interval()
        )

    def _start_custom(self):
        self._open_test(mode="custom", custom_color=self.custom_color)

    def _start_gray_cycle(self):
        self._open_test(mode="gray", auto_interval=self._interval() or 0)

    def _start_gray_single(self, g: int):
        self._open_test(mode="custom", custom_color=(g, g, g))

    def _start_pattern(self, pattern: str):
        self._open_test(
            mode="pattern", pattern=pattern, auto_interval=self._interval()
        )

    def _start_effect(self, effect: str):
        self._open_test(mode="effect", effect=effect)

    def _pick_color(self):
        result = colorchooser.askcolor(
            color=f"#{self.custom_color[0]:02x}{self.custom_color[1]:02x}{self.custom_color[2]:02x}",
            title="选择纯色",
        )
        if result and result[0]:
            r, g, b = (int(result[0][0]), int(result[0][1]), int(result[0][2]))
            self.custom_color = (r, g, b)
            self.r_var.set(r)
            self.g_var.set(g)
            self.b_var.set(b)
            self._update_color_preview()

    def _sync_rgb_from_sliders(self):
        r, g, b = self.r_var.get(), self.g_var.get(), self.b_var.get()
        self.custom_color = (r, g, b)
        self._update_color_preview()

    def _update_color_preview(self):
        r, g, b = self.custom_color
        hexc = f"#{r:02x}{g:02x}{b:02x}"
        self.color_preview.config(bg=hexc)
        self.color_label.config(text=f"自定义颜色: {hexc.upper()}  RGB({r},{g},{b})")

    def _pick_export_color(self):
        c = self.export_color
        result = colorchooser.askcolor(
            color=f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}",
            title="选择导出颜色",
        )
        if result and result[0]:
            self._set_export_color(
                (int(result[0][0]), int(result[0][1]), int(result[0][2]))
            )

    def _set_export_color(self, rgb: Tuple[int, int, int]):
        self.export_color = rgb
        hexc = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        self.export_preview.config(bg=hexc)
        self.export_color_lbl.config(text=f"导出颜色: {hexc.upper()}")

    def _export_image(self):
        try:
            w = int(self.export_w.get())
            h = int(self.export_h.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("错误", "请输入有效的分辨率")
            return
        if w < 1 or h < 1 or w > 7680 or h > 4320:
            messagebox.showerror("错误", "分辨率范围: 1–7680 × 1–4320")
            return

        r, g, b = self.export_color
        default_name = f"solid_{r:02x}{g:02x}{b:02x}_{w}x{h}.png"
        path = filedialog.asksaveasfilename(
            title="保存纯色图片",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG 图片", "*.png"), ("JPEG 图片", "*.jpg;*.jpeg"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            img = Image.new("RGB", (w, h), self.export_color)
            img.save(path)
            messagebox.showinfo("完成", f"已保存:\n{path}\n尺寸: {w}×{h}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e))


def main():
    # 必须在创建 Tk 窗口前设置，否则 4K 缩放屏分辨率会读成逻辑像素（如 2560×1440）
    setup_dpi_awareness()
    app = ScreenTestApp()
    app.mainloop()


if __name__ == "__main__":
    main()
