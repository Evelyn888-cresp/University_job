"""Desktop GUI for the University Job Opportunities Management System.

The GUI is built with Tkinter and does not connect to MySQL directly:
every action sends an HTTP request to the Flask API (app.py).

Run the API first (python app.py), then run:  python gui.py
"""
import datetime
import tkinter as tk
from tkinter import messagebox, ttk

import requests

API_URL = "http://localhost:5000/api"
STATUSES = ["Pending", "Under Review", "Accepted", "Rejected"]

# Colors and fonts of the interface
GREEN = "#2F5D50"
GREEN_DARK = "#234a3f"
BACKGROUND = "#F3F5F1"
SURFACE = "#FFFFFF"
LINE = "#C9D2C7"
TEXT = "#1E2B26"
ERROR_RED = "#A23B2A"
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
def make_table(parent, columns, widths):
    """Create a Treeview table with a scrollbar."""
    frame = ttk.Frame(parent, style="Surface.TFrame")
    table = ttk.Treeview(frame, columns=columns, show="headings", height=16)
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


# ------------------------------------------------------------
# Students tab: full CRUD
# ------------------------------------------------------------
class StudentsTab(ttk.Frame):
    def __init__(self, parent, api, status):
        super().__init__(parent, style="Page.TFrame", padding=16)
        self.api = api
        self.status = status
        self.selected_id = None

        table_frame, self.table = make_table(
            self, ("ID", "Name", "Last name", "Email", "Academic program"), (40, 90, 90, 200, 150)
        )
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        form = ttk.Frame(self, style="Surface.TFrame", padding=16)
        form.grid(row=0, column=1, sticky="n")
        ttk.Label(form, text="Student", style="FormTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.name = labeled_entry(form, "Name", 1)
        self.last_name = labeled_entry(form, "Last name", 3)
        self.email = labeled_entry(form, "Email", 5)
        self.program = labeled_entry(form, "Academic program", 7)

        ttk.Label(form, text="Skills", style="Form.TLabel").grid(row=9, column=0, sticky="w", pady=(10, 2))
        self.skills = ttk.Label(form, text="Select a student to see the skills.", style="Hint.TLabel", wraplength=240)
        self.skills.grid(row=10, column=0, sticky="w")

        buttons = ttk.Frame(form, style="Surface.TFrame")
        buttons.grid(row=11, column=0, sticky="we", pady=(16, 0))
        ttk.Button(buttons, text="Save student", style="Primary.TButton", command=self.save).pack(fill="x")
        ttk.Button(buttons, text="New student", command=self.clear).pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Delete student", style="Danger.TButton", command=self.delete).pack(fill="x", pady=(6, 0))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.load()

    def load(self):
        try:
            students = self.api.get("/students")
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.table.delete(*self.table.get_children())
        for s in students:
            self.table.insert("", "end", iid=s["student_id"], values=(
                s["student_id"], s["name"], s["last_name"], s["email"], s["academic_program"]))

    def on_select(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        values = self.table.item(selection[0], "values")
        for entry, value in zip((self.name, self.last_name, self.email, self.program), values[1:]):
            entry.delete(0, "end")
            entry.insert(0, value)
        try:
            skills = self.api.get(f"/students/{self.selected_id}/skills")
            text = ", ".join(s["name"] for s in skills) or "No skills registered."
        except ApiError as exc:
            text = str(exc)
        self.skills.configure(text=text)

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
        self.skills.configure(text="Select a student to see the skills.")


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

        table_frame, self.table = make_table(
            self, ("ID", "Student", "Position", "Company", "Date", "Status"), (35, 110, 165, 100, 85, 95)
        )
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.table.bind("<<TreeviewSelect>>", self.on_select)

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
            self.table.insert("", "end", iid=a["application_id"], values=(
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
        self.date.delete(0, "end")
        self.date.insert(0, datetime.date.today().isoformat())
        self.comments.delete(0, "end")

    def on_select(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        _id, student, position, _company, date, status = self.table.item(selection[0], "values")
        self.student.set(student)
        offer_label = next((label for label in self.offers if label.endswith(position)), "")
        self.offer.set(offer_label)
        self.date.delete(0, "end")
        self.date.insert(0, date)
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
# Companies and job offers tabs: read only (in this stage)
# ------------------------------------------------------------
class ReadOnlyTab(ttk.Frame):
    def __init__(self, parent, api, status, path, columns, keys, widths, note):
        super().__init__(parent, style="Page.TFrame", padding=16)
        self.api, self.status, self.path, self.keys = api, status, path, keys
        table_frame, self.table = make_table(self, columns, widths)
        table_frame.pack(fill="both", expand=True)
        ttk.Label(self, text=note, style="Hint.TLabel").pack(anchor="w", pady=(8, 0))
        self.load()

    def load(self):
        try:
            rows = self.api.get(self.path)
        except ApiError as exc:
            self.status(str(exc), error=True)
            return
        self.table.delete(*self.table.get_children())
        for r in rows:
            self.table.insert("", "end", values=[r[k] if r[k] is not None else "" for k in self.keys])


# ------------------------------------------------------------
# Main window
# ------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("University Job Opportunities")
        self.geometry("1080x700")
        self.minsize(980, 660)
        self.configure(bg=BACKGROUND)
        self.setup_style()

        header = tk.Frame(self, bg=GREEN, padx=20, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="University Job Opportunities", font=FONT_TITLE, bg=GREEN, fg="white").pack(side="left")
        ttk.Button(header, text="Refresh data", style="Header.TButton", command=self.refresh).pack(side="right")

        self.status_bar = tk.Label(self, text="Connected to " + API_URL, anchor="w", font=FONT,
                                   bg=SURFACE, fg=TEXT, padx=20, pady=6, relief="flat")
        self.status_bar.pack(side="bottom", fill="x")

        api = ApiClient(API_URL)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)
        self.tabs = [
            StudentsTab(notebook, api, self.show_status),
            ApplicationsTab(notebook, api, self.show_status),
            ReadOnlyTab(notebook, api, self.show_status, "/companies",
                        ("ID", "Name", "Email", "Phone"), ("company_id", "name", "email", "phone"),
                        (50, 200, 260, 140), "Companies can be viewed in this version. Editing will be added in the next stage."),
            ReadOnlyTab(notebook, api, self.show_status, "/job-offers",
                        ("ID", "Company ID", "Position", "Location", "Requirements"),
                        ("job_offer_id", "company_id", "position", "location", "requirements"),
                        (50, 90, 220, 120, 260), "Job offers can be viewed in this version. Editing will be added in the next stage."),
        ]
        for tab, name in zip(self.tabs, ("Students", "Applications", "Companies", "Job offers")):
            notebook.add(tab, text=name)

    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=FONT, background=BACKGROUND, foreground=TEXT)
        style.configure("Page.TFrame", background=BACKGROUND)
        style.configure("Surface.TFrame", background=SURFACE)
        style.configure("Form.TLabel", background=SURFACE, font=FONT_BOLD)
        style.configure("FormTitle.TLabel", background=SURFACE, font=("Segoe UI", 12, "bold"), foreground=GREEN)
        style.configure("Hint.TLabel", background=SURFACE, foreground="#5B6B64")
        style.configure("TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 6), font=FONT_BOLD)
        style.map("TNotebook.Tab", background=[("selected", SURFACE)], foreground=[("selected", GREEN)])
        style.configure("Treeview", rowheight=26, background=SURFACE, fieldbackground=SURFACE, bordercolor=LINE)
        style.configure("Treeview.Heading", font=FONT_BOLD, background="#E3E9E2", relief="flat")
        style.map("Treeview", background=[("selected", "#D8E6DF")], foreground=[("selected", TEXT)])
        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", background=GREEN, foreground="white", font=FONT_BOLD)
        style.map("Primary.TButton", background=[("active", GREEN_DARK)])
        style.configure("Danger.TButton", foreground=ERROR_RED)
        style.configure("Header.TButton", padding=(10, 4))

    def show_status(self, message, error=False):
        self.status_bar.configure(text=message, fg=ERROR_RED if error else GREEN)

    def refresh(self):
        for tab in self.tabs:
            tab.load()
        self.show_status("Data refreshed.")


if __name__ == "__main__":
    App().mainloop()
