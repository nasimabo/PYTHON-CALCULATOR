import tkinter as tk
from tkinter import ttk, messagebox
import math
import ast
import operator as op

# ---------- Safe Evaluator (AST-based) ----------
class SafeEvaluator:
    def __init__(self, is_degrees_callable):
        self.is_degrees = is_degrees_callable
        # Allowed operators
        self.ops = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Mod: op.mod,
            ast.Pow: op.pow,
            ast.FloorDiv: op.floordiv,
            ast.USub: op.neg,
            ast.UAdd: op.pos,
        }

    def _build_env(self):
        is_deg = self.is_degrees()
        # Wrap trig to honor degree/radian setting
        def _sin(x, is_deg=is_deg): return math.sin(math.radians(x)) if is_deg else math.sin(x)
        def _cos(x, is_deg=is_deg): return math.cos(math.radians(x)) if is_deg else math.cos(x)
        def _tan(x, is_deg=is_deg): return math.tan(math.radians(x)) if is_deg else math.tan(x)

        env = {
            "sin": _sin,
            "cos": _cos,
            "tan": _tan,
            "log": math.log10,
            "ln": math.log,
            "sqrt": math.sqrt,
            "abs": abs,
            "round": round,
            "pi": math.pi,
            "e": math.e,
        }
        return env

    def eval(self, expression: str):
        try:
            node = ast.parse(expression, mode='eval')
            return self._eval(node.body, self._build_env())
        except ZeroDivisionError:
            raise
        except Exception as e:
            raise ValueError("Invalid expression") from e

    def _eval(self, node, env):
        if isinstance(node, ast.Num):  # Py<3.8
            return node.n
        if isinstance(node, ast.Constant):  # Py3.8+
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Constants other than numbers not allowed")

        if isinstance(node, ast.BinOp):
            if type(node.op) not in self.ops:
                raise ValueError("Operator not allowed")
            return self.ops[type(node.op)](self._eval(node.left, env), self._eval(node.right, env))

        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in self.ops:
                raise ValueError("Unary operator not allowed")
            return self.ops[type(node.op)](self._eval(node.operand, env))

        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise ValueError(f"Unknown name: {node.id}")

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in env:
                raise ValueError("Function not allowed")
            fn = env[node.func.id]
            args = [self._eval(a, env) for a in node.args]
            if len(args) == 0:
                raise ValueError("Function needs arguments")
            return fn(*args)

        if isinstance(node, ast.Expr):
            return self._eval(node.value, env)

        raise ValueError("Unsupported syntax")

# ---------- UI ----------
class CalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Unique GUI Calculator • Tkinter")
        self.root.minsize(520, 520)

        # State
        self.is_dark = False
        self.degree_mode = True
        self.memory_value = 0.0
        self.history = []
        self.history_index = None  # for up/down navigation

        # Safe evaluator
        self.evaluator = SafeEvaluator(lambda: self.degree_mode)

        # Styles & layout
        self._build_styles()
        self._build_layout()
        self._bind_keys()
        self._apply_theme()

    # ---------- Styles ----------
    def _build_styles(self):
        self.colors = {
            "light": {
                "bg": "#f7f7fb",
                "panel": "#ffffff",
                "text": "#111827",
                "muted": "#6b7280",
                "primary": "#2563eb",
                "accent": "#10b981",
                "warn": "#ef4444",
                "button": "#e5e7eb",
                "button_txt": "#111827",
            },
            "dark": {
                "bg": "#0f172a",
                "panel": "#111827",
                "text": "#e5e7eb",
                "muted": "#94a3b8",
                "primary": "#60a5fa",
                "accent": "#34d399",
                "warn": "#f87171",
                "button": "#1f2937",
                "button_txt": "#e5e7eb",
            },
        }

    # ---------- Layout ----------
    def _build_layout(self):
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=2)

        # Top bar
        top = tk.Frame(self.root, bd=0, highlightthickness=0)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        top.grid_columnconfigure(0, weight=1)

        self.theme_btn = tk.Button(top, text="☀️ Light", command=self.toggle_theme, bd=0, relief="flat")
        self.mode_btn = tk.Button(top, text="DEG", command=self.toggle_degree_mode, bd=0, relief="flat")
        self.clear_hist_btn = tk.Button(top, text="🧹 Clear History", command=self.clear_history, bd=0, relief="flat")

        self.theme_btn.grid(row=0, column=1, padx=6)
        self.mode_btn.grid(row=0, column=2, padx=6)
        self.clear_hist_btn.grid(row=0, column=3, padx=6)

        # Display
        display_frame = tk.Frame(self.root, bd=0, highlightthickness=0)
        display_frame.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(6, 12))
        display_frame.grid_rowconfigure(1, weight=1)
        display_frame.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(display_frame, font=("Consolas", 22), borderwidth=0, relief="flat", justify="right")
        self.entry.grid(row=0, column=0, sticky="ew", ipady=12, padx=6, pady=(6, 10))

        self.result_var = tk.StringVar(value="")
        self.result_label = tk.Label(display_frame, textvariable=self.result_var, anchor="e",
                                     font=("Inter", 12))
        self.result_label.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 10))

        # Keypad
        keypad = tk.Frame(display_frame)
        keypad.grid(row=2, column=0, sticky="nsew")
        for r in range(6):
            keypad.grid_rowconfigure(r, weight=1)
        for c in range(5):
            keypad.grid_columnconfigure(c, weight=1)

        def add_btn(txt, r, c, cmd=None, kind="btn", colspan=1):
            btn = tk.Button(keypad, text=txt, command=cmd or (lambda t=txt: self.on_button(t)),
                            bd=0, relief="flat", font=("Inter", 14), padx=8, pady=12)
            btn.grid(row=r, column=c, sticky="nsew", padx=6, pady=6, columnspan=colspan)
            setattr(btn, "_kind", kind)
            return btn

        # Row 0 (functions)
        add_btn("sin(", 0, 0, lambda: self.insert_text("sin("), "func")
        add_btn("cos(", 0, 1, lambda: self.insert_text("cos("), "func")
        add_btn("tan(", 0, 2, lambda: self.insert_text("tan("), "func")
        add_btn("log(", 0, 3, lambda: self.insert_text("log("), "func")
        add_btn("ln(", 0, 4, lambda: self.insert_text("ln("), "func")

        # Row 1 (memory + constants)
        add_btn("MC", 1, 0, self.mem_clear, "mem")
        add_btn("MR", 1, 1, self.mem_recall, "mem")
        add_btn("M+", 1, 2, self.mem_add, "mem")
        add_btn("M-", 1, 3, self.mem_sub, "mem")
        add_btn("√", 1, 4, lambda: self.insert_text("sqrt("), "func")

        # Row 2
        add_btn("(", 2, 0)
        add_btn(")", 2, 1)
        add_btn("π", 2, 2, lambda: self.insert_text("pi"))
        add_btn("e", 2, 3, lambda: self.insert_text("e"))
        add_btn("C", 2, 4, self.clear, "warn")

        # Row 3
        add_btn("7", 3, 0); add_btn("8", 3, 1); add_btn("9", 3, 2)
        add_btn("÷", 3, 3, lambda: self.on_button("/"))
        add_btn("⌫", 3, 4, self.backspace, "warn")

        # Row 4
        add_btn("4", 4, 0); add_btn("5", 4, 1); add_btn("6", 4, 2)
        add_btn("×", 4, 3, lambda: self.on_button("*"))
        add_btn("%", 4, 4, lambda: self.on_button("%"))

        # Row 5
        add_btn("1", 5, 0); add_btn("2", 5, 1); add_btn("3", 5, 2)
        add_btn("–", 5, 3, lambda: self.on_button("-"))
        add_btn("^", 5, 4, lambda: self.on_button("**"))

        # Row 6
        add_btn("0", 6, 0, colspan=2)
        add_btn(".", 6, 2)
        add_btn("+", 6, 3, lambda: self.on_button("+"))
        add_btn("=", 6, 4, self.equals, "primary")

        # History panel
        right = tk.Frame(self.root)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(6, 12))
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        hist_title = tk.Label(right, text="History", font=("Inter", 12, "bold"), anchor="w")
        hist_title.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.hist_list = tk.Listbox(right, activestyle="none")
        self.hist_list.grid(row=1, column=0, sticky="nsew")
        self.hist_list.bind("<<ListboxSelect>>", self.on_history_select)

        hist_help = tk.Label(
            right,
            text="Tip: Enter = evaluate • ↑/↓ = navigate • Click to reuse",
            anchor="w", font=("Inter", 9)
        )
        hist_help.grid(row=2, column=0, sticky="ew", pady=(6, 0))

    # ---------- Theming ----------
    def _apply_theme(self):
        theme = self.colors["dark" if self.is_dark else "light"]
        bg = theme["bg"]
        panel = theme["panel"]
        text = theme["text"]
        muted = theme["muted"]
        primary = theme["primary"]
        accent = theme["accent"]
        warn = theme["warn"]
        btn_bg = theme["button"]
        btn_txt = theme["button_txt"]

        self.root.configure(bg=bg)
        for w in self.root.winfo_children():
            if isinstance(w, tk.Frame):
                w.configure(bg=bg)

        # Panels
        for frame in self.root.grid_slaves(row=1):
            try: frame.configure(bg=bg)
            except: pass

        # Top bar buttons
        for b in (self.theme_btn, self.mode_btn, self.clear_hist_btn):
            b.configure(bg=panel, fg=text, activebackground=btn_bg, activeforeground=text)

        # Display frame widgets
        self.entry.configure(bg=panel, fg=text, insertbackground=primary)
        self.result_label.configure(bg=self.root["bg"], fg=muted)

        # Keypad coloring
        display_frame = self.root.grid_slaves(row=1, column=0)[0]
        keypad = display_frame.grid_slaves(row=2, column=0)[0]
        for btn in keypad.winfo_children():
            kind = getattr(btn, "_kind", "btn")
            if kind == "primary":
                btn.configure(bg=primary, fg="#ffffff", activebackground=primary, activeforeground="#ffffff")
            elif kind == "warn":
                btn.configure(bg=warn, fg="#ffffff", activebackground=warn, activeforeground="#ffffff")
            elif kind == "func":
                btn.configure(bg=accent, fg="#0b1720", activebackground=accent, activeforeground="#0b1720")
            elif kind == "mem":
                btn.configure(bg=btn_bg, fg=btn_txt, activebackground=btn_bg, activeforeground=btn_txt)
            else:
                btn.configure(bg=btn_bg, fg=btn_txt, activebackground=btn_bg, activeforeground=btn_txt)

        # History panel
        right = self.root.grid_slaves(row=1, column=1)[0]
        for w in right.winfo_children():
            if isinstance(w, (tk.Label,)):
                w.configure(bg=bg, fg=text if "bold" in str(w.cget("font")) else text)
        self.hist_list.configure(bg=panel, fg=text, selectbackground=primary, selectforeground="#ffffff",
                                 highlightthickness=0, borderwidth=0)

        # Buttons text for theme/mode
        self.theme_btn.configure(text=("🌙 Dark" if not self.is_dark else "☀️ Light"))
        self.mode_btn.configure(text=("DEG" if self.degree_mode else "RAD"))

    # ---------- Events ----------
    def _bind_keys(self):
        self.root.bind("<Return>", lambda e: self.equals())
        self.root.bind("<KP_Enter>", lambda e: self.equals())
        self.root.bind("<Escape>", lambda e: self.clear())
        self.root.bind("<BackSpace>", lambda e: self.backspace())
        self.root.bind("<Up>", self.history_prev)
        self.root.bind("<Down>", self.history_next)

        # Allow number/operator input
        allowed = "0123456789+-*/().% ^"
        def on_key(e):
            if e.char and e.char in allowed:
                self.insert_text(e.char)
                return "break"  # keep focus
        self.root.bind("<Key>", on_key)

    # ---------- Helpers ----------
    def insert_text(self, txt):
        self.entry.insert(tk.END, txt)
        self.result_var.set("")

    def on_button(self, txt):
        self.insert_text(txt)

    def clear(self):
        self.entry.delete(0, tk.END)
        self.result_var.set("")
        self.history_index = None

    def backspace(self):
        s = self.entry.get()
        if s:
            self.entry.delete(len(s)-1, tk.END)

    def format_number(self, x):
        try:
            if isinstance(x, int) or (isinstance(x, float) and x.is_integer()):
                return str(int(x))
            # Up to 12 significant digits
            return f"{x:.12g}"
        except Exception:
            return str(x)

    def equals(self):
        expr = self.entry.get().strip()
        if not expr:
            return
        try:
            result = self.evaluator.eval(expr)
            self.result_var.set(self.format_number(result))
            # Push to history
            self._add_history(f"{expr} = {self.format_number(result)}")
            # Prepare next: replace entry with result
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.format_number(result))
            self.history_index = None
        except ZeroDivisionError:
            messagebox.showerror("Math error", "Division by zero")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _add_history(self, item):
        self.history.append(item)
        self.hist_list.insert(tk.END, item)
        self.hist_list.see(tk.END)

    def on_history_select(self, _event):
        sel = self.hist_list.curselection()
        if not sel:
            return
        item = self.hist_list.get(sel[0])
        expr = item.split("=")[0].strip()
        self.entry.delete(0, tk.END)
        self.entry.insert(0, expr)
        self.result_var.set("")

    def clear_history(self):
        self.history.clear()
        self.hist_list.delete(0, tk.END)
        self.history_index = None

    def history_prev(self, _e=None):
        if not self.history:
            return
        if self.history_index is None:
            self.history_index = len(self.history) - 1
        else:
            self.history_index = max(0, self.history_index - 1)
        self._load_history_index()

    def history_next(self, _e=None):
        if not self.history:
            return
        if self.history_index is None:
            return
        self.history_index = min(len(self.history) - 1, self.history_index + 1)
        self._load_history_index()

    def _load_history_index(self):
        if self.history_index is None: return
        item = self.history[self.history_index]
        expr = item.split("=")[0].strip()
        self.entry.delete(0, tk.END)
        self.entry.insert(0, expr)
        self.result_var.set("")

    # Memory functions use current display/result
    def _current_value(self):
        s = self.entry.get().strip()
        if not s:
            # try result
            try:
                return float(self.result_var.get())
            except Exception:
                return 0.0
        try:
            v = self.evaluator.eval(s)
            return float(v)
        except Exception:
            return 0.0

    def mem_clear(self):
        self.memory_value = 0.0
        self.result_var.set("Memory cleared")

    def mem_recall(self):
        self.insert_text(self.format_number(self.memory_value))

    def mem_add(self):
        self.memory_value += self._current_value()
        self.result_var.set(f"Memory: {self.format_number(self.memory_value)}")

    def mem_sub(self):
        self.memory_value -= self._current_value()
        self.result_var.set(f"Memory: {self.format_number(self.memory_value)}")

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self._apply_theme()

    def toggle_degree_mode(self):
        self.degree_mode = not self.degree_mode
        self._apply_theme()

def main():
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
