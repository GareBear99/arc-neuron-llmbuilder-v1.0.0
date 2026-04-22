from __future__ import annotations

from arc_lang.cli.handlers import dispatch
from arc_lang.cli.parser import parse_args


def main() -> None:
    dispatch(parse_args())


if __name__ == "__main__":
    main()
