"""
grammar.py
----------
Defines the (already left-recursion-eliminated) grammar used throughout the
application, plus small helper functions for inspecting it.

Grammar (as given):
~~~~~~~~~~~~~~~~~~~~
    S  -> A B C
    A  -> a b | a b A
    B  -> b | B C
    C  -> c | c C

This is the grammar from the assignment. As written it is NOT directly usable
by a non-recursive predictive (LL(1)) parser:

  * B -> b | B C  contains immediate left recursion, which would make the
    table-driven parser expand B forever (the program would get stuck / loop).
  * A -> a b | a b A  shares the common prefix "a b" across two productions,
    a source of FIRST/FIRST ambiguity.
  * C -> c | c C  shares the common prefix "c".

The hint in the assignment explicitly allows removing ambiguities and
immediate left-recursion. We do so programmatically in `transform` (which
chains `eliminate_immediate_left_recursion` and `left_factor`) so that the
working grammar `GRAMMAR` below is *derived* from `ORIGINAL_GRAMMAR` at import
time. The result still generates exactly the same language as the original:

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

# The grammar exactly as given in the assignment (before any transformation).
ORIGINAL_GRAMMAR = {
    "S":  [["A", "B", "C"]],
    "A":  [["a", "b", "A"], ["a", "b"]],   # common prefix "a b"  (ambiguous)
    "B":  [["b"], ["B", "C"]],             # immediate left recursion B -> B C
    "C":  [["c"], ["c", "C"]],             # common prefix "c"
}


def eliminate_immediate_left_recursion(grammar):
    """Remove immediate left recursion from a grammar.

    For every non-terminal A that has a production A -> A α (one whose right
    hand side *begins* with A), rewrite

        A  -> A α₁ | ... | A αₘ | β₁ | ... | βₙ   (βᵢ do not begin with A)

    as the equivalent, recursion-free pair:

        A  -> β₁ A' | ... | βₙ A'
        A' -> α₁ A' | ... | αₘ A' | ε

    The fresh helper A' is inserted immediately after A so that the resulting
    dictionary keeps a readable, deterministic order. Returns a new ordered
    dictionary."""
    out = {}
    for nt, productions in grammar.items():
        recursive = []        # αᵢ :- the tail after the leading nt
        nonrecursive = []     # βᵢ :- alternatives not starting with nt
        for prod in productions:
            if prod and prod[0] == nt:
                recursive.append(prod[1:])
            else:
                nonrecursive.append(prod)

        if not recursive:
            out[nt] = list(productions)
        else:
            helper = nt + "'"
            alts = [beta + [helper] for beta in nonrecursive]
            if not alts:
                alts = [[helper]]                      # pure left recursion
            out[nt] = alts
            out[helper] = [alpha + [helper] for alpha in recursive] + [[]]
    return out


def _longest_common_prefix(prod_lists):
    """Longest common prefix (a list of symbols) shared across the given RHS
    lists. Returns [] if there is none. An epsilon ([]) production blocks any
    factoring that would absorb it."""
    if not prod_lists or any(p == [] for p in prod_lists):
        return []
    first = prod_lists[0]
    limit = min(len(p) for p in prod_lists)
    prefix = []
    for i in range(limit):
        sym = first[i]
        if all(p[i] == sym for p in prod_lists):
            prefix.append(sym)
        else:
            break
    return prefix


def left_factor(grammar):
    """Remove common prefixes (left factoring) so that every non-terminal's
    alternatives have disjoint starting symbols.

    For a set of alternatives sharing the longest common prefix γ,

        A : γ δ1 | γ δ2 | ... | γ δk   (plus any other alternatives)

    they are rewritten as

        A : γ A' | (other alternatives)
        A' : δ1 | δ2 | ... | δk

    Helper nonterminals are placed right after their parent. Returns the
    transformed grammar as an ordered dictionary."""
    result = {}
    helpers = {}          # name -> factored alternatives

    for nt, productions in grammar.items():
        working = list(productions)
        out = []
        while len(working) > 1:
            prefix = _longest_common_prefix(working)
            if not prefix:
                break
            factored = [p[len(prefix):] for p in working
                        if p[:len(prefix)] == prefix]
            rest = [p for p in working if p[:len(prefix)] != prefix]
            helper = nt + "'"
            while helper in grammar or helper in helpers:
                helper += "'"
            helpers[helper] = factored
            out.append(prefix + [helper])
            working = rest
        out.extend(working)
        result[nt] = out

    # Place each created helper immediately after its parent non-terminal.
    final = {}
    for nt, productions in grammar.items():
        final[nt] = result[nt]
        for h in [k for k in helpers if _base(k) == nt]:
            final[h] = helpers[h]
    return final


def _base(symbol):
    """Strip trailing quotation marks: A'' -> A."""
    return symbol.rstrip("'")


def transform(original):
    """Produce an equivalent, LL(1)-friendly grammar by applying, in order:
        1. eliminate_immediate_left_recursion
        2. left_factor
    Nonterminal order is preserved (helpers placed beside their parents)."""
    gram = eliminate_immediate_left_recursion(original)
    gram = left_factor(gram)
    return gram


GRAMMAR = transform(ORIGINAL_GRAMMAR)


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
    print("\nOriginal grammar (as given in the assignment):")
    for nt, prods in ORIGINAL_GRAMMAR.items():
        for p in prods:
            print("   ", format_production(nt, p))
    print("\nTransformations applied:")
    print("   1. eliminate_immediate_left_recursion  (B -> b | B C  becomes  B -> b B', B' -> C B' | eps)")
    print("   2. left_factor  (A -> ab | ab A  and  C -> c | c C)")
    print("\nResulting (LL(1)) grammar:")
    for nt, prods in GRAMMAR.items():
        for p in prods:
            print("   ", format_production(nt, p))
    print("\nNon-terminals:", get_non_terminals())
    print("Terminals:", get_terminals())