"""
gui.py
------
The Tkinter graphical interface. Organizes everything into a tabbed
notebook (Phase 19):

    Grammar | FIRST & FOLLOW | Parsing Table | Parser | Parse Tree

and wires the grammar / FIRST / FOLLOW / table / parser modules together,
including step-by-step execution, stack & input-buffer visualization,
parsing-table cell highlighting, error handling, predefined test cases,
and CSV/TXT export.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from grammar import GRAMMAR, START_SYMBOL, END_MARKER, EPSILON, format_production, production_to_string
from first_follow import compute_first, compute_follow, sorted_set
from parsing_table import build_parsing_table
from parser import PredictiveParser, tokenize
from parse_tree import tree_to_text, compute_layout, draw_tree
from utils import export_rows_to_csv, export_rows_to_txt
import test_cases as tc

BG = "#f4f6f8"
ACCENT = "#2b6cb0"
GOOD = "#2f855a"
BAD = "#c53030"
HIGHLIGHT = "#fefcbf"


class ParserApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LL(1) Predictive Parser Demonstration")
        self.geometry("1180x760")
        self.configure(bg=BG)
        self.minsize(980, 640)

        # ---- compute grammar analysis once (fast, purely CPU-bound) ----
        self.first_sets = compute_first(GRAMMAR)
        self.follow_sets = compute_follow(GRAMMAR, self.first_sets, START_SYMBOL)
        self.table_result = build_parsing_table(GRAMMAR, self.first_sets, self.follow_sets)

        self.parser = None          # PredictiveParser instance, created on Parse/Step
        self.table_cell_widgets = {}  # (nt, term) -> Treeview item id, for highlighting

        self._build_style()
        self._build_layout()
        self._populate_grammar_tab()
        self._populate_first_follow_tab()
        self._populate_table_tab()
        self._populate_tree_tab()
        self._populate_parser_tab()

        self._set_status("Ready.")

    # ------------------------------------------------------------------ #
    # Style / skeleton
    # ------------------------------------------------------------------ #
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", rowheight=24, font=("Consolas", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    def _build_layout(self):
        title = tk.Label(self, text="LL(1) Predictive Parser \u2014 Interactive Demonstration",
                          font=("Segoe UI", 16, "bold"), bg=BG, fg="#1a202c")
        title.pack(fill="x", padx=10, pady=(10, 4))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=4)

        self.tab_grammar = ttk.Frame(self.notebook)
        self.tab_ff = ttk.Frame(self.notebook)
        self.tab_table = ttk.Frame(self.notebook)
        self.tab_parser = ttk.Frame(self.notebook)
        self.tab_tree = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_grammar, text="Grammar")
        self.notebook.add(self.tab_ff, text="FIRST & FOLLOW")
        self.notebook.add(self.tab_table, text="Parsing Table")
        self.notebook.add(self.tab_parser, text="Parser")
        self.notebook.add(self.tab_tree, text="Parse Tree")

        self.status_var = tk.StringVar(value="")
        status = tk.Label(self, textvariable=self.status_var, anchor="w", bg="#2d3748",
                           fg="white", font=("Segoe UI", 9), padx=8, pady=4)
        status.pack(fill="x", side="bottom")

    def _set_status(self, text):
        self.status_var.set(text)

    # ------------------------------------------------------------------ #
    # Phase 3 & 4 & 5 - Grammar / FIRST / FOLLOW tabs
    # ------------------------------------------------------------------ #
    def _populate_grammar_tab(self):
        frame = self.tab_grammar
        left = tk.Frame(frame, bg="white", bd=1, relief="solid")
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        right = tk.Frame(frame, bg="white", bd=1, relief="solid")
        right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        tk.Label(left, text="Productions", font=("Segoe UI", 12, "bold"),
                 bg="white", fg=ACCENT).pack(anchor="w", padx=10, pady=(10, 4))
        prod_text = tk.Text(left, height=16, font=("Consolas", 11), bd=0, bg="white")
        prod_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for nt, productions in GRAMMAR.items():
            alts = " | ".join(production_to_string(p) for p in productions)
            prod_text.insert("end", f"{nt:<4} \u2192 {alts}\n")
        prod_text.configure(state="disabled")

        info = tk.Frame(right, bg="white")
        info.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(info, text="Start Symbol", font=("Segoe UI", 11, "bold"), bg="white", fg=ACCENT).pack(anchor="w")
        tk.Label(info, text=START_SYMBOL, font=("Consolas", 12), bg="white").pack(anchor="w", pady=(0, 12))

        tk.Label(info, text="Non-terminals", font=("Segoe UI", 11, "bold"), bg="white", fg=ACCENT).pack(anchor="w")
        tk.Label(info, text="   ".join(GRAMMAR.keys()), font=("Consolas", 12), bg="white",
                 wraplength=380, justify="left").pack(anchor="w", pady=(0, 12))

        tk.Label(info, text="Terminals", font=("Segoe UI", 11, "bold"), bg="white", fg=ACCENT).pack(anchor="w")
        tk.Label(info, text="   ".join(self.table_result.terminals), font=("Consolas", 12),
                 bg="white").pack(anchor="w", pady=(0, 12))

        # LL(1) verification summary (Phase 20 optional item)
        tk.Label(info, text="LL(1) Verification", font=("Segoe UI", 11, "bold"),
                 bg="white", fg=ACCENT).pack(anchor="w")
        if self.table_result.is_ll1():
            msg = "This grammar is LL(1): every table cell has a single production."
            color = GOOD
        else:
            lines = [f"NOTE: This grammar is NOT strictly LL(1) - {len(self.table_result.conflicts)} "
                     f"cell(s) have more than one applicable production:", ""]
            for c in self.table_result.conflicts:
                nt, t = c["cell"]
                lines.append(f"M[{nt}, {t}]:")
                lines.append(f"    {c['candidates'][0]}")
                lines.append(f"    {c['candidates'][1]}")
                lines.append(f"    -> resolved to: {c['resolved_to']}")
                lines.append("")
            msg = "\n".join(lines)
            color = BAD
        tk.Label(info, text=msg, font=("Consolas", 9), bg="white", fg=color,
                 justify="left", wraplength=440, anchor="w").pack(anchor="w", pady=(0, 8), fill="x")

    def _populate_first_follow_tab(self):
        frame = self.tab_ff
        container = tk.Frame(frame, bg=BG)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        left = self._make_scrollable_labelframe(container, "FIRST Sets", side="left")
        right = self._make_scrollable_labelframe(container, "FOLLOW Sets", side="right")

        for nt in GRAMMAR:
            tk.Label(left, text=f"FIRST({nt}) = {{ {', '.join(sorted_set(self.first_sets[nt]))} }}",
                     font=("Consolas", 11), bg="white", anchor="w", justify="left").pack(
                fill="x", padx=10, pady=4, anchor="w")
        for nt in GRAMMAR:
            tk.Label(right, text=f"FOLLOW({nt}) = {{ {', '.join(sorted_set(self.follow_sets[nt]))} }}",
                     font=("Consolas", 11), bg="white", anchor="w", justify="left").pack(
                fill="x", padx=10, pady=4, anchor="w")

    def _make_scrollable_labelframe(self, parent, title, side):
        outer = tk.LabelFrame(parent, text=title, font=("Segoe UI", 11, "bold"), bg="white", fg=ACCENT)
        outer.pack(side=side, fill="both", expand=True, padx=8)
        return outer

    # ------------------------------------------------------------------ #
    # Phase 6 & 13 - Parsing table tab (Treeview) with highlighting
    # ------------------------------------------------------------------ #
    def _populate_table_tab(self):
        frame = self.tab_table
        top = tk.Frame(frame, bg=BG)
        top.pack(fill="both", expand=True, padx=10, pady=10)

        terms = self.table_result.terminals
        columns = ["NT"] + terms
        tv = ttk.Treeview(top, columns=columns, show="headings", height=10)
        tv.heading("NT", text="")
        tv.column("NT", width=60, anchor="center")
        for t in terms:
            tv.heading(t, text=t)
            tv.column(t, width=170, anchor="w")

        for nt in GRAMMAR:
            row_vals = [nt]
            for t in terms:
                entry = self.table_result.get(nt, t)
                if entry is None:
                    cell = ""
                else:
                    cell = format_production(nt, entry)
                    if self.table_result.raw_cells.get((nt, t)) and len(self.table_result.raw_cells[(nt, t)]) > 1:
                        cell += "  \u26a0"   # conflict marker
                row_vals.append(cell)
            item_id = tv.insert("", "end", values=row_vals)
            for t in terms:
                self.table_cell_widgets[(nt, t)] = item_id

        tv.pack(fill="both", expand=True, side="top")
        self.table_tree = tv
        self.table_columns = columns

        tv.tag_configure("highlight", background=HIGHLIGHT)

        legend = tk.Label(frame, text="\u26a0 = LL(1) conflict cell (grammar allows more than one production here; "
                                       "see the Grammar tab for details on how it was resolved).",
                           font=("Segoe UI", 9, "italic"), bg=BG, fg=BAD)
        legend.pack(anchor="w", padx=10, pady=(0, 6))

        export_bar = tk.Frame(frame, bg=BG)
        export_bar.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(export_bar, text="Export Table (CSV)",
                   command=self._export_table_csv).pack(side="left", padx=4)
        ttk.Button(export_bar, text="Export FIRST/FOLLOW (TXT)",
                   command=self._export_first_follow_txt).pack(side="left", padx=4)

    def _highlight_table_cell(self, nt, term):
        # Clear previous highlight
        for iid in self.table_tree.get_children():
            self.table_tree.item(iid, tags=())
        item_id = self.table_cell_widgets.get((nt, term))
        if item_id:
            self.table_tree.item(item_id, tags=("highlight",))
            self.table_tree.see(item_id)

    def _clear_table_highlight(self):
        for iid in self.table_tree.get_children():
            self.table_tree.item(iid, tags=())

    # ------------------------------------------------------------------ #
    # Phase 9-16 - Parser tab
    # ------------------------------------------------------------------ #
    def _populate_parser_tab(self):
        frame = self.tab_parser

        # ---- top controls: input entry, test-case dropdown, buttons ----
        controls = tk.Frame(frame, bg=BG)
        controls.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(controls, text="Input string:", bg=BG, font=("Segoe UI", 10, "bold")).pack(side="left")
        self.input_var = tk.StringVar()
        entry = tk.Entry(controls, textvariable=self.input_var, font=("Consolas", 12), width=24)
        entry.pack(side="left", padx=6)
        entry.bind("<Return>", lambda e: self._on_parse())

        tk.Label(controls, text="Test cases:", bg=BG, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(16, 4))
        self.test_case_var = tk.StringVar()
        all_labels = [f"\u2713 {s}" for s in tc.ACCEPTED_CASES] + [f"\u2717 {s}" for s in tc.REJECTED_CASES]
        combo = ttk.Combobox(controls, textvariable=self.test_case_var, values=all_labels,
                              state="readonly", width=16)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self._on_test_case_selected)

        btns = tk.Frame(frame, bg=BG)
        btns.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Button(btns, text="Parse (Automatic)", command=self._on_parse).pack(side="left", padx=4)
        ttk.Button(btns, text="Step", command=self._on_step).pack(side="left", padx=4)
        ttk.Button(btns, text="Reset", command=self._on_reset).pack(side="left", padx=4)
        ttk.Button(btns, text="Export Trace (CSV)", command=self._export_trace_csv).pack(side="right", padx=4)
        ttk.Button(btns, text="Export Trace (TXT)", command=self._export_trace_txt).pack(side="right", padx=4)

        # ---- middle: stack view + input buffer view ----
        mid = tk.Frame(frame, bg=BG)
        mid.pack(fill="x", padx=10, pady=(0, 8))

        stack_frame = tk.LabelFrame(mid, text="Stack (top \u2192 bottom)", bg="white",
                                     font=("Segoe UI", 10, "bold"), fg=ACCENT)
        stack_frame.pack(side="left", fill="y", padx=(0, 10))
        self.stack_listbox = tk.Listbox(stack_frame, font=("Consolas", 12), width=14, height=8,
                                         bg="white", bd=0)
        self.stack_listbox.pack(padx=8, pady=8)

        io_frame = tk.LabelFrame(mid, text="Input Buffer (^ = current reading position)", bg="white",
                                  font=("Segoe UI", 10, "bold"), fg=ACCENT)
        io_frame.pack(side="left", fill="both", expand=True)
        self.input_display = tk.Label(io_frame, text="", font=("Consolas", 14), bg="white",
                                       anchor="w", justify="left")
        self.input_display.pack(fill="x", padx=10, pady=(10, 0))
        self.pointer_display = tk.Label(io_frame, text="", font=("Consolas", 14), bg="white",
                                         fg=ACCENT, anchor="w", justify="left")
        self.pointer_display.pack(fill="x", padx=10, pady=(0, 10))

        self.action_var = tk.StringVar(value="")
        tk.Label(io_frame, textvariable=self.action_var, font=("Segoe UI", 10, "italic"),
                 bg="white", fg="#2d3748", anchor="w").pack(fill="x", padx=10, pady=(0, 10))

        # ---- result banner ----
        self.result_var = tk.StringVar(value="")
        self.result_label = tk.Label(frame, textvariable=self.result_var, font=("Segoe UI", 14, "bold"),
                                      bg=BG)
        self.result_label.pack(fill="x", padx=10, pady=(0, 6))

        # ---- trace table ----
        trace_frame = tk.LabelFrame(frame, text="Parsing Trace", bg="white",
                                     font=("Segoe UI", 10, "bold"), fg=ACCENT)
        trace_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("Step", "Stack", "Input", "Action")
        self.trace_tree = ttk.Treeview(trace_frame, columns=cols, show="headings", height=10)
        widths = (50, 260, 200, 380)
        for c, w in zip(cols, widths):
            self.trace_tree.heading(c, text=c)
            self.trace_tree.column(c, width=w, anchor="w")
        vsb = ttk.Scrollbar(trace_frame, orient="vertical", command=self.trace_tree.yview)
        self.trace_tree.configure(yscrollcommand=vsb.set)
        self.trace_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        vsb.pack(side="right", fill="y", pady=8)

        self._reset_parser_state(clear_input=False)

    # ---- test case selection ----
    def _on_test_case_selected(self, event=None):
        label = self.test_case_var.get()
        s = label.split(" ", 1)[1] if " " in label else label
        self.input_var.set(s)
        self._on_reset()

    # ---- core actions ----
    def _new_parser(self):
        s = self.input_var.get()
        self.parser = PredictiveParser(self.table_result, GRAMMAR, START_SYMBOL)
        self.parser.reset(s)
        return self.parser

    def _reset_parser_state(self, clear_input=True):
        if clear_input:
            self.input_var.set("")
        self.parser = None
        self.stack_listbox.delete(0, "end")
        self.stack_listbox.insert("end", END_MARKER)
        s = self.input_var.get().strip()
        tokens = tokenize(s)
        line, caret = "".join(tokens), ""
        self.input_display.configure(text=line if line else "(empty)")
        self.pointer_display.configure(text="^" if line else "")
        self.action_var.set("")
        self.result_var.set("")
        self.result_label.configure(bg=BG, fg="black")
        for row in self.trace_tree.get_children():
            self.trace_tree.delete(row)
        self._clear_table_highlight()
        self._draw_tree_placeholder()
        self._set_status("Ready.")

    def _on_reset(self):
        self._reset_parser_state(clear_input=False)

    def _refresh_stack_and_input_view(self):
        self.stack_listbox.delete(0, "end")
        # show top of stack first for readability
        for sym in reversed(self.parser.symbol_stack):
            self.stack_listbox.insert("end", sym)

        tokens = self.parser.tokens
        pos = self.parser.pos
        line = "".join(tokens)
        caret = " " * pos + "^"
        self.input_display.configure(text=line)
        self.pointer_display.configure(text=caret)

    def _append_trace_step(self, step):
        self.trace_tree.insert("", "end", values=step.as_tuple())
        self.trace_tree.see(self.trace_tree.get_children()[-1])
        self.action_var.set(step.action)
        if step.table_cell:
            self._highlight_table_cell(*step.table_cell)
        else:
            self._clear_table_highlight()

    def _finalize_result(self):
        if self.parser.accepted:
            self.result_var.set("\u2705 ACCEPTED")
            self.result_label.configure(fg=GOOD)
            self._set_status("Parsing complete: string accepted by the grammar.")
        else:
            last = self.parser.steps[-1] if self.parser.steps else None
            err = last.error if last and last.error else "Rejected."
            self.result_var.set(f"\u274c REJECTED \u2014 {err}")
            self.result_label.configure(fg=BAD)
            self._set_status(f"Parsing complete: string rejected. {err}")
        self._render_parse_tree()

    def _on_parse(self):
        if not self.input_var.get().strip():
            messagebox.showinfo("Input required", "Please enter a string to parse, or pick a test case.")
            return
        self._reset_parser_state(clear_input=False)
        self._new_parser()
        for row in self.trace_tree.get_children():
            self.trace_tree.delete(row)
        # first (Initialize) step already recorded by reset(); show it
        self._append_trace_step(self.parser.steps[-1])
        self._refresh_stack_and_input_view()
        while not self.parser.finished:
            step = self.parser.step()
            self._append_trace_step(step)
        self._refresh_stack_and_input_view()
        self._finalize_result()

    def _on_step(self):
        if self.parser is None:
            if not self.input_var.get().strip():
                messagebox.showinfo("Input required", "Please enter a string to parse, or pick a test case.")
                return
            for row in self.trace_tree.get_children():
                self.trace_tree.delete(row)
            self._new_parser()
            self._append_trace_step(self.parser.steps[-1])
            self._refresh_stack_and_input_view()
            self._set_status("Step 1: stack initialized. Click Step again to continue.")
            return

        if self.parser.finished:
            self._set_status("Parsing already finished. Click Reset to start over.")
            return

        step = self.parser.step()
        self._append_trace_step(step)
        self._refresh_stack_and_input_view()
        if self.parser.finished:
            self._finalize_result()
        else:
            self._set_status(f"Step {step.step_no}: {step.action}")

    # ------------------------------------------------------------------ #
    # Phase 17 - Parse tree tab
    # ------------------------------------------------------------------ #
    def _populate_tree_tab(self):
        frame = self.tab_tree
        top = tk.Frame(frame, bg=BG)
        top.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top, text="Parse tree is built automatically after a successful parse "
                            "(see Parser tab).", bg=BG, font=("Segoe UI", 10, "italic")).pack(anchor="w")

        body = tk.Frame(frame, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.LabelFrame(body, text="Tree (graphical)", bg="white", font=("Segoe UI", 10, "bold"), fg=ACCENT)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.tree_canvas = tk.Canvas(left, bg="white", height=380)
        hbar = ttk.Scrollbar(left, orient="horizontal", command=self.tree_canvas.xview)
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.tree_canvas.yview)
        self.tree_canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.tree_canvas.pack(side="top", fill="both", expand=True, padx=8, pady=(8, 0))
        hbar.pack(side="bottom", fill="x")

        right = tk.LabelFrame(body, text="Tree (text)", bg="white", font=("Segoe UI", 10, "bold"), fg=ACCENT)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))
        self.tree_text = tk.Text(right, font=("Consolas", 11), bg="white", bd=0)
        self.tree_text.pack(fill="both", expand=True, padx=8, pady=8)

    def _draw_tree_placeholder(self):
        self.tree_canvas.delete("all")
        self.tree_canvas.create_text(20, 20, anchor="nw", text="(no tree yet \u2014 parse a string first)",
                                      font=("Segoe UI", 10, "italic"), fill="#718096")
        self.tree_text.configure(state="normal")
        self.tree_text.delete("1.0", "end")
        self.tree_text.configure(state="disabled")

    def _render_parse_tree(self):
        root = self.parser.tree_root
        positions, w, h = compute_layout(root)
        draw_tree(self.tree_canvas, root, positions)
        self.tree_canvas.configure(scrollregion=(0, 0, w + 20, h + 20))

        self.tree_text.configure(state="normal")
        self.tree_text.delete("1.0", "end")
        for line in tree_to_text(root):
            self.tree_text.insert("end", line + "\n")
        self.tree_text.configure(state="disabled")

    # ------------------------------------------------------------------ #
    # Phase 18 - Export
    # ------------------------------------------------------------------ #
    def _ask_save_path(self, default_name, filetypes):
        return filedialog.asksaveasfilename(defaultextension=filetypes[0][1],
                                             filetypes=filetypes, initialfile=default_name)

    def _export_table_csv(self):
        path = self._ask_save_path("parsing_table.csv", [("CSV file", "*.csv")])
        if not path:
            return
        header = ["NonTerminal"] + self.table_result.terminals
        rows = []
        for nt in GRAMMAR:
            row = [nt]
            for t in self.table_result.terminals:
                entry = self.table_result.get(nt, t)
                row.append(format_production(nt, entry) if entry is not None else "")
            rows.append(row)
        export_rows_to_csv(path, header, rows)
        self._set_status(f"Parsing table exported to {path}")

    def _export_first_follow_txt(self):
        path = self._ask_save_path("first_follow.txt", [("Text file", "*.txt")])
        if not path:
            return
        header = ["NonTerminal", "FIRST", "FOLLOW"]
        rows = [[nt, ", ".join(sorted_set(self.first_sets[nt])), ", ".join(sorted_set(self.follow_sets[nt]))]
                for nt in GRAMMAR]
        export_rows_to_txt(path, header, rows)
        self._set_status(f"FIRST/FOLLOW sets exported to {path}")

    def _export_trace_csv(self):
        if not self.parser or not self.parser.steps:
            messagebox.showinfo("Nothing to export", "Run a parse first.")
            return
        path = self._ask_save_path("parsing_trace.csv", [("CSV file", "*.csv")])
        if not path:
            return
        header = ["Step", "Stack", "Input", "Action"]
        rows = [s.as_tuple() for s in self.parser.steps]
        export_rows_to_csv(path, header, rows)
        self._set_status(f"Parsing trace exported to {path}")

    def _export_trace_txt(self):
        if not self.parser or not self.parser.steps:
            messagebox.showinfo("Nothing to export", "Run a parse first.")
            return
        path = self._ask_save_path("parsing_trace.txt", [("Text file", "*.txt")])
        if not path:
            return
        header = ["Step", "Stack", "Input", "Action"]
        rows = [s.as_tuple() for s in self.parser.steps]
        export_rows_to_txt(path, header, rows)
        self._set_status(f"Parsing trace exported to {path}")


def launch():
    app = ParserApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
