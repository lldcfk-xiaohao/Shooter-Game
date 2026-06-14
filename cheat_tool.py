"""
TopDown Shooter -- 游戏修改器 v4.0
使用方法：先启动游戏 shooter.py，再启动本修改器
通信方式：通过同目录 cheat_cfg.json 与游戏实时交换数据
新增：尝鲜模式 + P1/P2单独修改 + P1自瞄
"""
# -- 隐藏 Windows 控制台窗口 --
import sys, os
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk
import json, time, threading

def get_app_dir():
    """获取 exe 或脚本所在目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# -- 共享配置文件路径 --
CFG_FILE = os.path.join(get_app_dir(), "cheat_cfg.json")

# -- 登录凭证 --
LOGIN_USER = "ADMIN"
LOGIN_PASS = "3kau"

# -- 默认配置 --
DEFAULTS = {
    "hp":               8,
    "hp_max":           8,
    "mag_size":         12,
    "shoot_cd":         160,
    "bullet_r":         4,
    "bullet_dmg":       1,
    "bullet_spd":       9.5,
    "player_spd":       3.5,
    "reload_ms":        1400,
    "invincible":       False,
    "inf_ammo":         False,
    "p1_autoaim":       False,
    "teleport_center":  False,
    "kill_all":         False,
    "full_restore":     False,
    "apply":            False,
    "target":           "ALL",
    "_version":         0
}

def write_cfg(cfg):
    cfg["_version"] = cfg.get("_version", 0) + 1
    try:
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def read_cfg():
    try:
        if os.path.exists(CFG_FILE):
            with open(CFG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return dict(DEFAULTS)


# ======================================================================
#  登录窗口
# ======================================================================
class LoginWindow:
    BG       = "#1a1a2e"
    BG2      = "#16213e"
    BG3      = "#0f3460"
    ACCENT   = "#e94560"
    GREEN    = "#4ecca3"
    CYAN     = "#5bc0de"
    TEXT     = "#eeeeee"
    TEXT_DIM = "#888888"

    def __init__(self, root):
        self.root = root
        self.success = False
        self.trial_mode = False
        self.attempts = 0
        root.title("Shooter 修改器 -- 登录")
        root.resizable(False, False)
        root.configure(bg=self.BG)
        root.geometry("340x280")
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    def _build_ui(self):
        root = self.root
        title_f = tk.Frame(root, bg=self.BG3, height=48)
        title_f.pack(fill="x")
        tk.Label(title_f, text="  🔒  Shooter 修改器  --  身份验证",
                 bg=self.BG3, fg=self.ACCENT,
                 font=("Consolas", 11, "bold")).pack(side="left", pady=10)

        body = tk.Frame(root, bg=self.BG, padx=30, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="请输入账号和密码以使用修改器",
                 bg=self.BG, fg=self.TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w", pady=(0, 10))

        tk.Label(body, text="账号：", bg=self.BG, fg=self.TEXT,
                 font=("Consolas", 10)).pack(anchor="w")
        self.user_var = tk.StringVar()
        self.user_ent = tk.Entry(body, textvariable=self.user_var,
                            bg=self.BG2, fg=self.GREEN, insertbackground=self.GREEN,
                            font=("Consolas", 11), relief="flat",
                            highlightthickness=1, highlightcolor=self.ACCENT,
                            highlightbackground=self.BG3, width=30)
        self.user_ent.pack(pady=(4, 10), ipady=4)
        self.user_ent.focus()

        tk.Label(body, text="密码：", bg=self.BG, fg=self.TEXT,
                 font=("Consolas", 10)).pack(anchor="w")
        self.pass_var = tk.StringVar()
        self.pass_ent = tk.Entry(body, textvariable=self.pass_var,
                            show="*", bg=self.BG2, fg=self.GREEN,
                            insertbackground=self.GREEN,
                            font=("Consolas", 11), relief="flat",
                            highlightthickness=1, highlightcolor=self.ACCENT,
                            highlightbackground=self.BG3, width=30)
        self.pass_ent.pack(pady=(4, 14), ipady=4)

        self.user_ent.bind("<Return>", lambda e: self.pass_ent.focus())
        self.pass_ent.bind("<Return>", lambda e: self._do_login())

        btn_f = tk.Frame(body, bg=self.BG)
        btn_f.pack(fill="x")

        tk.Button(btn_f, text="登  录",
                  bg=self.ACCENT, fg="white",
                  font=("Consolas", 11, "bold"),
                  relief="flat", cursor="hand2",
                  padx=24, pady=5,
                  command=self._do_login).pack(side="left", padx=(0, 8))

        tk.Button(btn_f, text="尝鲜模式",
                  bg=self.BG3, fg=self.CYAN,
                  font=("Consolas", 10),
                  relief="flat", cursor="hand2",
                  padx=16, pady=5,
                  command=self._do_trial).pack(side="left", padx=(0, 8))

        tk.Button(btn_f, text="退  出",
                  bg=self.BG2, fg=self.TEXT_DIM,
                  font=("Consolas", 10),
                  relief="flat", cursor="hand2",
                  padx=16, pady=5,
                  command=self._on_close).pack(side="left")

        self.err_var = tk.StringVar()
        self.err_lbl = tk.Label(body, textvariable=self.err_var,
                                bg=self.BG, fg=self.ACCENT,
                                font=("Consolas", 9))
        self.err_lbl.pack(pady=(10, 0))

    def _do_login(self):
        user = self.user_var.get().strip()
        pwd  = self.pass_var.get()
        if user == LOGIN_USER and pwd == LOGIN_PASS:
            self.success = True
            self.root.destroy()
        else:
            self.attempts += 1
            remain = 3 - self.attempts
            if remain <= 0:
                self.err_var.set("❌ 错误次数过多，程序退出")
                self.root.after(1500, self._on_close)
            else:
                self.err_var.set(f"❌ 账号或密码错误，还剩 {remain} 次机会")
                self.pass_var.set("")
                self.pass_ent.focus()
                orig_x = self.root.winfo_x()
                orig_y = self.root.winfo_y()
                for dx in (12, -12, 8, -8, 0):
                    self.root.geometry(f"340x280+{orig_x + dx}+{orig_y}")
                    self.root.update()

    def _do_trial(self):
        """进入尝鲜模式，无需登录"""
        self.trial_mode = True
        self.root.destroy()

    def _on_close(self):
        self.success = False
        self.root.destroy()


# ======================================================================
#  修改器主界面 GUI  v3.1  (支持尝鲜模式)
# ======================================================================
class CheatTool:
    BG       = "#1a1a2e"
    BG2      = "#16213e"
    BG3      = "#0f3460"
    ACCENT   = "#e94560"
    GREEN    = "#4ecca3"
    TEXT     = "#eeeeee"
    TEXT_DIM = "#888888"
    YELLOW   = "#f5a623"
    CYAN     = "#5bc0de"
    PURPLE   = "#c678dd"

    def __init__(self, root, trial_mode=False):
        self.root = root
        self.trial_mode = trial_mode
        if trial_mode:
            root.title("TopDown Shooter Cheat v4.0 -- 尝鲜模式")
        else:
            root.title("TopDown Shooter Cheat v4.0")
        root.resizable(False, True)
        root.configure(bg=self.BG)
        if trial_mode:
            root.geometry("400x560")
        else:
            root.geometry("400x900")

        self.cfg = read_cfg()
        self._build_ui()
        self._start_status_thread()

    def _label(self, parent, text, color=None, size=10, bold=False):
        font = ("Consolas", size, "bold" if bold else "normal")
        return tk.Label(parent, text=text,
                        bg=self.BG, fg=color or self.TEXT, font=font)

    def _section(self, parent, text):
        tk.Label(parent, text=text, bg=self.BG, fg=self.ACCENT,
                 font=("Consolas", 10, "bold")).pack(anchor="w", pady=(6, 2))

    def _spinbox(self, parent, var, lo, hi, width=6, step=1):
        sb = tk.Spinbox(parent, from_=lo, to=hi, increment=step,
                        textvariable=var, width=width,
                        bg=self.BG2, fg=self.GREEN,
                        buttonbackground=self.BG3,
                        font=("Consolas", 11, "bold"),
                        relief="flat", insertbackground=self.GREEN)
        return sb

    def _spinbox_f(self, parent, var, lo, hi, width=6, step=0.5):
        sb = tk.Spinbox(parent, from_=lo, to=hi, increment=step,
                        textvariable=var, width=width,
                        bg=self.BG2, fg=self.CYAN,
                        buttonbackground=self.BG3,
                        font=("Consolas", 11, "bold"),
                        relief="flat", insertbackground=self.CYAN)
        return sb

    def _check(self, parent, text, var, color):
        tk.Checkbutton(parent, text=text, variable=var,
                       bg=self.BG, fg=color, selectcolor=self.BG2,
                       activebackground=self.BG, activeforeground=color,
                       font=("Consolas", 10)).pack(anchor="w", pady=2)

    def _sep(self, parent):
        tk.Frame(parent, bg=self.BG3, height=1).pack(fill="x", pady=5)

    # ------------------------------------------------------------------
    #  构建 UI 入口
    # ------------------------------------------------------------------
    def _build_ui(self):
        if self.trial_mode:
            self._build_ui_trial()
        else:
            self._build_ui_full()

    # ------------------------------------------------------------------
    #  尝鲜模式 UI（只有3个基本功能）
    # ------------------------------------------------------------------
    def _build_ui_trial(self):
        root = self.root

        # -- 标题栏 --
        title_bar = tk.Frame(root, bg=self.BG3, height=44)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="  ⚡ Shooter 修改器  --  尝鲜模式",
                 bg=self.BG3, fg=self.CYAN,
                 font=("Consolas", 13, "bold")).pack(side="left", pady=8)
        tk.Label(title_bar, text="  🔓 试玩  ",
                 bg=self.BG3, fg=self.CYAN,
                 font=("Consolas", 9)).pack(side="right", pady=8)

        # -- 滚动区域 --
        canvas = tk.Canvas(root, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main = tk.Frame(canvas, bg=self.BG, padx=16, pady=8)
        canvas_win = canvas.create_window((0, 0), window=main, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(canvas_win, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            canvas.yview_scroll(-1*(e.delta//120), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        # -- 尝鲜模式提示横幅 --
        trial_banner = tk.Frame(main, bg=self.BG3, padx=10, pady=8)
        trial_banner.pack(fill="x", pady=(0, 10))
        tk.Label(trial_banner, text="🔓  尝鲜模式  --  功能有限",
                 bg=self.BG3, fg=self.CYAN,
                 font=("Consolas", 11, "bold")).pack(anchor="w")
        tk.Label(trial_banner, text="登录后可解锁全部修改功能",
                 bg=self.BG3, fg=self.TEXT_DIM,
                 font=("Consolas", 9)).pack(anchor="w", pady=(4, 0))

        # -- 状态栏 --
        self.status_var = tk.StringVar(value="● 等待游戏启动...")
        self.status_lbl = tk.Label(main, textvariable=self.status_var,
                                   bg=self.BG, fg=self.TEXT_DIM,
                                   font=("Consolas", 9))
        self.status_lbl.pack(anchor="w", pady=(0, 6))

        # == 目标选择 ==
        self._section(main, "◆ 修改目标")
        target_row = tk.Frame(main, bg=self.BG)
        target_row.pack(fill="x", pady=3)
        self.target_var = tk.StringVar(value="ALL")
        for label, val in [("全部", "ALL"), ("仅P1", "P1"), ("仅P2", "P2")]:
            tk.Radiobutton(target_row, text=label, variable=self.target_var, value=val,
                           bg=self.BG, fg=self.CYAN, selectcolor=self.BG2,
                           activebackground=self.BG, activeforeground=self.CYAN,
                           font=("Consolas", 9)).pack(side="left", padx=6)

        self.p1_autoaim_var = tk.BooleanVar(value=self.cfg.get("p1_autoaim", False))
        self._check(main, "🎯  P1 自瞄（自动瞄准最近敌人）", self.p1_autoaim_var, self.PURPLE)

        self._sep(main)

        # == 玩家移动速度 ==
        self._section(main, "◆ 玩家移动速度")
        row1 = tk.Frame(main, bg=self.BG)
        row1.pack(fill="x", pady=3)
        self._label(row1, "移动速度:", self.TEXT_DIM).pack(side="left")
        self.pspd_var = tk.DoubleVar(value=min(self.cfg.get("player_spd", 3.5), 15.0))
        self._spinbox_f(row1, self.pspd_var, 0.5, 15.0).pack(side="left", padx=8)
        self._label(row1, "← 默认3.5", self.TEXT_DIM, size=8).pack(side="left")

        pspd_row = tk.Frame(main, bg=self.BG)
        pspd_row.pack(fill="x", pady=2)
        for label, val in [("慢(2)",2.0),("默(3.5)",3.5),("快(7)",7.0),("超快(15)",15.0)]:
            tk.Button(pspd_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.pspd_var.set(v)).pack(side="left", padx=2)

        self._sep(main)

        # == 子弹速度 ==
        self._section(main, "◆ 子弹速度")
        row2 = tk.Frame(main, bg=self.BG)
        row2.pack(fill="x", pady=3)
        self._label(row2, "子弹速度:", self.TEXT_DIM).pack(side="left")
        self.bspd_var = tk.DoubleVar(value=min(self.cfg.get("bullet_spd", 9.5), 40.0))
        self._spinbox_f(row2, self.bspd_var, 1.0, 40.0).pack(side="left", padx=8)
        self._label(row2, "← 默认9.5", self.TEXT_DIM, size=8).pack(side="left")

        bspd_row = tk.Frame(main, bg=self.BG)
        bspd_row.pack(fill="x", pady=2)
        for label, val in [("慢(5)",5.0),("默(9.5)",9.5),("快(20)",20.0),("极速(40)",40.0)]:
            tk.Button(bspd_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.bspd_var.set(v)).pack(side="left", padx=2)

        self._sep(main)

        # == 无限弹药 ==
        self._section(main, "◆ 基本开关")
        self.inf_ammo_var = tk.BooleanVar(value=self.cfg.get("inf_ammo", False))
        self._check(main, "∞  无限弹药（射击不消耗子弹）", self.inf_ammo_var, self.YELLOW)

        self._sep(main)

        # == 被锁功能提示 ==
        lock_frame = tk.Frame(main, bg=self.BG2, padx=10, pady=8)
        lock_frame.pack(fill="x", pady=(4, 8))
        tk.Label(lock_frame, text="🔒 以下功能需登录后解锁：",
                 bg=self.BG2, fg=self.TEXT_DIM,
                 font=("Consolas", 9, "bold")).pack(anchor="w")
        tk.Label(lock_frame, text="血量设置 · 无敌模式 · 弹夹容量 · 射速调整",
                 bg=self.BG2, fg=self.TEXT_DIM,
                 font=("Consolas", 8)).pack(anchor="w", pady=(2, 0))
        tk.Label(lock_frame, text="子弹大小/伤害 · 换弹速度 · 传送/清敌/回满",
                 bg=self.BG2, fg=self.TEXT_DIM,
                 font=("Consolas", 8)).pack(anchor="w", pady=(1, 0))

        # == 应用按钮 ==
        btn_row = tk.Frame(main, bg=self.BG)
        btn_row.pack(fill="x", pady=(6, 4))

        self.apply_btn = tk.Button(btn_row, text="▶  立即应用到游戏",
                                   bg=self.ACCENT, fg="white",
                                   font=("Consolas", 11, "bold"),
                                   relief="flat", cursor="hand2",
                                   padx=20, pady=8,
                                   command=self.apply)
        self.apply_btn.pack(fill="x", padx=(0, 6))

        self._label(main,
                    "提示：修改参数后点击「立即应用」，游戏下一帧生效",
                    self.TEXT_DIM, size=8).pack(pady=(4, 8))

    # ------------------------------------------------------------------
    #  完整模式 UI
    # ------------------------------------------------------------------
    def _build_ui_full(self):
        root = self.root

        # -- 标题栏 --
        title_bar = tk.Frame(root, bg=self.BG3, height=44)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="  ⚡ Shooter 修改器 v4.0",
                 bg=self.BG3, fg=self.ACCENT,
                 font=("Consolas", 13, "bold")).pack(side="left", pady=8)
        tk.Label(title_bar, text="  ✔ 已验证  ",
                 bg=self.BG3, fg=self.GREEN,
                 font=("Consolas", 9)).pack(side="right", pady=8)

        # -- 滚动区域 --
        canvas = tk.Canvas(root, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main = tk.Frame(canvas, bg=self.BG, padx=16, pady=8)
        canvas_win = canvas.create_window((0, 0), window=main, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(canvas_win, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            canvas.yview_scroll(-1*(e.delta//120), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        # -- 状态栏 --
        self.status_var = tk.StringVar(value="● 等待游戏启动...")
        self.status_lbl = tk.Label(main, textvariable=self.status_var,
                                   bg=self.BG, fg=self.TEXT_DIM,
                                   font=("Consolas", 9))
        self.status_lbl.pack(anchor="w", pady=(0, 6))

        # == 修改目标 ==
        self._section(main, "◆ 修改目标（P1/P2 分别修改）")
        target_row = tk.Frame(main, bg=self.BG)
        target_row.pack(fill="x", pady=3)
        self.target_var = tk.StringVar(value="ALL")
        for label, val, color in [("全部", "ALL", self.TEXT), ("仅P1", "P1", self.GREEN), ("仅P2", "P2", self.CYAN)]:
            tk.Radiobutton(target_row, text=label, variable=self.target_var, value=val,
                           bg=self.BG, fg=color, selectcolor=self.BG2,
                           activebackground=self.BG, activeforeground=color,
                           font=("Consolas", 10, "bold")).pack(side="left", padx=8)

        self.p1_autoaim_var = tk.BooleanVar(value=self.cfg.get("p1_autoaim", False))
        self._check(main, "🎯  P1 自瞄（自动瞄准最近敌人）", self.p1_autoaim_var, self.PURPLE)

        self._sep(main)

        # == 血量设置 ==
        self._section(main, "◆ 血量设置")
        row1 = tk.Frame(main, bg=self.BG)
        row1.pack(fill="x", pady=3)
        self._label(row1, "当前血量:", self.TEXT_DIM).pack(side="left")
        self.hp_var = tk.IntVar(value=self.cfg.get("hp", 8))
        self._spinbox(row1, self.hp_var, 1, 99).pack(side="left", padx=(8, 20))
        self._label(row1, "最大血量:", self.TEXT_DIM).pack(side="left")
        self.hp_max_var = tk.IntVar(value=self.cfg.get("hp_max", 8))
        self._spinbox(row1, self.hp_max_var, 1, 99).pack(side="left", padx=8)

        self.inv_var = tk.BooleanVar(value=self.cfg.get("invincible", False))
        self._check(main, "🛡  无敌模式（不受任何伤害）", self.inv_var, self.GREEN)

        self._sep(main)

        # == 弹药设置 ==
        self._section(main, "◆ 弹药设置")
        row2 = tk.Frame(main, bg=self.BG)
        row2.pack(fill="x", pady=3)
        self._label(row2, "弹夹容量:", self.TEXT_DIM).pack(side="left")
        self.mag_var = tk.IntVar(value=self.cfg.get("mag_size", 12))
        self._spinbox(row2, self.mag_var, 1, 999).pack(side="left", padx=8)

        self.inf_ammo_var = tk.BooleanVar(value=self.cfg.get("inf_ammo", False))
        self._check(main, "∞  无限弹药（射击不消耗子弹）", self.inf_ammo_var, self.YELLOW)

        self._sep(main)

        # == 射速设置 ==
        self._section(main, "◆ 射速（冷却越小越快）")
        row3 = tk.Frame(main, bg=self.BG)
        row3.pack(fill="x", pady=3)
        self._label(row3, "射击冷却(ms):", self.TEXT_DIM).pack(side="left")
        self.cd_var = tk.IntVar(value=self.cfg.get("shoot_cd", 160))
        self._spinbox(row3, self.cd_var, 0, 2000).pack(side="left", padx=8)
        self._label(row3, "← 0=无限速", self.TEXT_DIM, size=8).pack(side="left")

        cd_row = tk.Frame(main, bg=self.BG)
        cd_row.pack(fill="x", pady=2)
        for label, val in [("超快(20)", 20), ("快(80)", 80),
                            ("普通(160)", 160), ("慢(400)", 400)]:
            tk.Button(cd_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.cd_var.set(v)).pack(side="left", padx=2)

        self._sep(main)

        # == 子弹设置 ==
        self._section(main, "◆ 子弹设置（大小 + 伤害 + 速度）")
        row4 = tk.Frame(main, bg=self.BG)
        row4.pack(fill="x", pady=3)
        self._label(row4, "子弹半径:", self.TEXT_DIM).pack(side="left")
        self.br_var = tk.IntVar(value=self.cfg.get("bullet_r", 4))
        self._spinbox(row4, self.br_var, 1, 40).pack(side="left", padx=(8,20))
        self._label(row4, "伤害:", self.TEXT_DIM).pack(side="left")
        self.dmg_var = tk.IntVar(value=self.cfg.get("bullet_dmg", 1))
        self._spinbox(row4, self.dmg_var, 1, 50).pack(side="left", padx=8)

        row4b = tk.Frame(main, bg=self.BG)
        row4b.pack(fill="x", pady=3)
        self._label(row4b, "子弹速度:", self.TEXT_DIM).pack(side="left")
        self.bspd_var = tk.DoubleVar(value=self.cfg.get("bullet_spd", 9.5))
        self._spinbox_f(row4b, self.bspd_var, 1.0, 60.0).pack(side="left", padx=8)
        self._label(row4b, "← 默认9.5", self.TEXT_DIM, size=8).pack(side="left")

        br_row = tk.Frame(main, bg=self.BG)
        br_row.pack(fill="x", pady=2)
        for label, val in [("小(2)",2),("默认(4)",4),("大(8)",8),("巨大(16)",16)]:
            tk.Button(br_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.br_var.set(v)).pack(side="left", padx=2)

        dmg_row = tk.Frame(main, bg=self.BG)
        dmg_row.pack(fill="x", pady=2)
        for label, val in [("x1",1),("x2",2),("x5",5),("x10",10),("x50",50)]:
            tk.Button(dmg_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.dmg_var.set(v)).pack(side="left", padx=2)

        bspd_row = tk.Frame(main, bg=self.BG)
        bspd_row.pack(fill="x", pady=2)
        for label, val in [("慢(5)",5.0),("默(9.5)",9.5),("快(20)",20.0),("极速(40)",40.0)]:
            tk.Button(bspd_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.bspd_var.set(v)).pack(side="left", padx=2)

        self._sep(main)

        # == 玩家速度 ==
        self._section(main, "◆ 玩家移动速度")
        row5 = tk.Frame(main, bg=self.BG)
        row5.pack(fill="x", pady=3)
        self._label(row5, "移动速度:", self.TEXT_DIM).pack(side="left")
        self.pspd_var = tk.DoubleVar(value=self.cfg.get("player_spd", 3.5))
        self._spinbox_f(row5, self.pspd_var, 0.5, 30.0).pack(side="left", padx=8)
        self._label(row5, "← 默认3.5", self.TEXT_DIM, size=8).pack(side="left")

        pspd_row = tk.Frame(main, bg=self.BG)
        pspd_row.pack(fill="x", pady=2)
        for label, val in [("慢(2)",2.0),("默(3.5)",3.5),("快(7)",7.0),("超快(15)",15.0)]:
            tk.Button(pspd_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.pspd_var.set(v)).pack(side="left", padx=2)

        self._sep(main)

        # == 换弹速度 ==
        self._section(main, "◆ 换弹速度（越小越快）")
        row6 = tk.Frame(main, bg=self.BG)
        row6.pack(fill="x", pady=3)
        self._label(row6, "换弹时间(ms):", self.TEXT_DIM).pack(side="left")
        self.rl_var = tk.IntVar(value=self.cfg.get("reload_ms", 1400))
        self._spinbox(row6, self.rl_var, 50, 5000).pack(side="left", padx=8)

        rl_row = tk.Frame(main, bg=self.BG)
        rl_row.pack(fill="x", pady=2)
        for label, val in [("瞬(50)",50),("极快(200)",200),("快(600)",600),("默(1400)",1400)]:
            tk.Button(rl_row, text=label, bg=self.BG2, fg=self.TEXT_DIM,
                      font=("Consolas", 8), relief="flat", cursor="hand2",
                      command=lambda v=val: self.rl_var.set(v)).pack(side="left", padx=2)

        self._sep(main)

        # == 即时操作 ==
        self._section(main, "◆ 即时操作（点应用后执行一次）")

        self.teleport_var = tk.BooleanVar(value=False)
        self._check(main, "📍  传送到屏幕中央", self.teleport_var, self.CYAN)

        self.kill_all_var = tk.BooleanVar(value=False)
        self._check(main, "💥  清除当前所有敌人", self.kill_all_var, self.YELLOW)

        self.restore_var = tk.BooleanVar(value=False)
        self._check(main, "❤  回满血量 + 回满弹药", self.restore_var, self.GREEN)

        self._sep(main)

        # == 应用 / 重置按钮 ==
        btn_row = tk.Frame(main, bg=self.BG)
        btn_row.pack(fill="x", pady=(6, 4))

        self.apply_btn = tk.Button(btn_row, text="▶  立即应用到游戏",
                                   bg=self.ACCENT, fg="white",
                                   font=("Consolas", 11, "bold"),
                                   relief="flat", cursor="hand2",
                                   padx=20, pady=8,
                                   command=self.apply)
        self.apply_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        reset_btn = tk.Button(btn_row, text="重置",
                              bg=self.BG2, fg=self.TEXT_DIM,
                              font=("Consolas", 10), relief="flat",
                              cursor="hand2", padx=10, pady=8,
                              command=self.reset_defaults)
        reset_btn.pack(side="right")

        self._label(main,
                    "提示：修改参数后点击「立即应用」，游戏下一帧生效",
                    self.TEXT_DIM, size=8).pack(pady=(4, 0))
        self._label(main,
                    "即时操作（传送/清敌/回满）应用后自动取消勾选",
                    self.TEXT_DIM, size=8).pack(pady=(2, 8))

    # ------------------------------------------------------------------
    #  写入配置
    # ------------------------------------------------------------------
    def apply(self):
        # 尝鲜模式：只写基本字段，其余用默认值
        if self.trial_mode:
            cfg = {
                "hp":              DEFAULTS["hp"],
                "hp_max":          DEFAULTS["hp_max"],
                "mag_size":        DEFAULTS["mag_size"],
                "shoot_cd":        DEFAULTS["shoot_cd"],
                "bullet_r":        DEFAULTS["bullet_r"],
                "bullet_dmg":      DEFAULTS["bullet_dmg"],
                "bullet_spd":      round(self.bspd_var.get(), 2),
                "player_spd":      round(self.pspd_var.get(), 2),
                "reload_ms":       DEFAULTS["reload_ms"],
                "invincible":      False,
                "inf_ammo":        self.inf_ammo_var.get(),
                "p1_autoaim":      self.p1_autoaim_var.get(),
                "teleport_center": False,
                "kill_all":        False,
                "full_restore":    False,
                "target":          self.target_var.get(),
                "apply":           True,
                "_version":        self.cfg.get("_version", 0)
            }
        else:
            cfg = {
                "hp":              self.hp_var.get(),
                "hp_max":          self.hp_max_var.get(),
                "mag_size":        self.mag_var.get(),
                "shoot_cd":        self.cd_var.get(),
                "bullet_r":        self.br_var.get(),
                "bullet_dmg":      self.dmg_var.get(),
                "bullet_spd":      round(self.bspd_var.get(), 2),
                "player_spd":      round(self.pspd_var.get(), 2),
                "reload_ms":       self.rl_var.get(),
                "invincible":      self.inv_var.get(),
                "inf_ammo":        self.inf_ammo_var.get(),
                "p1_autoaim":      self.p1_autoaim_var.get(),
                "teleport_center": self.teleport_var.get(),
                "kill_all":        self.kill_all_var.get(),
                "full_restore":    self.restore_var.get(),
                "target":          self.target_var.get(),
                "apply":           True,
                "_version":        self.cfg.get("_version", 0)
            }
        self.cfg = cfg
        write_cfg(cfg)
        # 即时操作一次性，应用后取消勾选（完整模式）
        if not self.trial_mode:
            self.teleport_var.set(False)
            self.kill_all_var.set(False)
            self.restore_var.set(False)
        # 按钮反馈
        self.apply_btn.config(text="✔  已写入，游戏下帧生效", bg="#2d8a6a")
        self.root.after(1500, lambda:
            self.apply_btn.config(text="▶  立即应用到游戏", bg=self.ACCENT))

    def reset_defaults(self):
        """重置为默认值（仅完整模式可用）"""
        self.hp_var.set(8);       self.hp_max_var.set(8)
        self.mag_var.set(12);     self.cd_var.set(160)
        self.br_var.set(4);       self.dmg_var.set(1)
        self.bspd_var.set(9.5);   self.pspd_var.set(3.5)
        self.rl_var.set(1400)
        self.inv_var.set(False);  self.inf_ammo_var.set(False)
        self.p1_autoaim_var.set(False)
        self.target_var.set("ALL")
        self.teleport_var.set(False)
        self.kill_all_var.set(False)
        self.restore_var.set(False)
        self.apply()

    # ------------------------------------------------------------------
    #  状态检测线程
    # ------------------------------------------------------------------
    def _start_status_thread(self):
        def check():
            last_mtime = 0
            while True:
                try:
                    if os.path.exists(CFG_FILE):
                        mtime = os.path.getmtime(CFG_FILE)
                        if mtime != last_mtime:
                            last_mtime = mtime
                            self.root.after(0, lambda: (
                                self.status_var.set("● 游戏运行中 -- 修改实时生效"),
                                self.status_lbl.config(fg=self.GREEN)
                            ))
                    else:
                        self.root.after(0, lambda: (
                            self.status_var.set("● 等待游戏启动..."),
                            self.status_lbl.config(fg=self.TEXT_DIM)
                        ))
                except Exception:
                    pass
                time.sleep(1)
        t = threading.Thread(target=check, daemon=True)
        t.start()


# ======================================================================
#  入口
# ======================================================================
def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    login_root = tk.Tk()
    login = LoginWindow(login_root)
    login_root.mainloop()

    if login.success or login.trial_mode:
        root = tk.Tk()
        app = CheatTool(root, trial_mode=login.trial_mode)
        root.mainloop()

if __name__ == "__main__":
    main()
