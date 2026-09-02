import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cli.app import WispApp  # noqa: E402


def main() -> None:
    app = WispApp()
    app.run()


if __name__ == "__main__":
    main()
