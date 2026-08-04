"""
parser.py
---------
A non-recursive, table-driven (stack-based) LL(1) predictive parser.

The parser never uses recursive descent: control is driven entirely by an
explicit stack, the remaining input buffer and the pre-computed parsing
table, exactly as required by the classical LL(1) algorithm:

    push $
    push StartSymbol
    while stack is not empty:
        X = top of stack
        a = current input symbol
        if X is a terminal (or $):
            if X == a: pop X, advance input
            else: error
        else:                                   # X is a non-terminal
            look up M[X, a]
            if entry exists: pop X, push RHS of the production (reversed)
            else: error
    accept if stack and input are both exhausted at the same time
"""

from grammar import GRAMMAR, START_SYMBOL, END_MARKER, EPSILON, is_terminal, production_to_string, format_production


class TreeNode:
    """A node of the parse tree, built incrementally as the parser runs."""
    __slots__ = ("symbol", "children", "matched")

    def __init__(self, symbol):
        self.symbol = symbol
        self.children = []
        self.matched = False  # True once a terminal leaf has been matched


class ParseStep:
    def __init__(self, step_no, stack, remaining_input, action, table_cell=None, error=None):
        self.step_no = step_no
        self.stack = stack                  # str, top-of-stack shown last (e.g. "$ C B A")
        self.remaining_input = remaining_input
        self.action = action
        self.table_cell = table_cell        # (nt, terminal) if this step consulted the table
        self.error = error

    def as_tuple(self):
        return (self.step_no, self.stack, self.remaining_input, self.action)


class ParseResult:
    def __init__(self, accepted, steps, error_message=None, tree_root=None):
        self.accepted = accepted
        self.steps = steps
        self.error_message = error_message
        self.tree_root = tree_root


def tokenize(input_string):
    """Turn the raw user string into a token list terminated by '$'.
    Every character is treated as an individual terminal symbol (this
    grammar's terminals are all single characters: a, b, c)."""
    tokens = [ch for ch in input_string.strip() if not ch.isspace()]
    tokens.append(END_MARKER)
    return tokens


class PredictiveParser:
    """Stateful stack-based parser supporting both full-run and single-step
    execution (needed by the GUI's Automatic / Step modes)."""

    def __init__(self, table_result, grammar=GRAMMAR, start_symbol=START_SYMBOL):
        self.table_result = table_result
        self.grammar = grammar
        self.start_symbol = start_symbol
        self.reset("")

    # ------------------------------------------------------------------ #
    # Setup / state
    # ------------------------------------------------------------------ #
    def reset(self, input_string):
        self.tokens = tokenize(input_string)
        self.pos = 0
        self.step_no = 0
        self.finished = False
        self.accepted = False
        self.error_message = None
        self.steps = []

        root = TreeNode(self.start_symbol)
        self.tree_root = root
        # parallel stacks: grammar-symbol stack and matching tree-node stack
        self.symbol_stack = [END_MARKER, self.start_symbol]
        self.node_stack = [None, root]

        self._record(f"Initialize: push {END_MARKER}, push start symbol {self.start_symbol}")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _stack_display(self):
        # Bottom of stack first, top last (top is what is examined next)
        return " ".join(self.symbol_stack) if self.symbol_stack else "(empty)"

    def _remaining_input_display(self):
        return "".join(self.tokens[self.pos:])

    def _record(self, action, table_cell=None, error=None):
        self.step_no += 1
        self.steps.append(ParseStep(
            self.step_no,
            self._stack_display(),
            self._remaining_input_display(),
            action,
            table_cell=table_cell,
            error=error,
        ))

    def current_input_symbol(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else END_MARKER

    # ------------------------------------------------------------------ #
    # Single-step execution (Step Mode)
    # ------------------------------------------------------------------ #
    def step(self):
        """Perform exactly one parser action. Returns the ParseStep taken,
        or None if parsing has already finished."""
        if self.finished:
            return None

        if not self.symbol_stack:
            # Should not normally happen (END_MARKER handles this) but guard anyway.
            self.finished = True
            self.accepted = (self.current_input_symbol() == END_MARKER)
            return None

        top = self.symbol_stack[-1]
        top_node = self.node_stack[-1]
        cur = self.current_input_symbol()

        # Case 1: stack top is the end marker -> success/failure decision
        if top == END_MARKER:
            self.symbol_stack.pop()
            self.node_stack.pop()
            if cur == END_MARKER:
                self._record("Accept: stack and input both exhausted")
                self.finished = True
                self.accepted = True
            else:
                msg = f"Rejected: input not fully consumed (found '{cur}' after stack emptied)"
                self._record(msg, error=msg)
                self.finished = True
                self.accepted = False
            return self.steps[-1]

        # Case 2: stack top is a terminal -> try to match
        if is_terminal(top, self.grammar):
            if top == cur:
                self.symbol_stack.pop()
                self.node_stack.pop()
                top_node.matched = True
                self.pos += 1
                self._record(f"Match terminal '{top}'")
            else:
                msg = f"Error: Expected '{top}', Found '{cur}'"
                self._record(msg, error=msg)
                self.finished = True
                self.accepted = False
            return self.steps[-1]

        # Case 3: stack top is a non-terminal -> consult the parsing table
        entry = self.table_result.get(top, cur)
        cell = (top, cur)
        if entry is None:
            msg = f"Error: No production M[{top}, {cur}]"
            self._record(msg, table_cell=cell, error=msg)
            self.finished = True
            self.accepted = False
            return self.steps[-1]

        # Pop the non-terminal, push its production's RHS (reversed so the
        # left-most symbol ends up on top of the stack)
        self.symbol_stack.pop()
        self.node_stack.pop()

        if entry:  # non-epsilon production
            children = [TreeNode(sym) for sym in entry]
            top_node.children = children
            for sym, child in zip(reversed(entry), reversed(children)):
                self.symbol_stack.append(sym)
                self.node_stack.append(child)
            action = f"Expand {format_production(top, entry)}"
        else:  # epsilon production
            eps_child = TreeNode(EPSILON)
            eps_child.matched = True
            top_node.children = [eps_child]
            action = f"Expand {format_production(top, entry)}"

        self._record(action, table_cell=cell)
        return self.steps[-1]

    # ------------------------------------------------------------------ #
    # Full run (Automatic Mode)
    # ------------------------------------------------------------------ #
    def run_to_completion(self, max_steps=10000):
        count = 0
        while not self.finished and count < max_steps:
            self.step()
            count += 1
        if not self.finished:
            self.error_message = "Aborted: exceeded maximum step count (possible infinite loop)."
            self.accepted = False
            self.finished = True
        if not self.accepted and self.error_message is None:
            last = self.steps[-1] if self.steps else None
            self.error_message = last.error if last else "Rejected"
        return self.result()

    def result(self):
        return ParseResult(self.accepted, list(self.steps), self.error_message, self.tree_root)


def parse_string(table_result, input_string, grammar=GRAMMAR, start_symbol=START_SYMBOL):
    """Convenience one-shot helper used by tests / console mode."""
    parser = PredictiveParser(table_result, grammar, start_symbol)
    parser.reset(input_string)
    return parser.run_to_completion()


if __name__ == "__main__":
    from first_follow import compute_first, compute_follow
    from parsing_table import build_parsing_table

    first = compute_first()
    follow = compute_follow(first_sets=first)
    table = build_parsing_table(first_sets=first, follow_sets=follow)

    for s in ["abbcc", "ababbcc"]:
        res = parse_string(table, s)
        print(f"\nInput: {s!r} -> {'ACCEPTED' if res.accepted else 'REJECTED'}")
        for st in res.steps:
            print(f"  {st.step_no:>3} | {st.stack:<15} | {st.remaining_input:<12} | {st.action}")
