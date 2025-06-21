import tkinter as tk
from tkinter import ttk, PhotoImage
import json
from gimbal import GimbalController

# Load gimbal addresses from config
with open("config.json") as f:
    config = json.load(f)

GIMBAL_OPTIONS = list(config.keys())
PORT = "COM5"
BAUD = 9600

TACTICAL_BLUE = {
    "bg": "#0f1b2d",
    "fg": "#ffffff",
    "button_bg": "#1e3a5f",
    "button_fg": "#ffffff",
    "highlight": "#2f81f7",
    "font": ("Segoe UI", 10),
    "font_bold": ("Segoe UI", 10, "bold")
}

class GimbalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PTZ Gimbal Controller")
        self.root.configure(bg=TACTICAL_BLUE["bg"])
        self.root.geometry("320x360")

        self.hold_enabled = tk.BooleanVar(value=False)
        self.pressed_buttons = {}
        self.buttons = {}
        self.active_pan = None
        self.active_tilt = None

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background=TACTICAL_BLUE["bg"], foreground=TACTICAL_BLUE["fg"], font=TACTICAL_BLUE["font"])
        style.configure("TButton", background=TACTICAL_BLUE["button_bg"], foreground=TACTICAL_BLUE["button_fg"], font=TACTICAL_BLUE["font_bold"])
        style.map("TButton", background=[("active", TACTICAL_BLUE["highlight"])])

        ttk.Label(root, text="Speed").pack(pady=(10, 0))
        self.speed = tk.IntVar(value=32)
        self.slider = tk.Scale(root, from_=1, to=63, orient=tk.HORIZONTAL, variable=self.speed,
                               bg=TACTICAL_BLUE["bg"], fg=TACTICAL_BLUE["fg"], highlightthickness=0,
                               troughcolor=TACTICAL_BLUE["highlight"])
        self.slider.pack(fill="x", padx=20)

        ttk.Label(root, text="Select Gimbal").pack(pady=(10, 0))
        self.selected_gimbal = tk.StringVar(value=GIMBAL_OPTIONS[0])
        self.dropdown = ttk.Combobox(root, textvariable=self.selected_gimbal, values=GIMBAL_OPTIONS, state="readonly")
        self.dropdown.pack(pady=(0, 10))

        hold_toggle = ttk.Checkbutton(root, text="Press & Hold Mode", variable=self.hold_enabled, command=self.refresh_bindings)
        hold_toggle.pack(pady=(0, 10))

        try:
            self.icons = {
                "up": PhotoImage(file="icons/up.png"),
                "down": PhotoImage(file="icons/down.png"),
                "left": PhotoImage(file="icons/left.png"),
                "right": PhotoImage(file="icons/right.png"),
                "stop": PhotoImage(file="icons/stop.png")
            }
        except:
            self.icons = {"up": None, "down": None, "left": None, "right": None, "stop": None}

        btn_frame = tk.Frame(root, bg=TACTICAL_BLUE["bg"])
        btn_frame.pack(pady=10)

        self.create_btn(btn_frame, "⬆️", self.tilt_up, 0, 1, "up")
        self.create_btn(btn_frame, "⬅️", self.pan_left, 1, 0, "left")
        self.create_btn(btn_frame, "⏹️", self.stop_all, 1, 1, "stop", bg="red", fg="white", activebg="#aa0000")
        self.create_btn(btn_frame, "➡️", self.pan_right, 1, 2, "right")
        self.create_btn(btn_frame, "⬇️", self.tilt_down, 2, 1, "down")

        self.refresh_bindings()
        self.root.bind_all("<KeyPress>", self.key_press)
        self.root.bind_all("<KeyRelease>", self.key_release)
        self.root.focus_set()

    def create_btn(self, frame, text, command, row, col, icon_key, bg=None, fg=None, activebg=None):
        kwargs = {
            "text": text,
            "width": 6,
            "height": 2,
            "bg": bg if bg else TACTICAL_BLUE["button_bg"],
            "fg": fg if fg else TACTICAL_BLUE["fg"],
            "activebackground": activebg if activebg else TACTICAL_BLUE["highlight"],
            "font": TACTICAL_BLUE["font_bold"]
        }
        if self.icons[icon_key]:
            kwargs["image"] = self.icons[icon_key]
            kwargs["text"] = ""
            kwargs["compound"] = "top"

        btn = tk.Button(frame, **kwargs)
        btn.grid(row=row, column=col, padx=5, pady=5)
        self.buttons[icon_key] = (btn, command)

    def refresh_bindings(self):
        for key, (btn, command) in self.buttons.items():
            btn.unbind("<ButtonPress>")
            btn.unbind("<ButtonRelease>")
            if self.hold_enabled.get():
                btn.config(command=lambda: None)
                btn.bind("<ButtonPress>", lambda e, c=command, k=key: self._start_hold(c, k))
                btn.bind("<ButtonRelease>", lambda e, k=key: self._stop_hold(k))
            else:
                btn.config(command=command)

    def _start_hold(self, func, key):
        if key not in self.pressed_buttons:
            func()
            self.pressed_buttons[key] = self.root.after(100, lambda: self._start_hold(func, key))
            if key in ["left", "right"]:
                self.active_pan = key
            elif key in ["up", "down"]:
                self.active_tilt = key

    def _stop_hold(self, key):
        if key in self.pressed_buttons:
            self.root.after_cancel(self.pressed_buttons[key])
            del self.pressed_buttons[key]

        if key in ["left", "right"] and self.active_pan == key:
            self.active_pan = None
            self.stop_pan()
            if self.active_tilt == "up": self.tilt_up()
            elif self.active_tilt == "down": self.tilt_down()
        elif key in ["up", "down"] and self.active_tilt == key:
            self.active_tilt = None
            self.stop_tilt()
            if self.active_pan == "left": self.pan_left()
            elif self.active_pan == "right": self.pan_right()

    def key_press(self, event):
      #  print(f"Key pressed: keysym='{event.keysym}' char='{event.char}'")  # Debug line

        keysym_map = {
            "Up": (self.tilt_up, "up"),
            "Down": (self.tilt_down, "down"),
            "Left": (self.pan_left, "left"),
            "Right": (self.pan_right, "right"),
            "space": (self.stop_all, "stop"),
            "KP_Add": (self.increase_speed, None),
            "KP_Subtract": (self.decrease_speed, None)
        }

        char_map = {
            "+": self.increase_speed,
            "=": self.increase_speed,
            "-": self.decrease_speed
        }

        if event.keysym in keysym_map:
            func, key = keysym_map[event.keysym]
            if key:
                self._start_hold(func, key)
            else:
                func()
        elif event.char in char_map:
            char_map[event.char]()

    def key_release(self, event):
        keymap = {
            "Up": "up",
            "Down": "down",
            "Left": "left",
            "Right": "right",
            "space": "stop"
        }
        if event.keysym in keymap:
            self._stop_hold(keymap[event.keysym])

    def increase_speed(self):
        val = self.speed.get()
        if val < 63:
            self.speed.set(val + 1)
            self.refresh_motion()

    def decrease_speed(self):
        val = self.speed.get()
        if val > 1:
            self.speed.set(val - 1)
            self.refresh_motion()

    def refresh_motion(self):
        if self.active_pan == "left": self.pan_left()
        elif self.active_pan == "right": self.pan_right()
        if self.active_tilt == "up": self.tilt_up()
        elif self.active_tilt == "down": self.tilt_down()

    def get_gimbal(self):
        addr = config[self.selected_gimbal.get()]
        return GimbalController(PORT, addr, BAUD)

    def pan_left(self): self.get_gimbal().pan_left(self.speed.get())
    def pan_right(self): self.get_gimbal().pan_right(self.speed.get())
    def tilt_up(self): self.get_gimbal().tilt_up(self.speed.get())
    def tilt_down(self): self.get_gimbal().tilt_down(self.speed.get())
    def stop_pan(self): self.get_gimbal().stop()
    def stop_tilt(self): self.get_gimbal().stop()
    def stop_all(self):
        for key in list(self.pressed_buttons): self._stop_hold(key)
        self.active_pan = None
        self.active_tilt = None
        self.get_gimbal().stop()

if __name__ == "__main__":
    root = tk.Tk()
    app = GimbalGUI(root)
    root.mainloop()