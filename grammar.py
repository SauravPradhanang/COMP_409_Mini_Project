"""
grammar.py
----------
Defines the (already left-recursion-eliminated) grammar used throughout the
application, plus small helper functions for inspecting it.

Grammar (as given):

    S  -> A B C
    A  -> a b A'
    A' -> A | epsilon
    B  -> b B'
    B' -> C B' | epsilon
    C  -> c C'
    C' -> C | epsilon

Internal representation
------------------------
The grammar is stored as an (ordered) dictionary:

    { non_terminal : [ production_1, production_2, ... ] }

Each production is a *list of symbols* (strings). The empty list ``[]``
represents an epsilon production. Terminals are plain lowercase letters,
non-terminals are any key of the dictionary (upper-case letters, optionally
followed by a single quote, e.g. ``"A'"``).
"""

EPSILON = "\u03b5"      # 'ε'
END_MARKER = "$"

START_SYMBOL = "S"

GRAMMAR = {
    "S":  [["A", "B", "C"]],
    "A":  [["a", "b", "A'"]],
    "A'": [["A"], []],
    "B":  [["b", "B'"]],
    "B'": [["C", "B'"], []],
    "C":  [["c", "C'"]],
    "C'": [["C"], []],
}


def get_non_terminals(grammar=GRAMMAR):
    """Return non-terminals in a stable, deterministic order."""
    return list(grammar.keys())


def get_terminals(grammar=GRAMMAR):
    """Scan every production and collect every symbol that is not itself
    a non-terminal (and is not epsilon). The end marker '$' is always
    included because it is required by the parsing table / parser."""
    terminals = []
    seen = set()
    for productions in grammar.values():
        for prod in productions:
            for sym in prod:
                if sym not in grammar and sym != EPSILON and sym not in seen:
                    terminals.append(sym)
                    seen.add(sym)
    if END_MARKER not in seen:
        terminals.append(END_MARKER)
    return terminals


def is_terminal(symbol, grammar=GRAMMAR):
    return symbol not in grammar and symbol != EPSILON


def is_non_terminal(symbol, grammar=GRAMMAR):
    return symbol in grammar


def production_to_string(prod):
    """Render a production (list of symbols) for display, e.g. ['a','b',"A'"] -> "a b A'"."""
    if not prod:
        return EPSILON
    return " ".join(prod)


def format_production(lhs, prod):
    return f"{lhs} \u2192 {production_to_string(prod)}"


if __name__ == "__main__":
    print("Start symbol:", START_SYMBOL)
    print("Non-terminals:", get_non_terminals())
    print("Terminals:", get_terminals())
    for nt, prods in GRAMMAR.items():
        for p in prods:
            print(" ", format_production(nt, p))
