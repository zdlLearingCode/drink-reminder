import tkinter as tk
import threading
import sys
import os
import winreg

from PIL import Image, ImageDraw
import pystray

INTERVAL_MINUTES = 15
APP_NAME = "DrinkWater"


def get_exe_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)


def is_autostart_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


def set_autostart(enable):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                         0, winreg.KEY_SET_VALUE)
    if enable:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_exe_path())
    else:
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


def create_tray_icon():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([16, 8, 48, 40], fill=(30, 144, 255))
    draw.polygon([(20, 40), (44, 40), (38, 56), (26, 56)], fill=(30, 144, 255))
    return img

class DrinkWaterApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.window = tk.Toplevel(self.root)
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)

        self.w, self.h = 210, 100
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = screen_w - self.w - 20
        y = screen_h - self.h - 60
        self.window.geometry(f"{self.w}x{self.h}+{x}+{y}")
        self.window.configure(bg="#f0f8ff")

        self.remaining = INTERVAL_MINUTES * 60
        self.running = True
        self.total_cups = 0
        self.tray_icon = None

        self._build_ui()
        self._build_context_menu()
        self.setup_tray()
        self.update_display()
        self.tick()

    def _build_ui(self):
        title_bar = tk.Frame(self.window, bg="#555555", height=24)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        lbl_title = tk.Label(title_bar, text=" 💧 喝水提醒", bg="#555555", fg="white",
                             font=("Microsoft YaHei", 9))
        lbl_title.pack(side="left")

        btn_close = tk.Label(title_bar, text=" ✕ ", bg="#555555", fg="white",
                             font=("Consolas", 10), cursor="hand2")
        btn_close.pack(side="right")
        btn_close.bind("<Button-1>", lambda e: self.hide_to_tray())

        btn_min = tk.Label(title_bar, text=" — ", bg="#555555", fg="white",
                           font=("Consolas", 10), cursor="hand2")
        btn_min.pack(side="right")
        btn_min.bind("<Button-1>", lambda e: self.hide_to_tray())

        for widget in (title_bar, lbl_title):
            widget.bind("<Button-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.on_drag)

        body = tk.Frame(self.window, bg="#f0f8ff")
        body.pack(fill="both", expand=True)

        self.label_time = tk.Label(body, text="", font=("Consolas", 20, "bold"),
                                   bg="#f0f8ff", fg="#1e90ff")
        self.label_time.pack(pady=(8, 0))

        self.label_cups = tk.Label(body, text="今日: 0 杯",
                                   font=("Microsoft YaHei", 9), bg="#f0f8ff", fg="#666")
        self.label_cups.pack()

        self.window.bind("<Button-3>", self.show_context_menu)

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="隐藏到托盘", command=self.hide_to_tray)
        self.context_menu.add_separator()
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        self.context_menu.add_checkbutton(label="开机自启",
                                          variable=self.autostart_var,
                                          command=self.toggle_autostart)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="退出", command=self.quit_app)

    def setup_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", self.show_from_tray, default=True),
            pystray.MenuItem("退出", self.quit_app)
        )
        self.tray_icon = pystray.Icon(APP_NAME, create_tray_icon(),
                                      "喝水提醒", menu)
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def hide_to_tray(self):
        self.window.withdraw()

    def show_from_tray(self, icon=None, item=None):
        self.window.after(0, self.window.deiconify)

    def toggle_autostart(self):
        set_autostart(self.autostart_var.get())

    def start_drag(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._win_x = self.window.winfo_x()
        self._win_y = self.window.winfo_y()

    def on_drag(self, event):
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        self.window.geometry(f"+{self._win_x + dx}+{self._win_y + dy}")

    def update_display(self):
        mins = self.remaining // 60
        secs = self.remaining % 60
        self.label_time.config(text=f"{mins:02d}:{secs:02d}")

    def tick(self):
        if not self.running:
            return
        if self.remaining > 0:
            self.remaining -= 1
            self.update_display()
            self.window.after(1000, self.tick)
        else:
            self.show_reminder()

    def show_reminder(self):
        self.total_cups += 1
        self.label_cups.config(text=f"今日: {self.total_cups} 杯")
        self.window.bell()
        self.window.after(0, self.window.deiconify)

        reminder = tk.Toplevel(self.window)
        reminder.title("喝水时间到！")
        reminder.attributes("-topmost", True)
        reminder.geometry("300x150")
        screen_w = reminder.winfo_screenwidth()
        screen_h = reminder.winfo_screenheight()
        x = (screen_w - 300) // 2
        y = (screen_h - 150) // 2
        reminder.geometry(f"+{x}+{y}")

        tk.Label(reminder, text="💧", font=("Segoe UI Emoji", 30)).pack(pady=(10, 0))
        tk.Label(reminder, text="该喝水啦！保持健康～",
                 font=("Microsoft YaHei", 12)).pack(pady=5)

        def close_and_reset():
            reminder.destroy()
            self.remaining = INTERVAL_MINUTES * 60
            self.tick()

        tk.Button(reminder, text="好的，已喝水", command=close_and_reset,
                  font=("Microsoft YaHei", 10), width=15).pack(pady=5)

    def quit_app(self, icon=None, item=None):
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = DrinkWaterApp()
    app.run()
