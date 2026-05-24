"""RCBash Manager GUI launcher.

Wrappar resultcalculation.py som subprocess. Ersätter batch-filerna
med ett fönster där knappar startar varje kommando och output visas
direkt i ett textfält. Ett inmatningsfält skickar svar till input()-prompter.

Inga ändringar i de underliggande Python-filerna krävs.
"""
import codecs
import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

SCRIPT_DIR = Path(__file__).resolve().parent
RESULTCALC = SCRIPT_DIR.parent / "racelogic" / "resultcalculation.py"

COMMAND_GROUPS = [
    ("Tävlingsdag", [
        ("Starta ny deltävling",          ["-s"],       "Starta en HELT NY deltävling? Eventuell pågående tävling för idag skrivs över."),
    ]),
    ("Omgång", [
        ("Starta nästa omgång",           ["-n"],       None),
    ]),
    ("Heat", [
        ("Visa nästa heat",               ["-g"],       None),
        ("Registrera resultat manuellt",  ["-r", "-m"], None),
        ("Visa nuvarande omgång",         ["-l"],       None),
    ]),
    ("Resultat & poäng", [
        ("Visa senaste resultat",         ["-d"],       None),
        ("Visa poängställning",           ["-o"],       None),
        ("Poängställning (med detaljer)", ["-o", "-v"], None),
    ]),
]


class LauncherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("RCBash Manager")
        screen_h = root.winfo_screenheight()
        initial_h = min(680, max(360, screen_h - 80))
        root.geometry(f"960x{initial_h}")
        root.minsize(720, 320)

        self.proc: subprocess.Popen | None = None
        self.out_queue: queue.Queue = queue.Queue()

        self._build_ui()
        self._set_running(False)
        self._poll_output()

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        groups_frame = ttk.Frame(self.root, padding=(8, 8, 8, 4))
        groups_frame.pack(fill="x")

        self.buttons: list[ttk.Button] = []
        cols = 2
        for group_name, commands in COMMAND_GROUPS:
            group = ttk.LabelFrame(groups_frame, text=group_name, padding=6)
            group.pack(fill="x", pady=(0, 6))
            for i, (label, args, confirm) in enumerate(commands):
                r, c = divmod(i, cols)
                btn = ttk.Button(
                    group, text=label, width=30,
                    command=lambda a=args, cf=confirm, lb=label: self._launch(a, cf, lb),
                )
                btn.grid(row=r, column=c, padx=4, pady=3, sticky="w")
                self.buttons.append(btn)

        status_frame = ttk.Frame(self.root, padding=(8, 0))
        status_frame.pack(fill="x")
        self.status_var = tk.StringVar(value="Klar")
        ttk.Label(status_frame, text="Status:").pack(side="left")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="#1a7f37")
        self.status_label.pack(side="left", padx=(4, 0))
        self.abort_btn = ttk.Button(status_frame, text="Avbryt körning", command=self._abort)
        self.abort_btn.pack(side="right")
        self.clear_btn = ttk.Button(status_frame, text="Rensa logg", command=self._clear)
        self.clear_btn.pack(side="right", padx=(0, 4))

        input_frame = ttk.Frame(self.root, padding=(8, 4, 8, 8))
        input_frame.pack(side="bottom", fill="x")
        ttk.Label(input_frame, text="Inmatning:").pack(side="left")
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_var, font=("Consolas", 11))
        self.input_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.input_entry.bind("<Return>", self._send_input)
        self.send_btn = ttk.Button(input_frame, text="Skicka", command=self._send_input)
        self.send_btn.pack(side="right")

        self.text = scrolledtext.ScrolledText(
            self.root, wrap="word",
            font=("Consolas", 11),
            background="#1e1e1e", foreground="#e6e6e6",
            insertbackground="#e6e6e6",
        )
        self.text.pack(fill="both", expand=True, padx=8, pady=4)
        self.text.tag_configure("system", foreground="#7fbf7f")
        self.text.tag_configure("error", foreground="#ff6060")
        self.text.tag_configure("input", foreground="#ffd060")
        self.text.configure(state="disabled")

    def _append(self, text: str, tag: str | None = None):
        self.text.configure(state="normal")
        if tag:
            self.text.insert("end", text, tag)
        else:
            self.text.insert("end", text)
        self.text.see("end")
        self.text.configure(state="disabled")

    def _clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def _set_running(self, running: bool):
        for btn in self.buttons:
            btn.configure(state="disabled" if running else "normal")
        self.abort_btn.configure(state="normal" if running else "disabled")
        self.send_btn.configure(state="normal" if running else "disabled")
        self.input_entry.configure(state="normal" if running else "disabled")
        if running:
            self.status_var.set("Kör...")
            self.status_label.configure(foreground="#0969da")
            self.input_entry.focus_set()
        else:
            self.status_var.set("Klar")
            self.status_label.configure(foreground="#1a7f37")

    def _launch(self, args: list[str], confirm: str | None = None, label: str = ""):
        if self.proc and self.proc.poll() is None:
            messagebox.showwarning("Upptaget", "En körning pågår redan.")
            return
        if not RESULTCALC.exists():
            messagebox.showerror("Fel", f"Hittade inte:\n{RESULTCALC}")
            return
        if confirm and not messagebox.askyesno(label or "Bekräfta", confirm, default="no", icon="warning"):
            return

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        cmd = ["py", "-u", str(RESULTCALC)] + args
        self._append(f"\n> resultcalculation.py {' '.join(args)}\n", tag="system")

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                cwd=str(RESULTCALC.parent),
                env=env,
                creationflags=creationflags,
            )
        except FileNotFoundError:
            self._append("Kunde inte starta 'py'. Är Python installerat och på PATH?\n", tag="error")
            return
        except Exception as e:
            self._append(f"Fel vid start: {e}\n", tag="error")
            return

        threading.Thread(target=self._reader_thread, args=(self.proc,), daemon=True).start()
        self._set_running(True)

    def _reader_thread(self, proc: subprocess.Popen):
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            while True:
                chunk = proc.stdout.read(64)
                if not chunk:
                    leftover = decoder.decode(b"", final=True)
                    if leftover:
                        self.out_queue.put(("data", leftover))
                    break
                text = decoder.decode(chunk)
                if text:
                    self.out_queue.put(("data", text))
        except Exception as e:
            self.out_queue.put(("error", f"\n[Läsfel: {e}]\n"))
        finally:
            rc = proc.wait()
            self.out_queue.put(("done", rc))

    def _poll_output(self):
        try:
            while True:
                kind, payload = self.out_queue.get_nowait()
                if kind == "data":
                    self._append(payload)
                elif kind == "error":
                    self._append(payload, tag="error")
                elif kind == "done":
                    self._append(f"\n[Klar — exitkod {payload}]\n", tag="system")
                    self._set_running(False)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_output)

    def _send_input(self, event=None):
        if not self.proc or self.proc.poll() is not None:
            return
        text = self.input_var.get()
        self._append(text + "\n", tag="input")
        try:
            self.proc.stdin.write((text + "\n").encode("utf-8"))
            self.proc.stdin.flush()
        except Exception as e:
            self._append(f"\n[Inmatningsfel: {e}]\n", tag="error")
        self.input_var.set("")

    def _abort(self):
        if not self.proc or self.proc.poll() is not None:
            return
        if not messagebox.askyesno("Avbryt", "Avsluta pågående körning?"):
            return
        try:
            self.proc.terminate()
        except Exception:
            pass
        self.root.after(2000, self._force_kill_if_alive)

    def _force_kill_if_alive(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.kill()
            except Exception:
                pass

    def _on_close(self):
        if self.proc and self.proc.poll() is None:
            if not messagebox.askyesno("Avsluta", "En körning pågår. Avsluta ändå?"):
                return
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
