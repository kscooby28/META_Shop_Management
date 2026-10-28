"""Muse Spark Open adapter: second-look grades via Baseten, demo-safe.

Spark Open is the open-weight model in the Compare stage. It re-grades the
same case evidence the pipeline already graded; its result is a second
look beside the rule grade, never an overrule. This adapter attempts one
live Baseten call when the key is present under BASETEN_API_KEY, with no
retries; anything else (no key, any failure) falls back to the demo-cache
sample, honestly labeled. Key names only are ever checked; values are
never printed or logged.

Isolated adapter with its own transport and key loading, following the
meta_client pattern. SPARK_OPEN_LIVE gates live attempts (on: Baseten is
outside the Meta rotation gate). Endpoint and model are the exact pinned
strings, not guesses.
"""

import json
import os
import urllib.error
import urllib.request

from meta_client import MetaAPIError

# Live Baseten attempts stay ON: the Baseten key was never pasted anywhere
# and is not covered by the Meta rotation gate. Tests flip this off to
# prove the demo path without touching the network.
SPARK_OPEN_LIVE = True
BASETEN_ENDPOINT = "https://inference.baseten.co/v1"
SPARK_OPEN_MODEL = "meta-models/muse-spark-open-1026"
BASETEN_KEY_NAME = "BASETEN_API_KEY"
TIMEOUT_SECONDS = 45
GRADES = ("A", "B", "C")

GRADE_PROMPT = """You give a second look at used-part grades. Meaning: A means
pull and list now, B means worth it if you are standing there, C means
leave it. Given the case evidence as JSON (parts with condition, frames
seen, count, demand, price range with source, pull effort), reply with
JSON only: {"grades": [{"part_id": ..., "grade": "A"|"B"|"C",
"reason": ...}]}. One entry per part, same part_ids, reasons in plain
words naming the evidence you leaned on. Never invent part numbers,
prices, or facts not in the evidence; if the evidence is thin, say so in
the reason and grade honestly."""


def _key_present():
    if os.environ.get(BASETEN_KEY_NAME, "").strip():
        return True
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                  "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(BASETEN_KEY_NAME + "=") and line.split("=", 1)[1].strip():
                    return True
    except OSError:
        pass
    return False


def _api_key():
    key = os.environ.get(BASETEN_KEY_NAME, "").strip()
    if key:
        return key
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                  "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(BASETEN_KEY_NAME + "="):
                    key = line.split("=", 1)[1].strip().strip("'").strip('"')
                    if key:
                        return key
    except OSError:
        pass
    raise MetaAPIError("no %s in the local environment" % BASETEN_KEY_NAME, kind="auth")


def request_grades(evidence):
    """Ask Spark Open via Baseten for second-look grades. One call, no retry.

    Raises MetaAPIError without touching the network unless the live flag
    is on, evidence is present, and the key is present. Any transport,
    auth, or shape problem raises so the caller falls back to demo cache.
    """
    if not SPARK_OPEN_LIVE:
        raise MetaAPIError("spark open live is off", kind="unreachable")
    if not evidence:
        raise MetaAPIError("no evidence to grade", kind="bad_response")
    if not _key_present():
        raise MetaAPIError("no %s in the local environment" % BASETEN_KEY_NAME, kind="auth")
    body = json.dumps({
        "model": SPARK_OPEN_MODEL,
        "messages": [
            {"role": "system", "content": GRADE_PROMPT},
            {"role": "user", "content": json.dumps(evidence)},
        ],
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    request = urllib.request.Request(
        BASETEN_ENDPOINT + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + _api_key(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise MetaAPIError("Baseten key rejected (%s)" % exc.code, kind="auth")
        raise MetaAPIError("Baseten error %s" % exc.code, kind="unreachable")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise MetaAPIError("Baseten unreachable: %s" % exc, kind="unreachable")
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        grades = parsed["grades"]
        assert isinstance(grades, list) and grades
        cleaned = []
        for entry in grades:
            assert entry.get("part_id") and entry.get("grade") in GRADES
            cleaned.append({
                "part_id": entry["part_id"],
                "grade": entry["grade"],
                "reason": entry.get("reason") or "",
            })
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        raise MetaAPIError("Spark Open returned an unusable shape: %s" % exc,
                           kind="bad_response")
    return {"grades": cleaned, "source": "spark-open-live"}


def demo_grades(root):
    """Demo second-look grades for the anonymized demo set. Offline."""
    samples = {}
    try:
        with open(os.path.join(root, "demo_cache", "compare.demo.json"),
                  "r", encoding="utf-8") as fh:
            samples = json.load(fh).get("spark_open", {})
    except (OSError, ValueError):
        pass
    return {
        "grades": [
            {"part_id": pid, "grade": g.get("grade", "C"),
             "reason": g.get("reason", "")}
            for pid, g in sorted(samples.items())
        ],
        "source": "demo-cache: spark open sample",
    }


def compare_grades(evidence, part_ids, root):
    """Gated entry: one live attempt when possible, else the demo sample.

    Returns {grades, mode, source, notice}. Live grades are filtered to
    the case's own part_ids; unknown ids from the model are dropped and
    named, never rendered.
    """
    try:
        result = request_grades(evidence)
        mode, notice = "live", ""
    except MetaAPIError as exc:
        result = demo_grades(root)
        mode = "demo-cache"
        if exc.kind == "auth" and "BASETEN_API_KEY" in str(exc):
            notice = ("No Baseten key under BASETEN_API_KEY, so this side shows "
                      "the demo sample. Add the key to run Spark Open live.")
        else:
            notice = ("Spark Open live failed (%s), so this side shows the demo "
                      "sample." % exc)
    known = set(part_ids or [])
    kept, dropped = [], 0
    for entry in result["grades"]:
        if not known or entry["part_id"] in known:
            kept.append(entry)
        else:
            dropped += 1
    if dropped:
        notice = (notice + " " if notice else "") + \
            "%d live grade(s) named unknown parts and were dropped." % dropped
    return {"grades": kept, "mode": mode, "source": result["source"], "notice": notice}
