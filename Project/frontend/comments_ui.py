import tkinter as tk
from tkinter import messagebox
import api_client as api
from theme import *

class CommentsPopup:
    def __init__(self, root, ticket_id, role):
        self.ticket_id = ticket_id
        self.role = role

        self.win = tk.Toplevel(root)
        self.win.title(f"Comments – Ticket #{ticket_id}")
        self.win.geometry("600x480")
        self.win.configure(bg=BG_MAIN)

        tk.Label(
            self.win,
            text=f"Comments (Ticket #{ticket_id})",
            font=FONT_SUB,
            bg=BG_MAIN,
            fg=PRIMARY
        ).pack(pady=10)

        # -------- Comments display --------
        self.text = tk.Text(
            self.win,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            wrap="word",
            height=15,
            state="disabled"
        )
        self.text.pack(fill="both", expand=True, padx=10)

        # -------- New comment --------
        self.entry = tk.Text(
            self.win,
            height=4,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN
        )
        self.entry.pack(fill="x", padx=10, pady=5)

        # -------- Internal checkbox (admin/helper only) --------
        self.is_internal = tk.BooleanVar(value=False)

        if self.role in ("admin", "helper"):
            tk.Checkbutton(
                self.win,
                text="Internal comment (visible only to staff)",
                variable=self.is_internal,
                bg=BG_MAIN,
                fg=TEXT_SUB,
                selectcolor=BG_CARD,
                activebackground=BG_MAIN
            ).pack(anchor="w", padx=12)

        dark_button(self.win, "Add Comment", self.add_comment).pack(pady=10)

        self.load_comments()

    # -------- Load comments --------
    def load_comments(self):
        res = api.get_comments(self.ticket_id)

        if res.status_code != 200:
            messagebox.showerror("Error", "Failed to load comments")
            return

        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)

        for c in res.json():
            prefix = "[INTERNAL] " if c.get("is_internal") else ""
            self.text.insert(
                tk.END,
                f"{prefix}{c['author']} ({c['created_at']}):\n{c['comment']}\n\n"
            )

        self.text.config(state="disabled")

    # -------- Add comment --------
    def add_comment(self):
        comment = self.entry.get("1.0", tk.END).strip()

        if not comment:
            messagebox.showwarning("Empty", "Comment cannot be empty")
            return

        res = api.add_comment(
            self.ticket_id,
            comment,
            is_internal=self.is_internal.get()
        )

        if res.status_code == 200:
            self.entry.delete("1.0", tk.END)
            self.is_internal.set(False)
            self.load_comments()
        else:
            messagebox.showerror("Error", res.text)
