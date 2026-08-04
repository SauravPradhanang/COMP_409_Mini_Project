"""
first_follow.py
----------------
Computes FIRST and FOLLOW sets for every non-terminal of a grammar.

Both computations use the classic *iterative fixed-point* strategy
(repeat until nothing changes) rather than naive recursion. This
automatically prevents infinite recursion on grammars that contain
mutually-recursive / self-referential non-terminals (e.g. this grammar's
``A' -> A`` together with ``A -> a b A'``), and it also removes duplicate
symbols for free because every set is a Python ``set``.
"""

from grammar import GRAMMAR, START_SYMBOL, END_MARKER, EPSILON, is_terminal, is_non_terminal


def first_of_sequence(seq, first_sets, grammar=GRAMMAR):
    """FIRST of a sequence of symbols (a production's right-hand side).

    Returns a set that may contain EPSILON if the whole sequence can
    derive the empty string.
    """
    if not seq:
        return {EPSILON}

    result = set()
    all_nullable = True
    for sym in seq:
        if is_terminal(sym, grammar):
            result.add(sym)
            all_nullable = False
            break
        else:
            sym_first = first_sets.get(sym, set())
            result |= (sym_first - {EPSILON})
            if EPSILON not in sym_first:
                all_nullable = False
                break
    if all_nullable:
        result.add(EPSILON)
    return result


def compute_first(grammar=GRAMMAR):
    """Compute FIRST(X) for every non-terminal X using fixed-point iteration."""
    first_sets = {nt: set() for nt in grammar}

    changed = True
    while changed:
        changed = False
        for nt, productions in grammar.items():
            for prod in productions:
                before = len(first_sets[nt])
                first_sets[nt] |= first_of_sequence(prod, first_sets, grammar)
                if len(first_sets[nt]) != before:
                    changed = True
    return first_sets


def compute_follow(grammar=GRAMMAR, first_sets=None, start_symbol=START_SYMBOL):
    """Compute FOLLOW(X) for every non-terminal X using fixed-point iteration."""
    if first_sets is None:
        first_sets = compute_first(grammar)

    follow_sets = {nt: set() for nt in grammar}
    follow_sets[start_symbol].add(END_MARKER)

    changed = True
    while changed:
        changed = False
        for lhs, productions in grammar.items():
            for prod in productions:
                for i, sym in enumerate(prod):
                    if not is_non_terminal(sym, grammar):
                        continue
                    beta = prod[i + 1:]
                    beta_first = first_of_sequence(beta, first_sets, grammar)

                    before = len(follow_sets[sym])
                    follow_sets[sym] |= (beta_first - {EPSILON})
                    if EPSILON in beta_first:
                        follow_sets[sym] |= follow_sets[lhs]
                    if len(follow_sets[sym]) != before:
                        changed = True
    return follow_sets


def sorted_set(s):
    """Deterministic display order: normal terminals alphabetically, '$' last."""
    return sorted(s, key=lambda x: (x == END_MARKER, x))


if __name__ == "__main__":
    first = compute_first()
    follow = compute_follow(first_sets=first)
    print("FIRST sets:")
    for nt in GRAMMAR:
        print(f"  FIRST({nt}) = {{ {', '.join(sorted_set(first[nt]))} }}")
    print("\nFOLLOW sets:")
    for nt in GRAMMAR:
        print(f"  FOLLOW({nt}) = {{ {', '.join(sorted_set(follow[nt]))} }}")
