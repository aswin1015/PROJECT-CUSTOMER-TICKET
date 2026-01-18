import tkinter as tk
from tkinter import ttk, messagebox
import api_client as api
from theme import *
from utils import logout
from comments_ui import CommentsPopup


class AdminPage:
    def __init__(self, root):
        self.root = root

        self.frame = tk.Frame(root, bg=BG_MAIN)
        self.frame.pack(fill="both", expand=True)

        tk.Label(
            self.frame,
            text="Admin Dashboard",
            font=FONT_TITLE,
            bg=BG_MAIN,
            fg=PRIMARY
        ).pack(pady=20)

        dark_button(self.frame, "View Users", self.users).pack(pady=6)
        dark_button(self.frame, "Assign Ticket", self.assign_ticket_ui).pack(pady=6)
        dark_button(self.frame, "View Tickets", self.view_tickets).pack(pady=6)
        dark_button(self.frame, "Update Ticket Status", self.update_ticket_status).pack(pady=6)
        dark_button(self.frame, "Analytics", self.analytics, color=SUCCESS).pack(pady=6)

        dark_button(
            self.frame,
            "Logout",
            lambda: self._logout(),
            color=DANGER
        ).pack(pady=20)

    # ---------------- USERS ----------------
    def users(self):
        res = api.get_users()
        if res.status_code != 200:
            messagebox.showerror("Error", "Failed to load users")
            return

        apply_dark_treeview()

        win = tk.Toplevel(self.root)
        win.title("Users")
        win.configure(bg=BG_MAIN)

        tree = ttk.Treeview(
            win,
            columns=("Email", "Name", "Role"),
            show="headings"
        )

        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=200)

        for u in res.json():
            tree.insert("", "end", values=(u["email"], u["name"], u["role"]))

        tree.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------- ASSIGN TICKET ----------------
    def assign_ticket_ui(self):
        apply_dark_treeview()

        win = tk.Toplevel(self.root)
        win.title("Assign Ticket")
        win.geometry("600x400")
        win.configure(bg=BG_MAIN)

        tickets_res = api.get_tickets()
        helpers_res = api.get_helpers()

        if tickets_res.status_code != 200 or helpers_res.status_code != 200:
            messagebox.showerror("Error", "Failed to load tickets or helpers")
            return

        tk.Label(win, text="Select Ticket", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack(pady=5)
        ticket_box = ttk.Combobox(
            win,
            values=[f"{t['id']} - {t['title']}" for t in tickets_res.json()],
            width=55
        )
        ticket_box.pack()

        tk.Label(win, text="Select Helper", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack(pady=5)
        helper_box = ttk.Combobox(
            win,
            values=[h["email"] for h in helpers_res.json()],
            width=55
        )
        helper_box.pack()

        def assign():
            if not ticket_box.get() or not helper_box.get():
                messagebox.showwarning("Missing", "Select ticket and helper")
                return

            ticket_id = int(ticket_box.get().split(" - ")[0])
            res = api.assign_ticket(ticket_id, helper_box.get())

            if res.status_code == 200:
                messagebox.showinfo("Success", "Ticket assigned successfully")
                win.destroy()
            else:
                messagebox.showerror("Error", res.text)

        dark_button(win, "Assign Ticket", assign).pack(pady=20)

    # ---------------- VIEW TICKETS ----------------
    def view_tickets(self):
        res = api.get_tickets()
        if res.status_code != 200:
            messagebox.showerror("Error", "Failed to load tickets")
            return

        apply_dark_treeview()

        win = tk.Toplevel(self.root)
        win.title("All Tickets")
        win.geometry("950x500")
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
                values=(t["id"], t["title"], t["status"], t["priority"], t["assigned_to"])
            )

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # -------- DELETE --------
        def delete_selected():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select", "Select a ticket first")
                return

            ticket_id = tree.item(selected[0])["values"][0]

            if not messagebox.askyesno("Confirm Delete", f"Delete Ticket #{ticket_id}?"):
                return

            res = api.delete_ticket(ticket_id)
            if res.status_code == 200:
                tree.delete(selected[0])
                messagebox.showinfo("Deleted", "Ticket deleted")
            else:
                messagebox.showerror("Error", res.text)

        # -------- COMMENTS --------
        def open_comments():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Select", "Select a ticket first")
                return

            ticket_id = tree.item(selected[0])["values"][0]
            CommentsPopup(self.root, ticket_id, role="admin")

        btn_frame = tk.Frame(win, bg=BG_MAIN)
        btn_frame.pack(pady=10)

        dark_button(btn_frame, "💬 Comments", open_comments).pack(side="left", padx=10)
        dark_button(btn_frame, "🗑 Delete", delete_selected, color=DANGER).pack(side="left", padx=10)

    # ---------------- UPDATE STATUS ----------------
    def update_ticket_status(self):
        win = tk.Toplevel(self.root)
        win.title("Update Ticket Status")
        win.geometry("400x320")
        win.configure(bg=BG_MAIN)

        tickets_res = api.get_tickets()
        if tickets_res.status_code != 200:
            messagebox.showerror("Error", "Failed to load tickets")
            return

        tk.Label(win, text="Select Ticket", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack(pady=5)
        ticket_box = ttk.Combobox(
            win,
            values=[f"{t['id']} - {t['title']}" for t in tickets_res.json()],
            width=40
        )
        ticket_box.pack()

        tk.Label(win, text="Select Status", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack(pady=5)
        status_box = ttk.Combobox(
            win,
            values=["Open", "In Progress", "Resolved", "Closed", "On Hold"],
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

    # ---------------- ANALYTICS ----------------
    def analytics(self):
        win = tk.Toplevel(self.root)
        win.title("Analytics Dashboard")
        win.geometry("500x400")
        win.configure(bg=BG_MAIN)

        stats_res = api.get_stats()
        perf_res = api.get_performance()

        if stats_res.status_code != 200:
            messagebox.showerror("Error", "Failed to load analytics")
            return

        tk.Label(win, text="Ticket Statistics", font=FONT_SUB, bg=BG_MAIN, fg=PRIMARY).pack(pady=10)

        for k, v in stats_res.json().items():
            tk.Label(win, text=f"{k}: {v}", bg=BG_MAIN, fg=TEXT_MAIN).pack(anchor="w", padx=15)

        if perf_res.status_code == 200:
            tk.Label(win, text="\nStaff Performance", font=FONT_SUB, bg=BG_MAIN, fg=PRIMARY).pack(pady=10)
            for s in perf_res.json():
                tk.Label(
                    win,
                    text=f"{s['name']} | Active: {s['active_tickets']} | Total: {s['total_handled']}",
                    bg=BG_MAIN,
                    fg=TEXT_MAIN
                ).pack(anchor="w", padx=15)

    # ---------------- LOGOUT ----------------
    def _logout(self):
        logout(self.frame)
        from auth_ui import LoginPage  # lazy import to avoid circular issue
        LoginPage(self.root)
