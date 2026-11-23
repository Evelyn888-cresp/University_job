"""Desktop GUI for the University Job Opportunities Management System.

The GUI is built with Tkinter and does not connect to MySQL directly:
every action sends an HTTP request to the Flask API (app.py).

Run the API first (python app.py), then run:  python gui.py
"""
import datetime
import tkinter as tk
from tkinter import messagebox, ttk

import requests

API_URL = "http://127.0.0.1:5000/api"  # 127.0.0.1 is faster than localhost on Windows
STATUSES = ["Pending", "Under Review", "Accepted", "Rejected"]

# Colors and fonts of the interface
GREEN = "#2F5D50"
GREEN_DARK = "#234a3f"
BACKGROUND = "#F3F5F1"
SURFACE = "#FFFFFF"
LINE = "#C9D2C7"
TEXT = "#1E2B26"
QUIET = "#5B6B64"
ERROR_RED = "#A23B2A"
STATUS_COLORS = {
    "Pending": "#FFF4D6",
    "Under Review": "#E2ECF7",
    "Accepted": "#DFF0E3",
    "Rejected": "#F6E0DB",
}
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 15, "bold")


# ------------------------------------------------------------
# API client: all the communication with the Flask API
# ------------------------------------------------------------
class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def _send(self, method, path, data=None):
        try:
            response = requests.request(method, self.base_url + path, json=data, timeout=5)
        except requests.ConnectionError:
            raise ApiError("The API is not running. Start it with: python app.py")
        body = response.json()
        if response.status_code >= 400:
            raise ApiError(body.get("error", "Unknown error."))
        return body

    def get(self, path):
        return self._send("GET", path)

    def post(self, path, data):
        return self._send("POST", path, data)

    def put(self, path, data):
        return self._send("PUT", path, data)

    def delete(self, path):
        return self._send("DELETE", path)


# ------------------------------------------------------------
# Reusable widgets
# ------------------------------------------------------------
def make_table(parent, columns, widths, height=12):
    """Create a Treeview table with a scrollbar."""
    frame = ttk.Frame(parent, style="Surface.TFrame")
    table = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    for col, width in zip(columns, widths):
        table.heading(col, text=col)
        table.column(col, width=width, anchor="w")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    table.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, table


def labeled_entry(parent, label, row, widget=None):
    ttk.Label(parent, text=label, style="Form.TLabel").grid(row=row, column=0, sticky="w", pady=(6, 2))
    if widget is None:
        widget = ttk.Entry(parent, width=34)
    widget.grid(row=row + 1, column=0, sticky="we")
    return widget


def set_entry(entry, value):
    entry.delete(0, "end")
    entry.insert(0, "" if value is None else value)


SKILL_CHIP = "#DFF0E3"
AVATAR_COLORS = ["#2F5D50", "#3C6E91", "#8A5A44", "#6B4F8A", "#9A6B1E", "#45707A"]


def initials(full_name):
    parts = [p for p in full_name.split() if p]
    return "".join(p[0].upper() for p in parts[:2]) or "?"


def draw_avatar(canvas, full_name, size):
    """Draw a colored circle with the initials of the person."""
    canvas.delete("all")
    if not full_name.strip():
        canvas.create_oval(2, 2, size - 2, size - 2, fill="#E3E9E2", outline="")
        canvas.create_text(size / 2, size / 2, text="+", fill=QUIET, font=("Segoe UI", int(size / 2.6), "bold"))
        return
    color = AVATAR_COLORS[sum(ord(c) for c in full_name) % len(AVATAR_COLORS)]
    canvas.create_oval(2, 2, size - 2, size - 2, fill=color, outline="")
    canvas.create_text(size / 2, size / 2, text=initials(full_name), fill="white",
                       font=("Segoe UI", int(size / 3.2), "bold"))


class SkillPanel(ttk.Frame):
    """Shows the skills linked to a student or a job offer as chips and lets
    the user add or remove them. Uses the endpoints /api/<owner>/<id>/skills,
    which work on the tables student_skill and job_offer_skill."""

    def __init__(self, parent, api, status, owner, title, on_change=None, per_row=4, compact=False):
        super().__init__(parent, style="Surface.TFrame", padding=12)
        self.api, self.status, self.owner, self.on_change = api, status, owner, on_change
        self.per_row = per_row
        self.table_name = "student_skill" if owner == "students" else "job_offer_skill"
        self.owner_id = None
        self.linked = []
        self.selected = None
        self.available = {}

        ttk.Label(self, text=title, style="FormTitle.TLabel").pack(anchor="w")
        self.hint = ttk.Label(self, text="Select a row to see its skills.", style="Hint.TLabel",
                              wraplength=230 if compact else 600)
        self.hint.pack(anchor="w", pady=(2, 6))

        self.chips = tk.Frame(self, bg=SURFACE, highlightthickness=1, highlightbackground=LINE, height=80)
        self.chips.pack(fill="x")
        self.chips.pack_propagate(False)
        self.chips.grid_propagate(False)

        controls = ttk.Frame(self, style="Surface.TFrame")
        controls.pack(fill="x", pady=(8, 0))
        if compact:
            self.choice = ttk.Combobox(controls, state="readonly", width=24)
            self.choice.pack(fill="x")
            buttons = ttk.Frame(controls, style="Surface.TFrame")
            buttons.pack(fill="x", pady=(6, 0))
            ttk.Button(buttons, text="Add skill", style="Primary.TButton", command=self.add).pack(
                side="left", fill="x", expand=True)
            ttk.Button(buttons, text="Remove", style="Danger.TButton", command=self.remove).pack(
                side="left", fill="x", expand=True, padx=(6, 0))
        else:
            self.choice = ttk.Combobox(controls, state="readonly", width=24)
            self.choice.pack(side="left")
            ttk.Button(controls, text="Add skill", style="Primary.TButton", command=self.add).pack(side="left", padx=(6, 0))
            ttk.Button(controls, text="Remove selected", style="Danger.TButton", command=self.remove).pack(side="left", padx=(6, 0))
        self.draw_chips()

    def draw_chips(self):
        for widget in self.chips.winfo_children():
            widget.destroy()
        if self.owner_id is None:
            tk.Label(self.chips, text="No row selected.", bg=SURFACE, fg=QUIET, font=FONT).grid(
                row=0, column=0, padx=8, pady=8, sticky="w")
            return
        if not self.linked:
            tk.Label(self.chips, text="No skills yet. Choose one below and press Add skill.", bg=SURFACE,
                     fg=QUIET, font=FONT).grid(row=0, column=0, padx=8, pady=8, sticky="w")
            return
        for i, skill in enumerate(self.linked):
            chosen = i == self.selected
            color = GREEN if chosen else SKILL_CHIP
            chip = tk.Frame(self.chips, bg=color, padx=10, pady=3, cursor="hand2")
            chip.grid(row=i // self.per_row, column=i % self.per_row, padx=(6, 0), pady=(6, 0), sticky="w")
            label = tk.Label(chip, text=skill["name"], bg=color, fg="white" if chosen else TEXT,
                             font=FONT, cursor="hand2")
            label.pack()
            for widget in (chip, label):
                widget.bind("<Button-1>", lambda _e, index=i: self.select(index))

    def select(self, index):
        self.selected = index
        self.draw_chips()

    def show(self, owner_id, name):
        self.owner_id = owner_id
        self.hint.configure(text=f"Skills of {name}, saved in the table {self.table_name}. "
                                 "Click a skill to select it.")
        self.refresh()

    def clear(self):
        self.owner_id = None
        self.linked = []
        self.selected = None
        self.choice.set("")
        self.choice.configure(values=[])
        self.hint.configure(text="Select a row to see its skills.")
        self.draw_chips()

    def refresh(self):
        if self.owner_id is None:
            return
        try:
            self.linked = self.api.get(f"/{self.owner}/{self.owner_id}/skills")
            catalog = self.api.get("/skills")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.selected = None
        linked_ids = {s["skill_id"] for s in self.linked}
        self.available = {s["name"]: s["skill_id"] for s in catalog if s["skill_id"] not in linked_ids}
        self.choice.configure(values=list(self.available))
        self.choice.set("")
        self.draw_chips()

    def after_change(self, message):
        self.status(message)
        self.refresh()
        if self.on_change:
            self.on_change()

    def add(self):
        if self.owner_id is None:
            self.status("Select a row in the table first.", error=True)
            return
        if not self.choice.get():
            self.status("Choose a skill from the list.", error=True)
            return
        name = self.choice.get()
        try:
            self.api.post(f"/{self.owner}/{self.owner_id}/skills", {"skill_id": self.available[name]})
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.after_change(f"Skill {name} added.")

    def remove(self):
        if self.selected is None:
            self.status("Click a skill to select it first.", error=True)
            return
        skill = self.linked[self.selected]
        try:
            self.api.delete(f"/{self.owner}/{self.owner_id}/skills/{skill['skill_id']}")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.after_change(f"Skill {skill['name']} removed.")


# ------------------------------------------------------------
# Students tab: full CRUD + profile card + skills of the student
# ------------------------------------------------------------
class StudentsTab(ttk.Frame):
    def __init__(self, parent, api, status):
        super().__init__(parent, style="Page.TFrame", padding=16)
        self.api = api
        self.status = status
        self.selected_id = None
        self.students = []

        left = ttk.Frame(self, style="Page.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        search_row = ttk.Frame(left, style="Page.TFrame")
        search_row.pack(fill="x", pady=(0, 8))
        ttk.Label(search_row, text="Search", style="Page.TLabel").pack(side="left")
        self.search = ttk.Entry(search_row, width=30)
        self.search.pack(side="left", padx=(8, 0))
        self.search.bind("<KeyRelease>", lambda _e: self.fill_table())
        self.count = ttk.Label(search_row, text="", style="PageHint.TLabel")
        self.count.pack(side="right")

        table_frame, self.table = make_table(
            left, ("ID", "Name", "Last name", "Email", "Academic program"),
            (40, 95, 95, 210, 170), height=8
        )
        table_frame.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        self.skills = SkillPanel(left, api, status, "students", "Skills of the student")
        self.skills.pack(fill="x", pady=(12, 0))

        form = ttk.Frame(self, style="Surface.TFrame", padding=16)
        form.grid(row=0, column=1, sticky="n")

        card = ttk.Frame(form, style="Surface.TFrame")
        card.grid(row=0, column=0, sticky="we", pady=(0, 6))
        self.avatar = tk.Canvas(card, width=56, height=56, bg=SURFACE, highlightthickness=0)
        self.avatar.pack(side="left")
        names = ttk.Frame(card, style="Surface.TFrame")
        names.pack(side="left", padx=(10, 0))
        self.card_name = ttk.Label(names, text="New student", style="FormTitle.TLabel")
        self.card_name.pack(anchor="w")
        self.card_info = ttk.Label(names, text="Fill in the form and press Save.", style="Hint.TLabel")
        self.card_info.pack(anchor="w")

        self.name = labeled_entry(form, "Name", 1)
        self.last_name = labeled_entry(form, "Last name", 3)
        self.email = labeled_entry(form, "Email", 5)
        self.program = labeled_entry(form, "Academic program", 7)

        buttons = ttk.Frame(form, style="Surface.TFrame")
        buttons.grid(row=9, column=0, sticky="we", pady=(14, 0))
        ttk.Button(buttons, text="Save student", style="Primary.TButton", command=self.save).pack(fill="x")
        ttk.Button(buttons, text="New student", command=self.clear).pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Delete student", style="Danger.TButton", command=self.delete).pack(fill="x", pady=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        draw_avatar(self.avatar, "", 56)
        self.load()

    def load(self):
        try:
            self.students = self.api.get("/students")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.fill_table()
        self.skills.refresh()

    def fill_table(self):
        text = self.search.get().strip().lower()
        self.table.delete(*self.table.get_children())
        shown = 0
        for s in self.students:
            row_text = f"{s['name']} {s['last_name']} {s['email']} {s['academic_program']}".lower()
            if text and text not in row_text:
                continue
            self.table.insert("", "end", iid=s["student_id"], values=(
                s["student_id"], s["name"], s["last_name"], s["email"], s["academic_program"]))
            shown += 1
        self.count.configure(text=f"{shown} of {len(self.students)} students")

    def on_select(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        student = next(s for s in self.students if s["student_id"] == self.selected_id)
        set_entry(self.name, student["name"])
        set_entry(self.last_name, student["last_name"])
        set_entry(self.email, student["email"])
        set_entry(self.program, student["academic_program"])
        full_name = f"{student['name']} {student['last_name']}"
        draw_avatar(self.avatar, full_name, 56)
        self.card_name.configure(text=full_name)
        self.card_info.configure(text=student["academic_program"])
        self.skills.show(self.selected_id, full_name)

    def form_data(self):
        return {
            "name": self.name.get().strip(),
            "last_name": self.last_name.get().strip(),
            "email": self.email.get().strip(),
            "academic_program": self.program.get().strip(),
        }

    def save(self):
        data = self.form_data()
        try:
            if self.selected_id is None:
                created = self.api.post("/students", data)
                self.status(f"Student {created['name']} {created['last_name']} created.")
            else:
                self.api.put(f"/students/{self.selected_id}", data)
                self.status(f"Student {self.selected_id} updated.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.clear()
        self.load()

    def delete(self):
        if self.selected_id is None:
            self.status("Select a student in the table first.", error=True)
            return
        if not messagebox.askyesno("Delete student", "Delete the selected student?"):
            return
        try:
            self.api.delete(f"/students/{self.selected_id}")
            self.status(f"Student {self.selected_id} deleted.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.clear()
        self.load()

    def clear(self):
        self.selected_id = None
        self.table.selection_remove(*self.table.selection())
        for entry in (self.name, self.last_name, self.email, self.program):
            entry.delete(0, "end")
        draw_avatar(self.avatar, "", 56)
        self.card_name.configure(text="New student")
        self.card_info.configure(text="Fill in the form and press Save.")
        self.skills.clear()


# ------------------------------------------------------------
# Job offers tab: full CRUD + required skills + matching candidates
# ------------------------------------------------------------
class JobOffersTab(ttk.Frame):
    def __init__(self, parent, api, status):
        super().__init__(parent, style="Page.TFrame", padding=16)
        self.api = api
        self.status = status
        self.selected_id = None
        self.companies = {}
        self.offers = {}

        left = ttk.Frame(self, style="Page.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        table_frame, self.table = make_table(
            left, ("ID", "Position", "Company", "Location", "Requirements"),
            (40, 175, 115, 100, 160), height=6
        )
        table_frame.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        bottom = ttk.Frame(left, style="Page.TFrame")
        bottom.pack(fill="x", pady=(12, 0))
        self.skills = SkillPanel(bottom, api, status, "job-offers", "Required skills",
                                 on_change=self.load_candidates, per_row=2, compact=True)
        self.skills.pack(side="left", fill="y")

        match = ttk.Frame(bottom, style="Surface.TFrame", padding=12)
        match.pack(side="left", fill="both", expand=True, padx=(12, 0))
        ttk.Label(match, text="Matching candidates", style="FormTitle.TLabel").pack(anchor="w")
        ttk.Label(match, text="The system compares the skills this offer requires with the skills of "
                              "each student. Has = skills in common, Missing = skills still needed.",
                  style="Hint.TLabel", wraplength=440).pack(anchor="w", pady=(2, 6))
        cand_frame, self.candidates = make_table(match, ("Student", "Match", "Has", "Missing"),
                                                 (105, 55, 170, 120), height=5)
        cand_frame.pack(fill="both", expand=True)

        form = ttk.Frame(self, style="Surface.TFrame", padding=16)
        form.grid(row=0, column=1, sticky="n")
        ttk.Label(form, text="Job offer", style="FormTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.company = labeled_entry(form, "Company", 1, ttk.Combobox(form, state="readonly", width=32))
        self.position = labeled_entry(form, "Position", 3)
        self.location = labeled_entry(form, "Location", 5)
        self.requirements = labeled_entry(form, "Other requirements", 7)
        self.description = labeled_entry(form, "Description", 9)

        buttons = ttk.Frame(form, style="Surface.TFrame")
        buttons.grid(row=11, column=0, sticky="we", pady=(14, 0))
        ttk.Button(buttons, text="Save job offer", style="Primary.TButton", command=self.save).pack(fill="x")
        row = ttk.Frame(buttons, style="Surface.TFrame")
        row.pack(fill="x", pady=(6, 0))
        ttk.Button(row, text="New", command=self.clear).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Delete", style="Danger.TButton", command=self.delete).pack(
            side="left", fill="x", expand=True, padx=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.load()

    def load(self):
        try:
            offers = self.api.get("/job-offers")
            companies = self.api.get("/companies")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.companies = {c["name"]: c["company_id"] for c in companies}
        company_names = {c["company_id"]: c["name"] for c in companies}
        self.company.configure(values=list(self.companies))
        self.offers = {o["job_offer_id"]: o for o in offers}
        self.table.delete(*self.table.get_children())
        for o in offers:
            self.table.insert("", "end", iid=o["job_offer_id"], values=(
                o["job_offer_id"], o["position"], company_names.get(o["company_id"], ""),
                o["location"] or "", o["requirements"] or ""))
        if self.selected_id in self.offers:
            self.skills.refresh()
            self.load_candidates()

    def on_select(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        offer = self.offers[self.selected_id]
        company = next((name for name, cid in self.companies.items() if cid == offer["company_id"]), "")
        self.company.set(company)
        set_entry(self.position, offer["position"])
        set_entry(self.location, offer["location"])
        set_entry(self.requirements, offer["requirements"])
        set_entry(self.description, offer["description"])
        self.skills.show(self.selected_id, offer["position"])
        self.load_candidates()

    def load_candidates(self):
        self.candidates.delete(*self.candidates.get_children())
        if self.selected_id is None:
            return
        try:
            rows = self.api.get(f"/job-offers/{self.selected_id}/candidates")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        for r in rows:
            self.candidates.insert("", "end", values=(
                r["student"], f"{r['matching_skills']} of {r['required_skills']}", r["skills"],
                r["missing"] or "Nothing"))

    def save(self):
        if not self.company.get():
            self.status("Choose the company of the job offer.", error=True)
            return
        data = {
            "company_id": self.companies[self.company.get()],
            "position": self.position.get().strip(),
            "location": self.location.get().strip() or None,
            "requirements": self.requirements.get().strip() or None,
            "description": self.description.get().strip() or None,
        }
        try:
            if self.selected_id is None:
                created = self.api.post("/job-offers", data)
                self.status(f"Job offer {created['position']} created.")
            else:
                self.api.put(f"/job-offers/{self.selected_id}", data)
                self.status(f"Job offer {self.selected_id} updated.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.clear()
        self.load()

    def delete(self):
        if self.selected_id is None:
            self.status("Select a job offer in the table first.", error=True)
            return
        if not messagebox.askyesno("Delete job offer", "Delete the selected job offer?"):
            return
        try:
            self.api.delete(f"/job-offers/{self.selected_id}")
            self.status(f"Job offer {self.selected_id} deleted.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.clear()
        self.load()

    def clear(self):
        self.selected_id = None
        self.table.selection_remove(*self.table.selection())
        self.company.set("")
        for entry in (self.position, self.location, self.requirements, self.description):
            entry.delete(0, "end")
        self.skills.clear()
        self.candidates.delete(*self.candidates.get_children())


# ------------------------------------------------------------
# Applications tab: create, read, update status, delete
# ------------------------------------------------------------
class ApplicationsTab(ttk.Frame):
    def __init__(self, parent, api, status):
        super().__init__(parent, style="Page.TFrame", padding=16)
        self.api = api
        self.status = status
        self.selected_id = None
        self.students = {}
        self.offers = {}

        left = ttk.Frame(self, style="Page.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        table_frame, self.table = make_table(
            left, ("ID", "Student", "Position", "Company", "Date", "Status"), (35, 120, 170, 105, 85, 95), height=16
        )
        table_frame.pack(fill="both", expand=True)
        for status_name, color in STATUS_COLORS.items():
            self.table.tag_configure(status_name, background=color)
        self.table.bind("<<TreeviewSelect>>", self.on_select)
        legend = ttk.Frame(left, style="Page.TFrame")
        legend.pack(anchor="w", pady=(8, 0))
        for status_name, color in STATUS_COLORS.items():
            tk.Label(legend, text=f"  {status_name}  ", bg=color, fg=TEXT, font=FONT).pack(side="left", padx=(0, 6))

        form = ttk.Frame(self, style="Surface.TFrame", padding=16)
        form.grid(row=0, column=1, sticky="n")
        ttk.Label(form, text="Application", style="FormTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.student = labeled_entry(form, "Student", 1, ttk.Combobox(form, state="readonly", width=32))
        self.offer = labeled_entry(form, "Job offer", 3, ttk.Combobox(form, state="readonly", width=32))
        self.date = labeled_entry(form, "Date (YYYY-MM-DD)", 5)
        self.state = labeled_entry(form, "Status", 7, ttk.Combobox(form, values=STATUSES, state="readonly", width=32))
        self.comments = labeled_entry(form, "Comments", 9)

        buttons = ttk.Frame(form, style="Surface.TFrame")
        buttons.grid(row=11, column=0, sticky="we", pady=(16, 0))
        ttk.Button(buttons, text="Create application", style="Primary.TButton", command=self.create).pack(fill="x")
        ttk.Button(buttons, text="Update status", command=self.update_status).pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Delete application", style="Danger.TButton", command=self.delete).pack(fill="x", pady=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.load()

    def load(self):
        try:
            rows = self.api.get("/applications/details")
            students = self.api.get("/students")
            offers = self.api.get("/job-offers")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.table.delete(*self.table.get_children())
        for a in rows:
            self.table.insert("", "end", iid=a["application_id"], tags=(a["status"],), values=(
                a["application_id"], a["student"], a["position"], a["company"], a["application_date"], a["status"]))
        self.students = {f"{s['name']} {s['last_name']}": s["student_id"] for s in students}
        self.offers = {f"{o['job_offer_id']}. {o['position']}": o["job_offer_id"] for o in offers}
        self.student.configure(values=list(self.students))
        self.offer.configure(values=list(self.offers))
        self.reset_form()

    def reset_form(self):
        self.selected_id = None
        self.student.set("")
        self.offer.set("")
        self.state.set("Pending")
        set_entry(self.date, datetime.date.today().isoformat())
        self.comments.delete(0, "end")

    def on_select(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        _id, student, position, _company, date, status = self.table.item(selection[0], "values")
        self.student.set(student)
        self.offer.set(next((label for label in self.offers if label.endswith(position)), ""))
        set_entry(self.date, date)
        self.state.set(status)

    def create(self):
        if not self.student.get() or not self.offer.get():
            self.status("Choose a student and a job offer.", error=True)
            return
        data = {
            "student_id": self.students[self.student.get()],
            "job_offer_id": self.offers[self.offer.get()],
            "application_date": self.date.get().strip(),
            "status": self.state.get(),
            "comments": self.comments.get().strip() or None,
        }
        try:
            created = self.api.post("/applications", data)
            self.status(f"Application {created['application_id']} created.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.load()

    def update_status(self):
        if self.selected_id is None:
            self.status("Select an application in the table first.", error=True)
            return
        try:
            self.api.put(f"/applications/{self.selected_id}", {"status": self.state.get()})
            self.status(f"Application {self.selected_id} changed to {self.state.get()}.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.load()

    def delete(self):
        if self.selected_id is None:
            self.status("Select an application in the table first.", error=True)
            return
        if not messagebox.askyesno("Delete application", "Delete the selected application?"):
            return
        try:
            self.api.delete(f"/applications/{self.selected_id}")
            self.status(f"Application {self.selected_id} deleted.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.load()


# ------------------------------------------------------------
# Simple CRUD tab, used for companies and skills
# ------------------------------------------------------------
class SimpleCrudTab(ttk.Frame):
    def __init__(self, parent, api, status, resource, title, pk, fields, widths, height=16):
        """fields = list of (column, label) shown in the table and the form."""
        super().__init__(parent, style="Page.TFrame", padding=16)
        self.api, self.status = api, status
        self.resource, self.title, self.pk, self.fields = resource, title, pk, fields
        self.selected_id = None

        left = ttk.Frame(self, style="Page.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.build_left(left)
        columns = ["ID"] + [field[1] for field in fields]
        table_frame, self.table = make_table(left, columns, widths, height=height)
        table_frame.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self.on_select)
        self.build_bottom(left)

        form = ttk.Frame(self, style="Surface.TFrame", padding=16)
        form.grid(row=0, column=1, sticky="n")
        ttk.Label(form, text=title, style="FormTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.entries = {}
        for i, field in enumerate(fields):
            col, label = field[0], field[1]
            widget = ttk.Combobox(form, values=field[2], width=32) if len(field) > 2 else None
            self.entries[col] = labeled_entry(form, label, 1 + 2 * i, widget)

        buttons = ttk.Frame(form, style="Surface.TFrame")
        buttons.grid(row=1 + 2 * len(fields), column=0, sticky="we", pady=(16, 0))
        ttk.Button(buttons, text=f"Save {title.lower()}", style="Primary.TButton", command=self.save).pack(fill="x")
        ttk.Button(buttons, text=f"New {title.lower()}", command=self.clear).pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text=f"Delete {title.lower()}", style="Danger.TButton", command=self.delete).pack(fill="x", pady=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.load()

    def build_left(self, left):
        """Hook for subclasses: widgets above the table."""

    def build_bottom(self, left):
        """Hook for subclasses: widgets below the table."""

    def load(self):
        try:
            rows = self.api.get(f"/{self.resource}")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.table.delete(*self.table.get_children())
        for r in rows:
            values = [r[self.pk]] + ["" if r[field[0]] is None else r[field[0]] for field in self.fields]
            self.table.insert("", "end", iid=r[self.pk], values=values)

    def on_select(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        values = self.table.item(selection[0], "values")
        for field, value in zip(self.fields, values[1:]):
            set_entry(self.entries[field[0]], value)

    def save(self):
        data = {field[0]: self.entries[field[0]].get().strip() or None for field in self.fields}
        try:
            if self.selected_id is None:
                self.api.post(f"/{self.resource}", data)
                self.status(f"{self.title} created.")
            else:
                self.api.put(f"/{self.resource}/{self.selected_id}", data)
                self.status(f"{self.title} {self.selected_id} updated.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.clear()
        self.load()

    def delete(self):
        if self.selected_id is None:
            self.status(f"Select a {self.title.lower()} in the table first.", error=True)
            return
        if not messagebox.askyesno(f"Delete {self.title.lower()}", f"Delete the selected {self.title.lower()}?"):
            return
        try:
            self.api.delete(f"/{self.resource}/{self.selected_id}")
            self.status(f"{self.title} {self.selected_id} deleted.")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.clear()
        self.load()

    def clear(self):
        self.selected_id = None
        self.table.selection_remove(*self.table.selection())
        for entry in self.entries.values():
            entry.delete(0, "end")


# ------------------------------------------------------------
# Skills tab: CRUD + explanation + who has / requires the skill
# ------------------------------------------------------------
HOW_SKILLS_WORK = (
    "1. Catalog: this tab lists every skill (table skill).\n"
    "2. Students: each student is linked to the skills they have (table student_skill), "
    "in the Students tab.\n"
    "3. Job offers: each offer is linked to the skills it requires (table job_offer_skill), "
    "in the Job offers tab.\n"
    "4. Matching: in Job offers, the system compares both lists and ranks the students "
    "by the number of skills in common."
)


class SkillsTab(SimpleCrudTab):
    def __init__(self, parent, api, status):
        self.usage_students = None
        super().__init__(parent, api, status, "skills", "Skill", "skill_id",
                         [("name", "Name"), ("description", "Description")], (50, 160, 300), height=6)

    def build_left(self, left):
        info = tk.Frame(left, bg="#E8F1EC", padx=14, pady=10)
        info.pack(fill="x", pady=(0, 12))
        tk.Label(info, text="How skills work", bg="#E8F1EC", fg=GREEN,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(info, text=HOW_SKILLS_WORK, bg="#E8F1EC", fg=TEXT, font=FONT, justify="left",
                 wraplength=740).pack(anchor="w", pady=(4, 0))

    def build_bottom(self, left):
        usage = ttk.Frame(left, style="Page.TFrame")
        usage.pack(fill="both", expand=True, pady=(12, 0))
        box1 = ttk.Frame(usage, style="Surface.TFrame", padding=12)
        box1.pack(side="left", fill="both", expand=True)
        self.usage_title_students = ttk.Label(box1, text="Students who have it", style="FormTitle.TLabel")
        self.usage_title_students.pack(anchor="w")
        ttk.Label(box1, text="Table student_skill", style="Hint.TLabel").pack(anchor="w", pady=(0, 6))
        frame1, self.usage_students = make_table(box1, ("ID", "Student"), (40, 200), height=4)
        frame1.pack(fill="both", expand=True)

        box2 = ttk.Frame(usage, style="Surface.TFrame", padding=12)
        box2.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.usage_title_offers = ttk.Label(box2, text="Job offers that require it", style="FormTitle.TLabel")
        self.usage_title_offers.pack(anchor="w")
        ttk.Label(box2, text="Table job_offer_skill", style="Hint.TLabel").pack(anchor="w", pady=(0, 6))
        frame2, self.usage_offers = make_table(box2, ("ID", "Position", "Company"), (40, 170, 110), height=4)
        frame2.pack(fill="both", expand=True)

    def on_select(self, _event=None):
        super().on_select(_event)
        if self.selected_id is None:
            return
        try:
            students = self.api.get(f"/skills/{self.selected_id}/students")
            offers = self.api.get(f"/skills/{self.selected_id}/job-offers")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        name = self.table.item(str(self.selected_id), "values")[1]
        self.usage_title_students.configure(text=f"Students who have {name}")
        self.usage_title_offers.configure(text=f"Job offers that require {name}")
        self.usage_students.delete(*self.usage_students.get_children())
        for r in students:
            self.usage_students.insert("", "end", values=(r["student_id"], r["student"]))
        self.usage_offers.delete(*self.usage_offers.get_children())
        for r in offers:
            self.usage_offers.insert("", "end", values=(r["job_offer_id"], r["position"], r["company"]))

    def clear(self):
        super().clear()
        if self.usage_students is not None:
            self.usage_title_students.configure(text="Students who have it")
            self.usage_title_offers.configure(text="Job offers that require it")
            self.usage_students.delete(*self.usage_students.get_children())
            self.usage_offers.delete(*self.usage_offers.get_children())


# ------------------------------------------------------------
# Main window
# ------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("University Job Opportunities")
        self.geometry("1200x800")
        self.minsize(1120, 760)
        self.configure(bg=BACKGROUND)
        self.setup_style()

        header = tk.Frame(self, bg=GREEN, padx=20, pady=10)
        header.pack(fill="x")
        titles = tk.Frame(header, bg=GREEN)
        titles.pack(side="left")
        tk.Label(titles, text="University Job Opportunities", font=FONT_TITLE, bg=GREEN, fg="white").pack(anchor="w")
        tk.Label(titles, text="Administration panel: students, job offers, skills, and applications",
                 font=FONT, bg=GREEN, fg="#D6E4DD").pack(anchor="w")
        ttk.Button(header, text="Refresh data", style="Header.TButton", command=self.refresh).pack(side="right")
        stats = tk.Frame(header, bg=GREEN)
        stats.pack(side="right", padx=(0, 20))
        self.stats = {}
        for key, label in (("students", "Students"), ("companies", "Companies"), ("job_offers", "Job offers"),
                           ("applications", "Applications"), ("skills", "Skills")):
            box = tk.Frame(stats, bg=GREEN_DARK, padx=12, pady=4)
            box.pack(side="left", padx=(6, 0))
            number = tk.Label(box, text="-", font=("Segoe UI", 13, "bold"), bg=GREEN_DARK, fg="white")
            number.pack()
            tk.Label(box, text=label, font=("Segoe UI", 8), bg=GREEN_DARK, fg="#D6E4DD").pack()
            self.stats[key] = number

        self.status_bar = tk.Label(self, text="Connected to " + API_URL, anchor="w", font=FONT,
                                   bg=SURFACE, fg=TEXT, padx=20, pady=6, relief="flat")
        self.status_bar.pack(side="bottom", fill="x")

        api = ApiClient(API_URL)
        self.api = api
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        self.tabs = [
            ("Students", StudentsTab(notebook, api, self.show_status)),
            ("Job offers", JobOffersTab(notebook, api, self.show_status)),
            ("Applications", ApplicationsTab(notebook, api, self.show_status)),
            ("Companies", SimpleCrudTab(notebook, api, self.show_status, "companies", "Company", "company_id",
                                        [("name", "Name"), ("email", "Email"), ("phone", "Phone")],
                                        (50, 220, 300, 160))),
            ("Skills", SkillsTab(notebook, api, self.show_status)),
        ]
        for name, tab in self.tabs:
            notebook.add(tab, text=name)
        notebook.bind("<<NotebookTabChanged>>", lambda _e: self.refresh_current(notebook))
        self.load_stats()

    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=FONT, background=BACKGROUND, foreground=TEXT)
        style.configure("Page.TFrame", background=BACKGROUND)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("Page.TLabel", background=BACKGROUND, font=FONT_BOLD)
        style.configure("PageHint.TLabel", background=BACKGROUND, foreground=QUIET)
        style.configure("Form.TLabel", background=SURFACE, font=FONT_BOLD)
        style.configure("FormTitle.TLabel", background=SURFACE, font=("Segoe UI", 12, "bold"), foreground=GREEN)
        style.configure("Hint.TLabel", background=SURFACE, foreground=QUIET)
        style.configure("TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 6), font=FONT_BOLD)
        style.map("TNotebook.Tab", background=[("selected", SURFACE)], foreground=[("selected", GREEN)])
        style.configure("Treeview", rowheight=26, background=SURFACE, fieldbackground=SURFACE, bordercolor=LINE)
        style.configure("Treeview.Heading", font=FONT_BOLD, background="#E3E9E2", relief="flat")
        style.map("Treeview", background=[("selected", "#C9DDD3")], foreground=[("selected", TEXT)])
        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", background=GREEN, foreground="white", font=FONT_BOLD)
        style.map("Primary.TButton", background=[("active", GREEN_DARK)])
        style.configure("Danger.TButton", foreground=ERROR_RED)
        style.configure("Header.TButton", padding=(10, 4))

    def show_status(self, message, error=False):
        self.status_bar.configure(text=message, fg=ERROR_RED if error else GREEN)
        if not error:
            self.load_stats()

    def load_stats(self):
        """Show the number of records of each table in the header."""
        try:
            counts = self.api.get("/summary")
        except ApiError:
            return
        for key, label in self.stats.items():
            label.configure(text=str(counts.get(key, "-")))

    def refresh_current(self, notebook):
        """Reload the tab that was just opened, so it shows the latest data."""
        index = notebook.index(notebook.select())
        self.tabs[index][1].load()
        self.load_stats()

    def refresh(self):
        for _name, tab in self.tabs:
            tab.load()
        self.load_stats()
        self.show_status("Data refreshed.")


if __name__ == "__main__":
    App().mainloop()
