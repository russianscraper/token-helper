import os
import subprocess
import sys


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_path = os.path.join(base_dir, "requirements.txt")

    if not os.path.isfile(requirements_path):
        print(f"requirements.txt introuvable: {requirements_path}")
        return 1

    cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_path]
    print(" ".join(cmd))

    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
