"""Dùng: python -m voc.cli validate data/sample/service_case_feedback.csv service_case_feedback"""
import json
import sys

from .validator import validate_file
from .counting import count_units


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 3 or argv[0] != "validate":
        print(__doc__)
        return 2
    m = validate_file(argv[1], argv[2])
    print(json.dumps(m.summary(), ensure_ascii=False, indent=2))
    print(json.dumps(count_units(m.accepted_rows), ensure_ascii=False, indent=2))
    return 0 if m.reconcile() else 1


if __name__ == "__main__":
    raise SystemExit(main())
