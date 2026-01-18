# theme.py
import tkinter as tk
from tkinter import ttk

# -------- COLORS --------
BG_MAIN   = "#0b0f1a"   # near-black background
BG_CARD   = "#111827"   # card background
PRIMARY   = "#3b82f6"   # blue
ACCENT    = "#60a5fa"   # hover blue
TEXT_MAIN = "#e5e7eb"   # main text
TEXT_SUB  = "#93c5fd"   # sub text
SUCCESS   = "#22c55e"
DANGER    = "#ef4444"

# -------- FONTS --------
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_SUB   = ("Segoe UI", 12)
FONT_BTN   = ("Segoe UI", 11, "bold")
FONT_TEXT  = ("Segoe UI", 10)

# -------- BUTTON --------
def dark_button(parent, text, command, color=PRIMARY):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg="white",
        font=FONT_BTN,
        activebackground=ACCENT,
        activeforeground="white",
        relief="flat",
        padx=18,
        pady=8,
        cursor="hand2",
        borderwidth=0
    )

    # Hover effect
    btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT))
    btn.bind("<Leave>", lambda e: btn.config(bg=color))
    return btn


# -------- TABLE STYLE --------
def apply_dark_treeview():
    style = ttk.Style()
    style.theme_use("default")

    style.configure(
        "Treeview",
        background=BG_CARD,
        foreground=TEXT_MAIN,
        fieldbackground=BG_CARD,
        rowheight=28,
        font=FONT_TEXT
    )

    style.configure(
        "Treeview.Heading",
        background=PRIMARY,
        foreground="white",
        font=("Segoe UI", 11, "bold")
    )

    style.map(
        "Treeview",
        background=[("selected", PRIMARY)],
        foreground=[("selected", "white")]
    )
