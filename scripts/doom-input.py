#!/usr/bin/env python3
"""Drive a Chocolate Doom window from a compact, shell-like command stream."""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import time

DISPLAY = os.environ.get("DISPLAY", ":99")
BASE_DELAY = float(os.environ.get("DOOM_KEY_DELAY", "0.12"))

KEYS = {
    "space": "space", "enter": "Return", "return": "Return", "esc": "Escape", "escape": "Escape",
    "tab": "Tab", "backspace": "BackSpace", "delete": "Delete", "insert": "Insert",
    "home": "Home", "end": "End", "pageup": "Page_Up", "pagedown": "Page_Down",
    "up": "Up", "arrowup": "Up", "down": "Down", "arrowdown": "Down",
    "left": "Left", "arrowleft": "Left", "right": "Right", "arrowright": "Right",
    "shift": "Shift_L", "ctrl": "Control_L", "control": "Control_L", "alt": "Alt_L",
    "super": "Super_L", "meta": "Super_L", "capslock": "Caps_Lock",
    "minus": "minus", "plus": "plus", "equals": "equal", "comma": "comma", "period": "period",
    "slash": "slash", "backslash": "backslash", "semicolon": "semicolon", "apostrophe": "apostrophe",
    "lbracket": "bracketleft", "rbracket": "bracketright", "grave": "grave",
}
for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
    KEYS[ch] = ch
for n in range(1, 13):
    KEYS[f"f{n}"] = f"F{n}"

CLICK_BUTTONS = {
    "click": 1, "left-click": 1, "leftclick": 1,
    "right-click": 3, "rightclick": 3,
    "middle-click": 2, "middleclick": 2,
    "mouse1": 1, "mouse2": 2, "mouse3": 3,
}


def run(*args: str) -> None:
    subprocess.run(["xdotool", *args], env={**os.environ, "DISPLAY": DISPLAY}, check=True)


def hold(key: str, seconds: float = BASE_DELAY) -> None:
    run("keydown", key)
    time.sleep(max(0.02, seconds))
    run("keyup", key)


def key(name: str) -> None:
    mapped = KEYS.get(name.lower())
    if mapped is None:
        if not re.fullmatch(r"[A-Za-z0-9_+.-]+", name):
            raise ValueError(f"invalid key name: {name!r}")
        mapped = name
    hold(mapped)


def click(button: int) -> None:
    run("click", str(button))
    time.sleep(0.08)


def parse_count(token: str) -> tuple[str, int]:
    match = re.fullmatch(r"(.+?)(?:\*(\d+))?", token)
    if not match:
        raise ValueError(f"invalid action: {token}")
    count = int(match.group(2) or "1")
    if count < 1 or count > 200:
        raise ValueError("repeat count must be between 1 and 200")
    return match.group(1), count


def execute(token: str) -> None:
    action, count = parse_count(token)
    lower = action.lower()

    if lower.startswith("!wait:"):
        ms = int(lower.split(":", 1)[1])
        if not 0 <= ms <= 30000:
            raise ValueError("wait must be 0..30000 ms")
        time.sleep(ms / 1000.0)
        return

    if lower.startswith("!hold:"):
        parts = action.split(":", 2)
        if len(parts) != 3:
            raise ValueError("hold syntax is !hold:key:milliseconds")
        name, ms_text = parts[1], parts[2]
        ms = int(ms_text)
        if not 1 <= ms <= 30000:
            raise ValueError("hold must be 1..30000 ms")
        mapped = KEYS.get(name.lower(), name)
        if not re.fullmatch(r"[A-Za-z0-9_+.-]+", mapped):
            raise ValueError("invalid hold key")
        for _ in range(count):
            hold(mapped, ms / 1000.0)
        return

    if lower.startswith("!key:"):
        name = action.split(":", 1)[1]
        for _ in range(count):
            key(name)
        return

    if lower.startswith("!type:"):
        text = action.split(":", 1)[1]
        if len(text) > 160:
            raise ValueError("!type payload is limited to 160 characters")
        for _ in range(count):
            run("type", "--delay", "25", "--clearmodifiers", text)
        return

    if lower.startswith("!move:"):
        parts = action.split(":")
        if len(parts) != 3:
            raise ValueError("move syntax is !move:x:y")
        x, y = (int(parts[1]), int(parts[2]))
        if not (0 <= x <= 1279 and 0 <= y <= 719):
            raise ValueError("mouse coordinates must be within 1280x720")
        for _ in range(count):
            run("mousemove", str(x), str(y))
        return

    if lower.startswith("!mouse:"):
        parts = action.split(":")
        if len(parts) != 3:
            raise ValueError("mouse motion syntax is !mouse:dx:dy")
        dx, dy = int(parts[1]), int(parts[2])
        if abs(dx) > 1000 or abs(dy) > 1000:
            raise ValueError("mouse motion is limited to +/-1000")
        for _ in range(count):
            run("mousemove_relative", "--", str(dx), str(dy))
        return

    if lower in CLICK_BUTTONS:
        for _ in range(count):
            click(CLICK_BUTTONS[lower])
        return

    if lower.startswith("!"):
        name = lower[1:]
        for _ in range(count):
            key(name)
        return

    raise ValueError(f"unknown Doom action: {token}")


def normalize_tokens(tokens: list[str]) -> list[str]:
    """Accept both !left-click and the friendlier '!left click' spelling."""
    out: list[str] = []
    i = 0
    click_words = {
        ("!left", "click"): "!left-click",
        ("!right", "click"): "!right-click",
        ("!middle", "click"): "!middle-click",
    }
    while i < len(tokens):
        if i + 1 < len(tokens) and (tokens[i].lower(), tokens[i + 1].lower()) in click_words:
            out.append(click_words[(tokens[i].lower(), tokens[i + 1].lower())])
            i += 2
        else:
            out.append(tokens[i])
            i += 1
    return out


def find_window() -> str | None:
    try:
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", "Chocolate Doom"],
            env={**os.environ, "DISPLAY": DISPLAY},
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("xdotool is not installed", file=sys.stderr)
        return None
    windows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return windows[-1] if windows else None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: doom-input.py 'doom !w !w !d !space'", file=sys.stderr)
        return 2

    command = sys.argv[1].strip()
    if not re.match(r"^doom(?:\s|$)", command, re.I):
        print("command must start with doom", file=sys.stderr)
        return 2

    payload = command[4:].strip()
    try:
        tokens = normalize_tokens(shlex.split(payload, posix=True))
    except ValueError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 2

    if not tokens:
        # Bare `doom` means: boot Chocolate Doom and leave the title/home screen visible.
        tokens = ["!wait:800"]

    if len(tokens) > 80:
        print("too many Doom actions (max 80)", file=sys.stderr)
        return 2

    window = None
    for _ in range(30):
        window = find_window()
        if window:
            break
        time.sleep(0.25)
    if not window:
        print("Chocolate Doom window did not appear", file=sys.stderr)
        return 1

    # GitHub Actions runners have no window manager. `windowactivate` therefore
    # fails with _NET_ACTIVE_WINDOW errors. The X server already has the SDL
    # window; use XSetInputFocus directly instead and tolerate focus refusal.
    subprocess.run(
        ["xdotool", "windowfocus", "--sync", window],
        env={**os.environ, "DISPLAY": DISPLAY},
        check=False,
    )

    print(f"Doom window: {window}")
    print(f"Doom actions: {len(tokens)}")
    for i, token in enumerate(tokens, 1):
        print(f"[{i:02d}] {token}")
        execute(token)

    time.sleep(0.35)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
