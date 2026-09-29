import sys
import subprocess
import shutil
from tkinter import messagebox
import os
import json
import math
from datetime import datetime, timedelta

try:
    import customtkinter as ctk
except ModuleNotFoundError:
    print("📦 Installing customtkinter...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COURSES_DIR = os.path.join(BASE_DIR, "courses")
SETTINGS_FILE = os.path.join(BASE_DIR, "app_settings.json")
LEGACY_CONFIG = os.path.join(BASE_DIR, "course_config.json")
LEGACY_STORAGE = os.path.join(BASE_DIR, "datacamp_tracker_storage.json")

# ============================================================
# COURSES  ->  each course is a file in the courses/ folder.
# Use the dropdown / New / Edit buttons in the app to manage them.
# ============================================================

DEFAULT_PHASES = [
    ("Foundations Arch", 4, [
        ("Understanding Cloud Computing", 2), ("Introduction to Python for Developers", 4),
        ("Intermediate Python for Developers", 4), ("Introduction to Git", 3),
        ("Introduction to Object-Oriented Programming", 4)]),
    ("Data Handling Arch", 4, [
        ("Data Manipulation with pandas", 4), ("Streamlined Data Ingestion with Python", 4),
        ("Writing Efficient Python Code", 4), ("Writing Code Tests in Python", 4),
        ("Understanding Modern Data Architecture", 2)]),
    ("Orchestration Arch", 4, [
        ("Introduction to Data Pipelines", 3), ("Introduction to Bash / Unix Command Line", 3),
        ("Introduction to Apache Airflow", 4), ("Containerization Concepts (Docker)", 2)]),
]


def slugify(name):
    s = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    return s or "course"


def default_config():
    return {
        "track_name": "Data Engineering",
        "horizon": "Standard Q4 View",
        "phases": [
            {"name": n, "weeks": w, "courses": [{"name": a, "hours": h} for a, h in cs]}
            for n, w, cs in DEFAULT_PHASES
        ],
    }


def new_course_config(name):
    return {
        "track_name": name,
        "horizon": "Standard View",
        "phases": [{"name": "Phase 1", "weeks": 4, "courses": [
            {"name": "First course", "hours": 4}, {"name": "Second course", "hours": 4}]}],
    }


def config_path(slug):
    return os.path.join(COURSES_DIR, f"{slug}.json")


def storage_path(slug):
    return os.path.join(COURSES_DIR, f"{slug}.progress.json")


def list_courses():
    return sorted(f[:-5] for f in os.listdir(COURSES_DIR)
                  if f.endswith(".json") and not f.endswith(".progress.json"))


def course_labels():
    out = {}
    for slug in list_courses():
        try:
            with open(config_path(slug)) as f:
                label = json.load(f).get("track_name", slug)
        except Exception:
            label = slug
        out[label if label not in out else f"{label} ({slug})"] = slug
    return out


def bootstrap_courses():
    os.makedirs(COURSES_DIR, exist_ok=True)
    if list_courses():
        return
    cfg = default_config()
    if os.path.exists(LEGACY_CONFIG):
        try:
            with open(LEGACY_CONFIG) as f:
                cfg = json.load(f)
        except Exception:
            pass
    with open(config_path("data-engineering"), "w") as f:
        json.dump(cfg, f, indent=2)
    if os.path.exists(LEGACY_STORAGE):
        shutil.copy(LEGACY_STORAGE, storage_path("data-engineering"))


def get_active():
    try:
        with open(SETTINGS_FILE) as f:
            slug = json.load(f)["active"]
    except Exception:
        slug = None
    courses = list_courses()
    return slug if slug in courses else courses[0]


def set_active(slug):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"active": slug}, f)


def open_file(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Couldn't open {path}: {e}")


def set_course(slug):
    global ACTIVE, STORAGE_FILE, CFG, TRACK_NAME, HORIZON, TRACK_DATA
    global TOTAL_TRACK_HOURS, PHASES, PHASE_INDEXES, PHASE_RANGES
    ACTIVE, STORAGE_FILE = slug, storage_path(slug)
    try:
        with open(config_path(slug)) as f:
            CFG = json.load(f)
        assert CFG["phases"] and all(p["courses"] for p in CFG["phases"])
    except Exception as e:
        print(f"{slug}.json problem ({e}); showing a blank template instead")
        CFG = new_course_config(slug)
    TRACK_NAME = CFG.get("track_name", slug)
    HORIZON = CFG.get("horizon", "Standard View")
    TRACK_DATA = [
        {"name": c["name"], "hours": c["hours"], "phase": p["name"]}
        for p in CFG["phases"] for c in p["courses"]
    ]
    TOTAL_TRACK_HOURS = sum(c["hours"] for c in TRACK_DATA)
    PHASES = [p["name"] for p in CFG["phases"]]
    PHASE_INDEXES = {ph: [i for i, c in enumerate(TRACK_DATA) if c["phase"] == ph] for ph in PHASES}
    PHASE_RANGES, w = [], 1
    for p in CFG["phases"]:
        n = int(p.get("weeks", 4))
        PHASE_RANGES.append((w, w + n - 1))
        w += n


bootstrap_courses()
set_course(get_active())

BG = "#16181E"
PANEL = "#1D2027"
PANEL_LIGHT = "#252831"
CARD = "#20232B"
WHITE = "#F4F6F8"
TEXT = "#D8DCE2"
MUTED = "#8C929D"
BLUE_BRIGHT = "#5AA0FF"
GREEN = "#54C994"
AMBER = "#E8B04B"
BORDER = "#30343D"
CANVAS_BG = "#080B10"
TRACK_ARC = "#1C2430"
PHASE_COLORS = ["#3F7BD8", "#5B9BF0", "#8FD9B8", "#3FBF7F"]
CANVAS_H = 240
PACE_VALUES = ["5 Hours / Week", "10 Hours / Week", "20 Hours / Week", "40 Hours / Week"]
TARGET_VALUES = ["This Month", "Next Month", "Within 3 Months", "Flexible"]


class AdvancedDataTracker(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(f"{TRACK_NAME} Tracker")
        self.geometry("470x920")
        self.minsize(440, 700)
        self.configure(fg_color=BG)
        self.restart_requested = False
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.weekly_hours_var = ctk.StringVar(value="10")
        self.target_month_var = ctk.StringVar(value="Next Month")
        self.course_vars = [ctk.BooleanVar(value=False) for _ in TRACK_DATA]
        self.log = []
        self.timer_start = None
        self.phase_widgets, self.phase_open, self.hours_labels = {}, {}, {}
        self.arc_state = {"phase_pcts": [0.0] * len(PHASES), "active_phase": PHASES[0], "milestone": ""}

        self.load_from_storage()
        todo = next((c["name"] for i, c in enumerate(TRACK_DATA) if not self.course_vars[i].get()),
                    TRACK_DATA[0]["name"])
        self.log_course_var = ctk.StringVar(value=todo)
        self.build_interface()
        self.update_analytics()

    # ------------------------------------------------------------ helpers

    def make_pill(self, parent, prefix, value, icon=None):
        pill = ctk.CTkFrame(parent, corner_radius=8, fg_color=PANEL_LIGHT)
        if icon:
            ctk.CTkLabel(pill, text=icon, text_color=BLUE_BRIGHT, font=ctk.CTkFont(size=11)
                         ).pack(side="left", padx=(10, 2), pady=7)
        ctk.CTkLabel(pill, text=prefix, text_color=MUTED, font=ctk.CTkFont(size=10)
                     ).pack(side="left", padx=(0 if icon else 10, 6), pady=7)
        val = ctk.CTkLabel(pill, text=value, text_color=WHITE, font=ctk.CTkFont(size=11, weight="bold"))
        val.pack(side="left", padx=(0, 12), pady=7)
        return pill, val

    def make_metric(self, parent, col, label, value, color):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, sticky="ew")
        ctk.CTkLabel(box, text=label, text_color=MUTED, font=ctk.CTkFont(size=9)).pack()
        val = ctk.CTkLabel(box, text=value, text_color=color, font=ctk.CTkFont(size=12, weight="bold"))
        val.pack(pady=(3, 0))
        return val

    def bind_click(self, widget, callback):
        widget.bind("<Button-1>", lambda e: callback())
        for child in widget.winfo_children():
            self.bind_click(child, callback)

    # ------------------------------------------------------------- main UI

    def build_interface(self):
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=12, pady=12)
        card = ctk.CTkFrame(self.main_scroll, corner_radius=18, fg_color=PANEL,
                            border_width=1, border_color="#292D35")
        card.pack(fill="x")

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 12))
        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left")
        self.make_pill(left, "Track:", TRACK_NAME)[0].pack(anchor="w")
        self.make_pill(left, "Horizon:", HORIZON)[0].pack(anchor="w", pady=(6, 0))
        fp, self.forecast_value = self.make_pill(top, "Forecast Target:", "--", icon="📅")
        fp.pack(side="right")

        self.arc_canvas = ctk.CTkCanvas(card, height=CANVAS_H, bg=CANVAS_BG, highlightthickness=0)
        self.arc_canvas.pack(fill="x")
        self.arc_canvas.bind("<Configure>", lambda e: self.draw_progress_arcs())

        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x")
        metrics = ctk.CTkFrame(card, fg_color="transparent")
        metrics.pack(fill="x", padx=16, pady=12)
        for c in range(3):
            metrics.grid_columnconfigure(c, weight=1, uniform="metric")
        self.modules_value = self.make_metric(metrics, 0, "Completed Modules", f"0 / {len(PHASES)}", WHITE)
        self.progress_value = self.make_metric(metrics, 1, "Current Track Progress", "0%", GREEN)
        self.date_value = self.make_metric(metrics, 2, "Forecast Target Date", "--", BLUE_BRIGHT)
        ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x")

        course_row = ctk.CTkFrame(card, fg_color="transparent")
        course_row.pack(fill="x", padx=16, pady=(12, 0))
        self.course_map = course_labels()
        current = next((l for l, sl in self.course_map.items() if sl == ACTIVE), ACTIVE)
        self.course_menu = ctk.CTkOptionMenu(
            course_row, values=list(self.course_map), command=self.switch_course,
            width=150, height=28, fg_color=PANEL_LIGHT, button_color=PANEL_LIGHT,
            button_hover_color=BORDER, text_color=WHITE, font=ctk.CTkFont(size=11, weight="bold"))
        self.course_menu.set(current)
        self.course_menu.pack(side="left")
        for txt, w, cmd in (("+ New", 58, self.new_course), ("Edit", 46, self.edit_course),
                            ("⟳", 34, self.restart),
                            ("Delete", 52, self.delete_course)):
            ctk.CTkButton(course_row, text=txt, width=w, height=28, fg_color=PANEL_LIGHT,
                          hover_color=BORDER, text_color=TEXT, font=ctk.CTkFont(size=10),
                          command=cmd).pack(side="left", padx=(6, 0))

        # settings
        settings = ctk.CTkFrame(card, fg_color="transparent")
        settings.pack(fill="x", padx=16, pady=(12, 0))
        opt = dict(height=28, fg_color=PANEL_LIGHT, button_color=PANEL_LIGHT,
                   button_hover_color=BORDER, text_color=TEXT, font=ctk.CTkFont(size=10))
        self.pace_dropdown = ctk.CTkOptionMenu(settings, values=PACE_VALUES,
                                               command=self.on_pace_changed, width=140, **opt)
        stored = f"{self.weekly_hours_var.get()} Hours / Week"
        if stored not in PACE_VALUES:
            stored = PACE_VALUES[1]
            self.weekly_hours_var.set("10")
        self.pace_dropdown.set(stored)
        self.pace_dropdown.pack(side="left")
        ctk.CTkOptionMenu(settings, values=TARGET_VALUES, variable=self.target_month_var,
                          command=lambda _: self.update_analytics(), width=135, **opt
                          ).pack(side="left", padx=8)

        self.build_study_log(card, opt)

        ctk.CTkLabel(card, text="Curriculum Sections Accordion (Select to Expand Time Arch)",
                     text_color=MUTED, font=ctk.CTkFont(size=10)
                     ).pack(anchor="w", padx=16, pady=(14, 8))
        self.curriculum_container = ctk.CTkFrame(card, fg_color="transparent")
        self.curriculum_container.pack(fill="x", padx=16, pady=(0, 16))
        for n, phase in enumerate(PHASES):
            self.create_phase(phase, n)

    # ----------------------------------------------------------- study log

    def build_study_log(self, card, opt):
        box = ctk.CTkFrame(card, corner_radius=10, fg_color=CARD, border_width=1, border_color="#2B2F38")
        box.pack(fill="x", padx=16, pady=(14, 0))

        r1 = ctk.CTkFrame(box, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(r1, text="Study Log", text_color=WHITE,
                     font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        self.timer_btn = ctk.CTkButton(r1, text="Start", width=90, height=28,
                                       fg_color="#3F7BD8", command=self.toggle_timer)
        self.timer_btn.pack(side="right")
        self.timer_label = ctk.CTkLabel(r1, text="00:00:00", text_color=BLUE_BRIGHT,
                                        font=ctk.CTkFont(size=18, weight="bold"))
        self.timer_label.pack(side="right", padx=10)

        r2 = ctk.CTkFrame(box, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=4)
        ctk.CTkOptionMenu(r2, values=[c["name"] for c in TRACK_DATA],
                          variable=self.log_course_var, width=170, **opt).pack(side="left")
        self.hours_entry = ctk.CTkEntry(r2, width=80, height=28, placeholder_text="1.5 or 45m",
                                        fg_color=PANEL_LIGHT, border_color=BORDER, font=ctk.CTkFont(size=10))
        self.hours_entry.pack(side="left", padx=6)
        self.hours_entry.bind("<Return>", lambda e: self.add_manual())
        ctk.CTkButton(r2, text="Add", width=44, height=28, fg_color="#3F7BD8",
                      command=self.add_manual).pack(side="left")
        ctk.CTkButton(r2, text="Undo", width=44, height=28, fg_color=PANEL_LIGHT,
                      hover_color=BORDER, command=self.undo_log).pack(side="left", padx=6)

        self.log_stats = ctk.CTkLabel(box, text="", text_color=MUTED, justify="left",
                                      wraplength=380, font=ctk.CTkFont(size=10))
        self.log_stats.pack(anchor="w", padx=12, pady=(4, 10))

    def toggle_timer(self):
        if self.timer_start is None:
            self.timer_start = datetime.now()
            self.timer_btn.configure(text="Stop & Save", fg_color=AMBER, text_color="#111111")
            self.tick()
        else:
            secs = (datetime.now() - self.timer_start).total_seconds()
            self.timer_start = None
            self.timer_btn.configure(text="Start", fg_color="#3F7BD8", text_color=WHITE)
            self.timer_label.configure(text="00:00:00")
            self.add_log(secs / 3600)

    def tick(self):
        if self.timer_start:
            s = int((datetime.now() - self.timer_start).total_seconds())
            self.timer_label.configure(text=f"{s // 3600:02}:{s % 3600 // 60:02}:{s % 60:02}")
            self.after(1000, self.tick)

    def add_manual(self):
        t = self.hours_entry.get().strip().lower()
        try:
            h = float(t[:-1]) / 60 if t.endswith("m") else float(t)
        except ValueError:
            return
        self.hours_entry.delete(0, "end")
        self.add_log(h)

    def add_log(self, hours):
        if hours <= 0:
            return
        self.log.append({"date": datetime.now().isoformat(timespec="minutes"),
                         "hours": round(hours, 3), "course": self.log_course_var.get()})
        self.update_analytics()

    def undo_log(self):
        if self.log:
            self.log.pop()
            self.update_analytics()

    def restart(self, slug=None):
        if slug:
            set_active(slug)
        self.restart_requested = True
        self.on_close()

    def switch_course(self, label):
        self.after(50, lambda: self.restart(self.course_map[label]))

    def delete_course(self):
        if len(list_courses()) < 2:
            messagebox.showinfo("Can't delete", "This is your only course. Create another one first.")
            return
        if not messagebox.askyesno(
                "Delete course",
                f"Delete '{TRACK_NAME}' along with its progress and study log?\nThis can't be undone."):
            return
        self.timer_start = None  # don't save a running session back into the deleted course
        for path in (config_path(ACTIVE), storage_path(ACTIVE)):
            if os.path.exists(path):
                os.remove(path)
        set_active(list_courses()[0])
        self.after(50, self.restart)

    def edit_course(self):
        open_file(config_path(ACTIVE))

    def new_course(self):
        name = ctk.CTkInputDialog(text="Name of the new course (e.g. DevOps):",
                                  title="New course").get_input()
        if not name or not name.strip():
            return
        slug = slugify(name)
        if not os.path.exists(config_path(slug)):
            with open(config_path(slug), "w") as f:
                json.dump(new_course_config(name.strip()), f, indent=2)
        open_file(config_path(slug))
        self.after(50, lambda: self.restart(slug))

    def on_close(self):
        if self.timer_start:
            self.toggle_timer()
        self.destroy()

    # ----------------------------------------------------------- accordion

    def create_phase(self, phase, n):
        accent = PHASE_COLORS[n % len(PHASE_COLORS)]
        self.phase_open[phase] = False
        box = ctk.CTkFrame(self.curriculum_container, corner_radius=10, fg_color=CARD,
                           border_width=1, border_color="#2B2F38")
        box.pack(fill="x", pady=4)
        header = ctk.CTkFrame(box, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(header, text="●", text_color=accent, font=ctk.CTkFont(size=11)
                     ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header, text=phase, text_color=WHITE, font=ctk.CTkFont(size=11, weight="bold")
                     ).pack(side="left")
        a, b = PHASE_RANGES[n]
        chip = ctk.CTkFrame(header, corner_radius=6, fg_color=PANEL_LIGHT)
        chip.pack(side="left", padx=8)
        ctk.CTkLabel(chip, text=f"Weeks {a}-{b}", text_color=MUTED, font=ctk.CTkFont(size=9)
                     ).pack(padx=8, pady=2)
        arrow = ctk.CTkLabel(header, text="⌄", text_color=MUTED, width=20)
        arrow.pack(side="right")
        completion = ctk.CTkLabel(header, text="0% Completed", text_color=TEXT, font=ctk.CTkFont(size=10))
        completion.pack(side="right", padx=6)

        content = ctk.CTkFrame(box, fg_color=PANEL_LIGHT, corner_radius=8)
        for idx in PHASE_INDEXES[phase]:
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=5)
            ctk.CTkCheckBox(row, text=TRACK_DATA[idx]["name"], variable=self.course_vars[idx],
                            command=self.update_analytics, text_color=TEXT, fg_color=accent,
                            hover_color=accent, border_color=MUTED, font=ctk.CTkFont(size=10)
                            ).pack(side="left")
            lbl = ctk.CTkLabel(row, text="", text_color=MUTED, font=ctk.CTkFont(size=9))
            lbl.pack(side="right")
            self.hours_labels[idx] = lbl

        self.phase_widgets[phase] = {"completion": completion, "arrow": arrow, "content": content}
        self.bind_click(header, lambda p=phase: self.toggle_phase(p))

    def toggle_phase(self, phase):
        w = self.phase_widgets[phase]
        if self.phase_open[phase]:
            w["content"].pack_forget()
            w["arrow"].configure(text="⌄")
        else:
            w["content"].pack(fill="x", padx=10, pady=(0, 10))
            w["arrow"].configure(text="⌃")
        self.phase_open[phase] = not self.phase_open[phase]

    # ------------------------------------------------------------ forecast

    def on_pace_changed(self, value):
        self.weekly_hours_var.set(value.split(" ")[0])
        self.update_analytics()

    def get_deadline(self):
        now = datetime.now()
        choice = self.target_month_var.get()
        if choice == "Within 3 Months":
            return now + timedelta(days=91)
        offset = {"This Month": 0, "Next Month": 1}.get(choice)
        if offset is None:
            return None
        m = now.month - 1 + offset
        y, m = now.year + m // 12, m % 12 + 1
        return datetime(y + m // 12, m % 12 + 1, 1) - timedelta(days=1)

    def update_analytics(self):
        now = datetime.now()
        done = [v.get() for v in self.course_vars]
        hours_done = sum(c["hours"] for c, d in zip(TRACK_DATA, done) if d)
        hours_left = TOTAL_TRACK_HOURS - hours_done
        pct = hours_done / TOTAL_TRACK_HOURS if TOTAL_TRACK_HOURS else 0

        # study log stats
        stamps = [(datetime.fromisoformat(e["date"]), e["hours"]) for e in self.log]
        total_logged = sum(h for _, h in stamps)
        week_hours = sum(h for t, h in stamps if t >= now - timedelta(days=7))
        try:
            pace = float(self.weekly_hours_var.get())
        except ValueError:
            pace = 10.0
        src = "planned"
        if stamps:
            days = (now - min(t for t, _ in stamps)).days
            if days >= 7 and total_logged > 0:
                pace, src = total_logged / (days / 7), "logged"
        self.log_stats.configure(
            text=f"Last 7 days: {week_hours:.1f} h  ·  Total: {total_logged:.1f} h  ·  "
                 f"Pace: {pace:.1f} h/wk ({src})")
        per_course = {}
        for e in self.log:
            per_course[e.get("course")] = per_course.get(e.get("course"), 0) + e["hours"]
        for i, c in enumerate(TRACK_DATA):
            self.hours_labels[i].configure(text=f"{per_course.get(c['name'], 0):.1f} / {c['hours']} hrs")

        phase_pcts = []
        for phase in PHASES:
            idxs = PHASE_INDEXES[phase]
            p = sum(1 for i in idxs if done[i]) / len(idxs)
            phase_pcts.append(p)
            self.phase_widgets[phase]["completion"].configure(text=f"{p * 100:.0f}% Completed")

        active = next((ph for ph, p in zip(PHASES, phase_pcts) if p < 1), PHASES[-1])
        next_course = next((c["name"] for c, d in zip(TRACK_DATA, done) if not d), None)
        weeks_needed = hours_left / pace if pace > 0 else 0
        target_date = now + timedelta(weeks=weeks_needed)
        deadline = self.get_deadline()

        self.modules_value.configure(text=f"{sum(1 for p in phase_pcts if p >= 1)} / {len(PHASES)}")
        self.progress_value.configure(text=f"{pct * 100:.0f}%")
        if hours_left == 0:
            self.date_value.configure(text="Complete", text_color=GREEN)
        else:
            ok = deadline is None or target_date <= deadline
            self.date_value.configure(text=target_date.strftime("%b %d, %Y"),
                                      text_color=BLUE_BRIGHT if ok else AMBER)
        self.forecast_value.configure(text=deadline.strftime("%b %d, %Y") if deadline else "Flexible")

        self.arc_state = {"phase_pcts": phase_pcts, "active_phase": active,
                          "milestone": next_course or "Curriculum complete 🎉"}
        self.draw_progress_arcs()
        self.save_to_storage()

    # ---------------------------------------------------------------- arcs

    def draw_progress_arcs(self):
        c = self.arc_canvas
        c.delete("all")
        w = max(c.winfo_width(), 300)
        n = len(PHASES)
        cx, cy = w / 2, CANVAS_H - 40
        max_r = min(w / 2 - 22, cy - 45)
        base = 50
        step = min(42, (max_r - base) / max(n - 1, 1))
        outer = base + (n - 1) * step

        c.create_line(16, cy, w - 16, cy, fill="#27313E", dash=(2, 4))
        c.create_line(cx, cy, cx, cy - outer, fill="#1F2A38", dash=(2, 4))

        for i, pct in enumerate(self.arc_state["phase_pcts"]):
            r = base + i * step
            color = PHASE_COLORS[i % len(PHASE_COLORS)]
            wd = max(4, 8 - i)
            box = (cx - r, cy - r, cx + r, cy + r)
            c.create_arc(*box, start=180, extent=-180, style="arc", outline=TRACK_ARC, width=wd)
            if pct > 0:
                c.create_arc(*box, start=180, extent=-180 * pct, style="arc", outline=color, width=wd)
                ang = math.pi * (1 - pct)
                x, y = cx + r * math.cos(ang), cy - r * math.sin(ang)
                c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline=CANVAS_BG, width=2)
            a, b = PHASE_RANGES[i]
            c.create_text(cx - r, cy + 14, text=f"W{a}-{b}", fill=MUTED, font=("Arial", 8))

        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#355174", outline="")
        c.create_text(14, 16, text="Active Matrix Phase", fill=MUTED, anchor="w", font=("Arial", 9))
        c.create_text(14, 38, text=self.arc_state["active_phase"], fill=WHITE, anchor="w",
                      font=("Arial", 14, "bold"))

        box_w = 150
        x0 = w - 12 - box_w
        t1 = c.create_text(x0 + 10, 0, text="Target Milestone", fill=MUTED, anchor="nw", font=("Arial", 8))
        t2 = c.create_text(x0 + 10, 0, text=self.arc_state["milestone"], fill=WHITE, anchor="nw",
                           width=box_w - 20, font=("Arial", 9, "bold"))
        bb = c.bbox(t2)
        bottom = cy + 8
        top = bottom - (10 + 14 + (bb[3] - bb[1]) + 10)
        c.coords(t1, x0 + 10, top + 10)
        c.coords(t2, x0 + 10, top + 24)
        rect = c.create_rectangle(x0, top, x0 + box_w, bottom, fill=PANEL, outline=BORDER)
        c.tag_lower(rect, t1)

    # ------------------------------------------------------------- storage

    def save_to_storage(self):
        payload = {
            "weekly_hours": str(self.weekly_hours_var.get()),
            "target_window": str(self.target_month_var.get()),
            "checked_courses": [c["name"] for c, v in zip(TRACK_DATA, self.course_vars) if v.get()],
            "log": self.log,
        }
        try:
            with open(STORAGE_FILE, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"Storage Sync Error: {e}")

    def load_from_storage(self):
        if not os.path.exists(STORAGE_FILE):
            return
        try:
            with open(STORAGE_FILE) as f:
                p = json.load(f)
            self.weekly_hours_var.set(str(p.get("weekly_hours", "10")))
            self.target_month_var.set(str(p.get("target_window", "Next Month")))
            names = set(p.get("checked_courses", []))
            if not names:  # older save format used positions
                names = {TRACK_DATA[i]["name"] for i in p.get("checked_indexes", [])
                         if isinstance(i, int) and 0 <= i < len(TRACK_DATA)}
            for c, v in zip(TRACK_DATA, self.course_vars):
                if c["name"] in names:
                    v.set(True)
            self.log = [e for e in p.get("log", []) if isinstance(e, dict) and "date" in e and "hours" in e]
        except Exception as e:
            print(f"Storage Read Warning: {e}")


if __name__ == "__main__":
    while True:
        app = AdvancedDataTracker()
        app.mainloop()
        if not app.restart_requested:
            break
        set_course(get_active())