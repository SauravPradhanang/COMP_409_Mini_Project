# LL(1) Predictive Parser Demonstration

An interactive Tkinter application that visualizes every stage of
**non-recursive, table-driven LL(1) parsing**: grammar analysis, FIRST/FOLLOW
computation, parsing-table construction, and a stack-based predictive parser
with a full step-by-step trace, live stack/input visualization, parsing-table
cell highlighting, and an optional parse tree.

Built entirely on the Python standard library — no external dependencies
required.

---

## Quick start

```bash
# (Linux only, if Tkinter isn't already installed)
sudo apt install python3-tk

# Run the app
cd PredictiveParser
python3 main.py
```

Requires Python 3.8+. See `requirements.txt` for details (there is nothing to
`pip install` for normal use).

---

## Project layout

```
PredictiveParser/
│
├── main.py            Entry point - run this file
├── grammar.py          Grammar definition (dict-based) + helpers
├── first_follow.py      FIRST / FOLLOW set computation
├── parsing_table.py     LL(1) parsing table construction + conflict detection
├── parser.py            Stack-based, table-driven predictive parser
├── parse_tree.py         Optional parse-tree layout & rendering
├── gui.py               Tkinter GUI (5-tab notebook)
├── utils.py              Shared helpers (formatting, CSV/TXT export)
├── test_cases.py          Predefined accepted/rejected test strings
├── assets/                (reserved for icons/images, currently empty)
└── requirements.txt
```

Each module has a single responsibility and can also be run directly for a
quick console self-check, e.g.:

```bash
python3 grammar.py          # prints grammar / terminals / non-terminals
python3 first_follow.py     # prints FIRST and FOLLOW sets
python3 parsing_table.py    # prints the parsing table + any conflicts
python3 parser.py           # parses two sample strings and prints the trace
python3 test_cases.py       # runs all 8 predefined test cases and reports PASS/FAIL
```

---

## The grammar

The grammar given in the assignment is:

```
S  → A B C
A  → a b A | a b
B  → b | B C
C  → c | c C
```

As written it is **not** directly usable by a non-recursive predictive parser:

- `B → b | B C` is immediately left-recursive — a naive predictive parser would
  keep expanding `B` forever and get stuck in an infinite loop (exactly the
  trap hinted at in the assignment).
- `A → a b A | a b` and `C → c | c C` each share a common prefix, which is a
  source of FIRST/FIRST ambiguity.

The assignment explicitly permits generating an equivalent grammar by removing
ambiguities and immediate left-recursion. The app does this **programmatically**
in `grammar.py` (see `eliminate_immediate_left_recursion` and `left_factor`),
turning the original grammar into the equivalent LL(1)-friendly one used by the
parser:

```
S  → A B C
A  → a b A'
A' → A | ε
B  → b B'
B' → C B' | ε
C  → c C'
C' → C | ε
```

- **Start symbol:** `S`
- **Non-terminals:** `S, A, A', B, B', C, C'`
- **Terminals:** `a, b, c, $`

The language both grammars generate is `(ab)^n b c^k`, for `n ≥ 1, k ≥ 1`.

### A note on LL(1) conflicts

While implementing the parsing table, two genuine conflicts were found:

- `M[B', c]` — both `B' → C B'` and `B' → ε` apply
- `M[C', c]` — both `C' → C` and `C' → ε` apply

This is not a bug in the FIRST/FOLLOW/table algorithm — it's an inherent
property of this grammar: a run of `c`'s can be generated either through the
`B'` chain or through the trailing `C` in `S → A B C`, and one token of
lookahead cannot tell which path is intended. Strictly speaking, this makes
the grammar **not LL(1)**.

The app doesn't hide this. It's reported on the **Grammar tab** under "LL(1)
Verification," and flagged with a ⚠ marker on the corresponding cells of the
**Parsing Table tab**. To let the demonstration still run to completion, each
conflicting cell is resolved by an explicit, documented override in
`parsing_table.py` (`CONFLICT_RESOLUTION`):

- `M[B', c]` → resolved to `B' → ε`
- `M[C', c]` → resolved to `C' → C`

With this resolution, all 8 predefined test cases parse exactly as expected
(verified in both Automatic and Step execution modes — see `test_cases.py`).

---

## Using the application

The GUI is organized into five tabs:

1. **Grammar** — productions, start symbol, terminals/non-terminals, and the
   LL(1) verification summary described above.
2. **FIRST & FOLLOW** — computed FIRST and FOLLOW sets for every non-terminal.
3. **Parsing Table** — the full LL(1) table (conflicts marked with ⚠),
   with CSV export and FIRST/FOLLOW TXT export.
4. **Parser** — the main workspace:
   - Type any string, or pick one of the predefined test cases from the
     dropdown.
   - **Parse (Automatic)** runs the parser to completion in one click.
   - **Step** performs exactly one parser action per click (push/expand/
     match/accept/reject), updating the stack view, input buffer pointer,
     current action, and parsing-table highlight after every click.
   - **Reset** clears the current run so you can try another string.
   - The **Parsing Trace** table logs every step (step number, stack
     contents, remaining input, action taken), and can be exported to CSV
     or TXT.
   - The result banner shows ✅ **ACCEPTED** or ❌ **REJECTED** with a
     specific error message (expected vs. found symbol, or "no production"
     for an undefined table cell).
5. **Parse Tree** — after a successful parse, shows the derivation both as
   a graphical tree (Canvas) and as an indented text tree.

### Predefined test cases

| Expected | Strings |
|---|---|
| Accepted | `abbcc`, `ababbcc`, `ababbcccc` |
| Rejected | `abc`, `abb`, `bcc`, `abca`, `accc` |

---

## Extending the project

- Swap in a different grammar by editing `GRAMMAR` / `START_SYMBOL` in
  `grammar.py` — every other module reads from these, so nothing else needs
  to change for a grammar that *is* strictly LL(1) (no `CONFLICT_RESOLUTION`
  entries needed).
- `parse_tree.py` currently draws with a simple built-in Canvas layout;
  swap in `graphviz` there if you'd like nicer rendering.
- `utils.py`'s CSV export could be swapped for `pandas.DataFrame.to_csv`
  if you prefer working with DataFrames.
