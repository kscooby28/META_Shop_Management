"""Full-yard folder contract (WO13 paves it, the owner fills it later).

Folder: ``<repo>/yard-photos``, one subfolder per car. Each car folder
holds photos plus an optional ``notes.txt`` naming runs, miles, and
why-parked where known. The loader reports an absent or empty folder
cleanly and never invents data: missing notes or missing keys read as
unknown, and no cars, parts, or values are ever guessed.

``yard-photos/`` is git-ignored so staged real photos can never be
swept into the submission.
"""

import os

YARD_DIR_NAME = "yard-photos"
NOTES_NAME = "notes.txt"
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp")
KNOWN_KEYS = ("runs", "miles", "why_parked")
UNKNOWN = "unknown"


def yard_dir(root):
    return os.path.join(root, YARD_DIR_NAME)


def parse_notes(text):
    """Parse ``key: value`` lines. Missing keys stay unknown, never guessed."""
    notes = {key: UNKNOWN for key in KNOWN_KEYS}
    more = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower().replace("-", "_").replace(" ", "_")
        value = value.strip()
        if not value:
            continue
        if key in notes:
            notes[key] = value
        else:
            more[key] = value
    notes["more"] = more
    return notes


def load_yard(root):
    """Read the staged yard folder. Absent or empty reads clean, no invention."""
    path = yard_dir(root)
    if not os.path.isdir(path):
        return {
            "status": "absent",
            "dir": YARD_DIR_NAME,
            "notice": ("No yard-photos folder staged yet. The owner stages "
                       "one subfolder per car, photos plus a notes file, and "
                       "the full-yard follow-up runs them."),
            "cars": [],
        }
    try:
        folders = sorted(name for name in os.listdir(path)
                         if os.path.isdir(os.path.join(path, name)))
    except OSError:
        folders = []
    if not folders:
        return {
            "status": "empty",
            "dir": YARD_DIR_NAME,
            "notice": ("The yard-photos folder is staged but holds no car "
                       "folders yet, so there is nothing to measure."),
            "cars": [],
        }
    cars = []
    for folder in folders:
        car_dir = os.path.join(path, folder)
        try:
            names = sorted(os.listdir(car_dir))
        except OSError:
            names = []
        photos = [n for n in names
                  if n.lower().endswith(PHOTO_EXTS)
                  and os.path.isfile(os.path.join(car_dir, n))]
        notes_text = ""
        if NOTES_NAME in names:
            try:
                with open(os.path.join(car_dir, NOTES_NAME),
                          "r", encoding="utf-8") as fh:
                    notes_text = fh.read()
            except OSError:
                notes_text = ""
        cars.append({
            "car": folder,
            "photos": photos,
            "notes": parse_notes(notes_text),
        })
    return {
        "status": "ok",
        "dir": YARD_DIR_NAME,
        "notice": "",
        "cars": cars,
    }
