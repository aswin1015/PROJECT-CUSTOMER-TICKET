import tkinter as tk
from tkinter import messagebox
import api_client as api
from admin_ui import AdminPage
from customer_ui import CustomerPage
from helper_ui import HelperPage
from theme import *

class LoginPage:
    def __init__(self, root):
        self.root = root

        self.frame = tk.Frame(root, bg=BG_MAIN)
        self.frame.pack(fill="both", expand=True)

        tk.Label(
            self.frame,
            text="Login",
            font=FONT_TITLE,
            bg=BG_MAIN,
            fg=PRIMARY
        ).pack(pady=20)

        tk.Label(self.frame, text="Email", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack()
        self.email = tk.Entry(
            self.frame,
            width=35,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN
        )
        self.email.pack(pady=5)

        tk.Label(self.frame, text="Password", bg=BG_MAIN, fg=TEXT_SUB, font=FONT_SUB).pack()
        self.password = tk.Entry(
            self.frame,
            show="*",
            width=35,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN
        )
        self.password.pack(pady=5)

        dark_button(self.frame, "Login", self.login).pack(pady=15)
        dark_button(self.frame, "Register", self.open_register).pack()

    def login(self):
        res = api.login(self.email.get(), self.password.get())

        if res.status_code != 200:
            messagebox.showerror("Error", "Invalid credentials")
            return

        me = api.get_me().json()
        role = me["role"]

        self.frame.destroy()

        if role == "admin":
            AdminPage(self.root)
        elif role == "helper":
            HelperPage(self.root)
        else:
            CustomerPage(self.root)

    def open_register(self):
        RegisterPage(self.root)


# ---------------- REGISTER ----------------
class RegisterPage:
    def __init__(self, root):
        self.top = tk.Toplevel(root)
        self.top.title("Register")
        self.top.geometry("400x350")
        self.top.configure(bg=BG_MAIN)

        tk.Label(
            self.top,
            text="Register",
            font=FONT_TITLE,
            bg=BG_MAIN,
            fg=PRIMARY
        ).pack(pady=15)

        self.email = self._entry("Email")
        self.name = self._entry("Name")
        self.password = self._entry("Password", show="*")

        tk.Label(
            self.top,
            text="Role",
            bg=BG_MAIN,
            fg=TEXT_SUB,
            font=FONT_SUB
        ).pack(pady=5)

        self.role = tk.StringVar(value="customer")
        role_menu = tk.OptionMenu(self.top, self.role, "customer", "helper", "admin")
        role_menu.config(bg=BG_CARD, fg=TEXT_MAIN)
        role_menu.pack()

        dark_button(self.top, "Register", self.submit).pack(pady=20)

    def _entry(self, label, show=None):
        tk.Label(
            self.top,
            text=label,
            bg=BG_MAIN,
            fg=TEXT_SUB,
            font=FONT_SUB
        ).pack(pady=3)

        e = tk.Entry(
            self.top,
            width=35,
            show=show,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN
        )
        e.pack()
        return e

    def submit(self):
        res = api.register(
            self.email.get(),
            self.name.get(),
            self.password.get(),
            self.role.get()
        )

        if res.status_code == 200:
            messagebox.showinfo("Success", "User registered")
            self.top.destroy()
        else:
            messagebox.showerror("Error", res.text)
