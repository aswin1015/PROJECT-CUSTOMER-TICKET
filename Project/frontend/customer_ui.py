import tkinter as tk
import api_client as api
from tkinter import ttk, messagebox
from theme import *
from utils import logout
from comments_ui import CommentsPopup

class CustomerPage:
    def __init__(self, root):
        self.root = root

        self.frame = tk.Frame(root, bg=BG_MAIN)
        self.frame.pack(fill="both", expand=True)

        tk.Label(
            self.frame,
            text="Customer Dashboard",
            font=FONT_TITLE,
            bg=BG_MAIN,
            fg=PRIMARY
        ).pack(pady=20)

        dark_button(self.frame, "Create Ticket", self.create_ticket_ui).pack(pady=6)
        dark_button(self.frame, "View My Tickets", self.view_tickets).pack(pady=6)
        dark_button(
            self.frame,
            "Logout",
            lambda: self._logout(),
            color=DANGER
        ).pack(pady=20)

    # ---------------- CREATE TICKET ----------------
    def create_ticket_ui(self):
        win = tk.Toplevel(self.root)
        win.title("Create Ticket")
        win.geometry("420x380")
        win.configure(bg=BG_MAIN)

        tk.Label(win, text="Title", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack(pady=5)
        title_entry = tk.Entry(
            win,
            width=42,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN
        )
        title_entry.pack()

        tk.Label(win, text="Description", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack(pady=5)
        desc_entry = tk.Text(
            win,
            width=42,
            height=6,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN
        )
        desc_entry.pack()

        tk.Label(win, text="Priority", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack(pady=5)
        priority_box = ttk.Combobox(
            win,
            values=["Low", "Medium", "High", "Critical"],
            width=30
        )
        priority_box.set("Medium")
        priority_box.pack()

        def submit():
            title = title_entry.get()
            desc = desc_entry.get("1.0", tk.END).strip()
            priority = priority_box.get()

            if not title or not desc:
                messagebox.showwarning("Missing", "Title and description are required")
                return

            res = api.create_ticket(title, desc, priority)

            if res.status_code == 200:
                messagebox.showinfo("Success", "Ticket created successfully")
                win.destroy()
            else:
                messagebox.showerror("Error", res.text)

        dark_button(win, "Submit", submit).pack(pady=20)

    # ---------------- VIEW TICKETS ----------------
    def view_tickets(self):
        res = api.get_tickets()

        if res.status_code != 200:
            messagebox.showerror("Error", "Failed to load tickets")
            return

        apply_dark_treeview()

        win = tk.Toplevel(self.root)
        win.title("My Tickets")
        win.geometry("900x450")
        win.configure(bg=BG_MAIN)

        tree = ttk.Treeview(
            win,
            columns=("ID", "Title", "Status", "Priority", "Assigned To"),
            show="headings",
            selectmode="browse"
        )

        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=170)

        for t in res.json():
            tree.insert(
                "",
                "end",
                values=(
                    t["id"],
                    t["title"],
                    t["status"],
                    t["priority"],
                    t["assigned_to"]
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
            CommentsPopup(self.root, ticket_id, role="customer")

        dark_button(win, "💬 View / Add Comments", open_comments).pack(pady=10)

    # ---------------- LOGOUT ----------------
    def _logout(self):
        logout(self.frame)
        from auth_ui import LoginPage   # lazy import avoids circular issue
        LoginPage(self.root)
