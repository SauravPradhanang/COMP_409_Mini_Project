"""
parse_tree.py
-------------
Optional parse-tree support (Phase 17).

The tree itself is built incrementally by parser.PredictiveParser (each
TreeNode gets its children attached the moment its production is expanded).
This module only concerns itself with *displaying* an already-built tree:

  * `tree_to_text`   - an indented text representation (always available)
  * `compute_layout` - assigns (x, y) coordinates to every node
  * `draw_tree`       - draws the tree onto a Tkinter Canvas using the layout
"""


def tree_to_text(node, prefix="", is_last=True, lines=None):
    if lines is None:
        lines = []
    connector = "\u2514\u2500 " if is_last else "\u251c\u2500 "
    lines.append(prefix + (connector if prefix else "") + node.symbol)
    new_prefix = prefix + ("   " if is_last else "\u2502  ")
    for i, child in enumerate(node.children):
        tree_to_text(child, new_prefix, i == len(node.children) - 1, lines)
    return lines


def _count_leaves(node):
    if not node.children:
        return 1
    return sum(_count_leaves(c) for c in node.children)


def compute_layout(root, x0=20, y0=30, x_gap=50, y_gap=70):
    """Simple layered tree layout: assigns each node an (x, y) position and
    stores it in a dict keyed by id(node). Returns (positions, width, height)."""
    positions = {}
    next_x = [x0]

    def place(node, depth):
        if not node.children:
            x = next_x[0]
            next_x[0] += x_gap
            y = y0 + depth * y_gap
            positions[id(node)] = (x, y)
            return x
        child_xs = [place(child, depth + 1) for child in node.children]
        x = sum(child_xs) / len(child_xs)
        y = y0 + depth * y_gap
        positions[id(node)] = (x, y)
        return x

    place(root, 0)
    max_x = max((p[0] for p in positions.values()), default=x0) + x_gap
    max_y = max((p[1] for p in positions.values()), default=y0) + y_gap
    return positions, max_x, max_y


def draw_tree(canvas, root, positions, node_radius=18,
              node_color="#2b6cb0", matched_color="#2f855a",
              line_color="#a0aec0", text_color="white"):
    canvas.delete("all")

    def draw_edges(node):
        x1, y1 = positions[id(node)]
        for child in node.children:
            x2, y2 = positions[id(child)]
            canvas.create_line(x1, y1, x2, y2, fill=line_color, width=2)
            draw_edges(child)

    def draw_nodes(node):
        x, y = positions[id(node)]
        color = matched_color if getattr(node, "matched", False) else node_color
        canvas.create_oval(x - node_radius, y - node_radius, x + node_radius, y + node_radius,
                            fill=color, outline="#1a202c", width=2)
        canvas.create_text(x, y, text=node.symbol, fill=text_color, font=("Consolas", 10, "bold"))
        for child in node.children:
            draw_nodes(child)

    draw_edges(root)
    draw_nodes(root)
