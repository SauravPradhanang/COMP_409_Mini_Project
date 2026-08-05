"""
parsing_table.py
-----------------
Builds the LL(1) predictive-parsing table M[NonTerminal, Terminal] from the
grammar plus its FIRST and FOLLOW sets, following the standard algorithm:

    For every production  A -> alpha :
        for every terminal t in FIRST(alpha):
            M[A, t] = A -> alpha
        if epsilon is in FIRST(alpha):
            for every terminal t in FOLLOW(A):
                M[A, t] = A -> alpha

IMPORTANT - grammar analysis
-----------------------------
This particular textbook grammar is *not* strictly LL(1): two cells receive
more than one candidate production:

    M[B', c]  ->  B' -> C B'   AND   B' -> epsilon
    M[C', c]  ->  C' -> C      AND   C' -> epsilon

This happens because the grammar lets a chain of C's be generated either
through B' or through the trailing C in `S -> A B C`; the two paths produce
the same terminal strings, so a single token of lookahead cannot tell them
apart. That is a genuine, inherent property of the grammar - not a bug in
the table-construction algorithm - and the application surfaces it to the
user (see `conflicts` returned by `build_parsing_table`) instead of hiding
it.

To let the demonstration parser still run to completion on the sample
strings, each conflicting cell is resolved by an explicit, documented
override (`CONFLICT_RESOLUTION`) rather than silently by "first production
wins". Both the conflict *and* the chosen resolution are reported to the
GUI so the user can see exactly what happened and why.
"""

from grammar import GRAMMAR, EPSILON, END_MARKER, is_non_terminal, format_production
from first_follow import compute_first, compute_follow, first_of_sequence, sorted_set

# Maps (non_terminal, terminal) -> the production (as a list of symbols) that
# should be used when more than one production is applicable for that cell. The
# entry is matched against GRAMMAR[non_terminal] *by content*, so it is robust
# to whatever production order the grammar transform happens to produce.
# See module docstring for why these overrides are needed.
CONFLICT_RESOLUTION = {
    ("B'", "c"): [],        # prefer  B' -> epsilon
    ("C'", "c"): ["C"],     # prefer  C' -> C
}


class ParsingTableResult:
    def __init__(self, table, conflicts, terminals, non_terminals):
        self.table = table                # {(nt, term): production (list)}
        self.raw_cells = {}                # {(nt, term): [production, ...]} all candidates
        self.conflicts = conflicts         # list of dicts describing each conflict
        self.terminals = terminals
        self.non_terminals = non_terminals

    def get(self, nt, term):
        return self.table.get((nt, term))

    def is_ll1(self):
        return len(self.conflicts) == 0


def build_parsing_table(grammar=GRAMMAR, first_sets=None, follow_sets=None,
                         terminals=None, non_terminals=None):
    if first_sets is None:
        first_sets = compute_first(grammar)
    if follow_sets is None:
        follow_sets = compute_follow(grammar, first_sets)
    if non_terminals is None:
        non_terminals = list(grammar.keys())
    if terminals is None:
        from grammar import get_terminals
        terminals = [t for t in get_terminals(grammar) if t != END_MARKER] + [END_MARKER]

    table = {}
    raw_cells = {}   # (nt, term) -> list of (prod_index, production)
    conflicts = []

    for nt, productions in grammar.items():
        for idx, prod in enumerate(productions):
            seq_first = first_of_sequence(prod, first_sets, grammar)
            target_terms = set(seq_first - {EPSILON})
            if EPSILON in seq_first:
                target_terms |= follow_sets[nt]

            for t in target_terms:
                key = (nt, t)
                raw_cells.setdefault(key, []).append((idx, prod))

    # Resolve every cell (detect + record conflicts, then pick final entry)
    for key, candidates in raw_cells.items():
        nt, t = key
        if len(candidates) == 1:
            table[key] = candidates[0][1]
        else:
            chosen_prod = CONFLICT_RESOLUTION.get(key)
            if chosen_prod is None or chosen_prod not in grammar[nt]:
                chosen_prod = candidates[0][1]   # default: first-listed production
            table[key] = chosen_prod

            conflicts.append({
                "cell": key,
                "candidates": [format_production(nt, p) for _, p in candidates],
                "resolved_to": format_production(nt, chosen_prod),
            })

    result = ParsingTableResult(table, conflicts, terminals, non_terminals)
    result.raw_cells = raw_cells
    return result


if __name__ == "__main__":
    first = compute_first()
    follow = compute_follow(first_sets=first)
    result = build_parsing_table(first_sets=first, follow_sets=follow)

    terms = result.terminals
    print("Parsing Table")
    header = "      " + "".join(f"{t:>8}" for t in terms)
    print(header)
    print("-" * len(header))
    for nt in result.non_terminals:
        row = f"{nt:>5} "
        for t in terms:
            entry = result.get(nt, t)
            cell = format_production(nt, entry) if entry is not None else ""
            row += f"{cell:>8}" if len(cell) <= 8 else f" {cell}"
        print(row)

    print("\nLL(1)?", result.is_ll1())
    if result.conflicts:
        print("Conflicts detected:")
        for c in result.conflicts:
            print(f"  M{c['cell']}: candidates = {c['candidates']}  -> resolved to: {c['resolved_to']}")
