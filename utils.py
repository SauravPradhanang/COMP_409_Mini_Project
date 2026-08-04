"""
utils.py
--------
Small shared helper functions (string formatting, CSV/TXT export, input
buffer pointer rendering) used by the GUI.
"""

import csv
import os
from grammar import EPSILON, END_MARKER


def format_set(s):
    return "{ " + ", ".join(sorted(s, key=lambda x: (x == END_MARKER, x))) + " }"


def render_input_with_pointer(tokens, pos):
    """Return two aligned lines: the token string, and a caret line
    pointing at index `pos` (Phase 12 - input buffer visualization)."""
    line = "".join(tokens)
    caret = " " * pos + "^"
    return line, caret


def export_rows_to_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def export_rows_to_txt(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as f:
        f.write("\t".join(str(h) for h in header) + "\n")
        f.write("-" * 60 + "\n")
        for row in rows:
            f.write("\t".join(str(c) for c in row) + "\n")
    return path
