"""Small Tkinter desktop window: choose a file, review findings, create a safe copy."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import scan, scan_and_verify, SUPPORTED
from .models import Severity

_COLORS = {Severity.HIGH: "#c0392b", Severity.MEDIUM: "#d68910", Severity.LOW: "#2471a3"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BeforeShare")
        self.geometry("720x480")
        self.path = None
        self.findings = []
        self.vars = {}
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Button(top, text="Choose file...", command=self.choose).pack(side="left")
        self.label = ttk.Label(top, text="No file selected", padding=(10, 0))
        self.label.pack(side="left")
        self.box = ttk.Frame(self, padding=10)
        self.box.pack(fill="both", expand=True)
        self.btn = ttk.Button(self, text="Create safe copy", command=self.make_copy, state="disabled")
        self.btn.pack(pady=10)

    def choose(self):
        types = [("Supported files", " ".join("*" + e for e in SUPPORTED))]
        p = filedialog.askopenfilename(filetypes=types)
        if p:
            self.load(p)

    def load(self, p):
        for w in self.box.winfo_children():
            w.destroy()
        self.vars.clear()
        try:
            self.findings = scan(p)
        except Exception as e:
            messagebox.showerror("BeforeShare", str(e))
            return
        self.path = p
        self.label.config(text=p)
        if not self.findings:
            ttk.Label(self.box, text="No hidden data found by the available checks.").pack(anchor="w")
        for f in self.findings:
            row = ttk.Frame(self.box)
            row.pack(fill="x", anchor="w")
            if f.removable:
                v = tk.BooleanVar(value=True)
                self.vars[f.code] = v
                ttk.Checkbutton(row, variable=v).pack(side="left")
            else:
                ttk.Label(row, text="   ").pack(side="left")
            tk.Label(row, text=f"[{f.severity.label()}]", fg=_COLORS[f.severity]).pack(side="left")
            ttk.Label(row, text=" " + f.message + ("" if f.removable else "  (review manually)")).pack(side="left")
        self.btn.config(state="normal" if self.vars else "disabled")

    def make_copy(self):
        codes = [c for c, v in self.vars.items() if v.get()]
        try:
            out, remaining, ok = scan_and_verify(self.path, None, codes)
        except Exception as e:
            messagebox.showerror("BeforeShare", str(e))
            return
        msg = f"Safe copy: {out}\nOriginal not changed.\n"
        msg += "Verified: selected items are gone." if ok else "Verification failed for:\n" + "\n".join(map(str, remaining))
        messagebox.showinfo("BeforeShare", msg)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
