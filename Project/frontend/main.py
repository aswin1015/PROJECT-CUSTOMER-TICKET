import tkinter as tk
from auth_ui import LoginPage
from theme import *

root = tk.Tk()
root.configure(bg=BG_MAIN)
root.title("Customer Support Ticketing System")
root.geometry("900x600")

LoginPage(root)

root.mainloop()
