"""Check UI rules: scan for emoji, dashes, gradients, purple, banned words, etc."""

import os
import re
import sys

# Banned patterns
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    re.UNICODE,
)

BANNED_WORDS = [
    "seamless", "unlock", "revolutionize", "leverage", "empower",
    "elevate", "cutting-edge", "next-gen", "supercharge", "effortless",
    "journey", "game-changer",
]

BANNED_PHRASES = [
    "ai-powered", "powered by ai", "made with",
]

# Patterns to check
CHECKS = [
    ("Emoji", EMOJI_PATTERN),
    ("Em dash", re.compile(r"\u2014")),
    ("En dash", re.compile(r"\u2013")),
    ("Gradient (CSS)", re.compile(r"gradient", re.IGNORECASE)),
    ("Purple", re.compile(r"\bpurple\b", re.IGNORECASE)),
    ("rounded-full", re.compile(r"rounded-full", re.IGNORECASE)),
]

# border-radius above 8px
BORDER_RADIUS_PATTERN = re.compile(r"border-radius\s*:\s*(\d+)px")

SCAN_EXTENSIONS = {".py", ".css", ".html", ".js", ".ts", ".json", ".md", ".yml", ".yaml"}
EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv"}
SCRIPT_NAME = os.path.basename(__file__)


def scan_file(filepath: str) -> list[str]:
    """Scan a single file for violations."""
    violations = []

    # Skip this script itself
    if os.path.basename(filepath) == SCRIPT_NAME:
        return []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception:
        return []

    for line_num, line in enumerate(lines, 1):
        for check_name, pattern in CHECKS:
            if pattern.search(line):
                violations.append(f"{filepath}:{line_num} - {check_name}: {line.strip()[:80]}")

        # Check banned words
        line_lower = line.lower()
        for word in BANNED_WORDS:
            if word in line_lower:
                violations.append(f"{filepath}:{line_num} - Banned word '{word}': {line.strip()[:80]}")

        for phrase in BANNED_PHRASES:
            if phrase in line_lower:
                violations.append(f"{filepath}:{line_num} - Banned phrase '{phrase}': {line.strip()[:80]}")

        # Check border-radius > 8px
        for match in BORDER_RADIUS_PATTERN.finditer(line):
            px_val = int(match.group(1))
            if px_val > 8:
                violations.append(f"{filepath}:{line_num} - border-radius {px_val}px (max 8px): {line.strip()[:80]}")

    return violations


def scan_directory(root_dir: str) -> list[str]:
    """Scan all files in a directory tree."""
    all_violations = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude certain directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SCAN_EXTENSIONS:
                filepath = os.path.join(dirpath, filename)
                violations = scan_file(filepath)
                all_violations.extend(violations)

    return all_violations


def main():
    project_root = os.path.join(os.path.dirname(__file__), "..")
    app_dir = os.path.join(project_root, "app")

    print("Scanning app/ directory for UI rule violations...")
    print("=" * 60)

    violations = scan_directory(app_dir)

    # Also scan data/
    data_dir = os.path.join(project_root, "data")
    if os.path.exists(data_dir):
        violations.extend(scan_directory(data_dir))

    if violations:
        print(f"Found {len(violations)} violation(s):\n")
        for v in violations:
            print(f"  {v}")
        print(f"\nTotal: {len(violations)} violations")
        sys.exit(1)
    else:
        print("No violations found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
