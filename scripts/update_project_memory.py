import argparse
import json
from pathlib import Path

from utils.project_memory import write_project_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh compact project memory documents.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    print(json.dumps(write_project_memory(Path(args.root)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
