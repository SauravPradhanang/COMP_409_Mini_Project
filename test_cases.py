"""
test_cases.py
-------------
Predefined test strings used by the GUI's "Test Cases" selector and by the
console self-test (`python3 test_cases.py`).
"""

ACCEPTED_CASES = [
    "abbcc",
    "ababbcc",
    "ababbcccc",
]

REJECTED_CASES = [
    "abc",
    "abb",
    "bcc",
    "abca",
    "accc",
]

ALL_CASES = [(s, True) for s in ACCEPTED_CASES] + [(s, False) for s in REJECTED_CASES]


if __name__ == "__main__":
    from first_follow import compute_first, compute_follow
    from parsing_table import build_parsing_table
    from parser import parse_string

    first = compute_first()
    follow = compute_follow(first_sets=first)
    table = build_parsing_table(first_sets=first, follow_sets=follow)

    print("LL(1) conflicts:")
    for c in table.conflicts:
        print(f"  M{c['cell']}: {c['candidates']} -> resolved to {c['resolved_to']}")

    print("\nRunning predefined test cases:")
    all_ok = True
    for s, expected in ALL_CASES:
        res = parse_string(table, s)
        status = "PASS" if res.accepted == expected else "FAIL"
        if status == "FAIL":
            all_ok = False
        outcome = "ACCEPTED" if res.accepted else "REJECTED"
        expected_str = "ACCEPTED" if expected else "REJECTED"
        print(f"  [{status}] {s!r:<14} -> {outcome:<9} (expected {expected_str})"
              + (f"  | {res.error_message}" if res.error_message else ""))

    print("\nAll tests passed!" if all_ok else "\nSome tests FAILED.")
