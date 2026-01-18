import tkinter as tk
from tkinter import ttk, messagebox
import api_client as api
from theme import *
from utils import logout
from comments_ui import CommentsPopup

class HelperPage:
    def __init__(self, root):
        self.root = root

        self.frame = tk.Frame(root, bg=BG_MAIN)
        self.frame.pack(fill="both", expand=True)

        tk.Label(
            self.frame,
            text="Helper Dashboard",
            font=FONT_TITLE,
            bg=BG_MAIN,
            fg=PRIMARY
        ).pack(pady=20)

        dark_button(self.frame, "Assigned Tickets", self.view_assigned_tickets).pack(pady=6)
        dark_button(self.frame, "Update Status", self.update_ticket_status).pack(pady=6)
        dark_button(
            self.frame,
            "Logout",
            lambda: self._logout(),
            color=DANGER
        ).pack(pady=20)

    # ---------------- ASSIGNED TICKETS ----------------
    def view_assigned_tickets(self):
        res = api.get_tickets()

        if res.status_code != 200:
            messagebox.showerror("Error", "Failed to load assigned tickets")
            return

        apply_dark_treeview()

        win = tk.Toplevel(self.root)
        win.title("Assigned Tickets")
        win.geometry("900x450")
        win.configure(bg=BG_MAIN)

        tree = ttk.Treeview(
            win,
            columns=("ID", "Title", "Status", "Priority"),
            show="headings",
            selectmode="browse"
        )

        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=200)

        for t in res.json():
            tree.insert(
                "",
                "end",
                values=(
                    t["id"],
                    t["title"],
                    t["status"],
                    t["priority"]
                )
            )

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # -------- COMMENTS BUTTON --------
        def open_comments():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select", "Select a ticket first")
                return

            ticket_id = tree.item(selected[0])["values"][0]
            CommentsPopup(self.root, ticket_id, role="helper")

        dark_button(win, "💬 View / Add Comments", open_comments).pack(pady=10)

    # ---------------- UPDATE STATUS ----------------
    def update_ticket_status(self):
        win = tk.Toplevel(self.root)
        win.title("Update Ticket Status")
        win.geometry("420x320")
        win.configure(bg=BG_MAIN)

        tickets_res = api.get_tickets()
        if tickets_res.status_code != 200:
            messagebox.showerror("Error", "Failed to load tickets")
            return

        tk.Label(
            win,
            text="Select Ticket",
            bg=BG_MAIN,
            fg=TEXT_SUB,
            font=FONT_SUB
        ).pack(pady=5)

        ticket_box = ttk.Combobox(
            win,
            values=[f"{t['id']} - {t['title']}" for t in tickets_res.json()],
            width=42
        )
        ticket_box.pack()

        tk.Label(
            win,
            text="Select Status",
            bg=BG_MAIN,
            fg=TEXT_SUB,
            font=FONT_SUB
        ).pack(pady=5)

        status_box = ttk.Combobox(
            win,
            values=["Open", "In Progress", "Resolved", "On Hold"],
            width=30
        )
        status_box.pack()

        def update():
            if not ticket_box.get() or not status_box.get():
                messagebox.showwarning("Missing", "Select ticket and status")
                return

            ticket_id = int(ticket_box.get().split(" - ")[0])
            res = api.update_ticket(ticket_id, status_box.get())

            if res.status_code == 200:
                messagebox.showinfo("Success", "Ticket status updated")
                win.destroy()
            else:
                messagebox.showerror("Error", res.text)

        dark_button(win, "Update", update).pack(pady=20)

    # ---------------- LOGOUT ----------------
    def _logout(self):
        logout(self.frame)
        from auth_ui import LoginPage   # lazy import avoids circular issue
        LoginPage(self.root)
