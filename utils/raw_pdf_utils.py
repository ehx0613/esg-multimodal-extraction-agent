from pathlib import Path


def list_raw_pdfs(raw_data_dir: Path) -> list[Path]:
    return sorted(path for path in raw_data_dir.rglob("*.pdf") if path.is_file())


def find_raw_pdf_by_name(raw_data_dir: Path, filename: str) -> Path | None:
    exact_path = raw_data_dir / filename
    if exact_path.exists() and exact_path.is_file():
        return exact_path

    matches = [path for path in raw_data_dir.rglob(filename) if path.is_file()]
    if not matches:
        return None

    matches.sort(key=lambda p: (len(p.parts), str(p)))
    return matches[0]


__all__ = ["find_raw_pdf_by_name", "list_raw_pdfs"]
