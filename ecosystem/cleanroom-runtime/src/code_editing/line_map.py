from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(slots=True)
class FileSnapshot:
    path: str
    content: str
    content_hash: str
    lines: list[str]

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def line(self, line_no: int) -> str:
        return self.lines[line_no - 1]

    def slice_lines(self, start_line: int, end_line: int) -> list[str]:
        return self.lines[start_line - 1:end_line]

    def preview(self, start_line: int = 1, end_line: int | None = None) -> list[dict[str, str | int]]:
        last = end_line or self.line_count
        return [
            {'line': idx + 1, 'text': text}
            for idx, text in enumerate(self.lines[start_line - 1:last], start=start_line - 1)
        ]


def compute_hash(content: str) -> str:
    return sha256(content.encode('utf-8')).hexdigest()


def load_snapshot(path: str | Path) -> FileSnapshot:
    file_path = Path(path)
    content = file_path.read_text(encoding='utf-8')
    return FileSnapshot(
        path=str(file_path),
        content=content,
        content_hash=compute_hash(content),
        lines=content.splitlines(),
    )
