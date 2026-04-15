import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from services.analyzer import analyze

class App:

    def __init__(self, root):
        self.root = root
        self.root.title("Network Analyzer Pro")
        self.root.geometry("750x600")
        self.root.config(bg="#0f172a")

        # Title
        tk.Label(root, text="🌐 Network Analyzer Pro",
                 font=("Arial", 18, "bold"),
                 fg="white", bg="#0f172a").pack(pady=10)

        # Input
        self.entry = tk.Entry(root, font=("Arial", 14), width=40)
        self.entry.pack(pady=10)

        # Button
        tk.Button(root, text="Analyze",
                  bg="#22c55e", fg="white",
                  font=("Arial", 12),
                  command=self.start).pack(pady=10)

        # Progress bars
        self.bars = {}
        self.create_bars()

        # Output
        self.output = scrolledtext.ScrolledText(
            root, height=15, bg="#111827", fg="white")
        self.output.pack(pady=10)

    def create_bars(self):
        frame = tk.Frame(self.root, bg="#0f172a")
        frame.pack()

        for p in ["dns", "tcp", "http", "ssl", "udp", "ntp"]:
            tk.Label(frame, text=p.upper(),
                     fg="white", bg="#0f172a").pack()

            bar = ttk.Progressbar(frame, length=500)
            bar.pack(pady=2)

            self.bars[p] = bar

    def callback(self, key, value):
        self.output.insert(tk.END, f"{key.upper()}: {value}\n")
        self.bars[key]["value"] = 100
        self.root.update_idletasks()

    def start(self):
        domain = self.entry.get()
        self.output.delete("1.0", tk.END)

        for b in self.bars.values():
            b["value"] = 0

        threading.Thread(
            target=lambda: analyze(domain, self.callback),
            daemon=True
        ).start()