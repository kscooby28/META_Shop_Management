"""End-to-end demo smoke: runs the whole flow N times against a live server.

Usage:  python scripts/smoke_demo.py [base_url] [runs]
Default: http://127.0.0.1:8765, 10 runs.

Each run: session → intake (demo) → harvest → comps → verdicts → listing
draft → approve → mock post → chat. Asserts the A/B/C spread, plain-money
totals, the Approve gate (post-before-approve is refused), and SSE chat.
Exits nonzero on the first failure so "10 out of 10" is a real claim.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 10

NAMES = ["demo-frame-1", "demo-frame-2", "demo-frame-3", "demo-frame-4"]


def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except ValueError:
            return exc.code, {}


def post_sse(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as res:
        text = res.read().decode("utf-8")
    events = []
    for chunk in text.split("\n\n"):
        for line in chunk.splitlines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:].strip()))
    return events


def check(cond, what):
    if not cond:
        raise AssertionError(what)


def one_run(n):
    _, session = post("/api/session", {})
    sid = session["sessionId"]
    check(sid, "run %d: no session id" % n)

    _, intake = post(
        "/api/intake",
        {"sessionId": sid, "images": [{"name": x} for x in NAMES], "demo": True},
    )
    check(intake["mode"] == "demo-cache", "run %d: intake not cached" % n)
    check(intake["intake"]["car"]["trim"] == "unknown", "run %d: trim must stay unknown" % n)
    check(len(intake["intake"]["parts"]) == 7, "run %d: want 7 parts" % n)

    _, harvest = post("/api/harvest", {"sessionId": sid, "demo": True})
    parts = harvest["harvest"]["parts"]
    check(all(p["sightings"] for p in parts), "run %d: every part needs a sighting" % n)
    check(
        all(s.get("source_tag") for p in parts for s in p["sightings"]),
        "run %d: every sighting needs a source tag" % n,
    )

    _, comps = post("/api/comps", {"sessionId": sid})
    check("p_diff" in comps["comps"], "run %d: diff comp missing" % n)

    _, verdicts = post("/api/verdicts", {"sessionId": sid, "partInputs": {}})
    grades = {v["part_id"]: v["verdict"] for v in verdicts["report"]["verdicts"]}
    check(grades["p_diff"] == "A", "run %d: diff must be A" % n)
    check(grades["p_headlight"] == "B", "run %d: headlight must be B" % n)
    check(grades["p_taillight"] == "C", "run %d: taillight must be C" % n)
    totals = verdicts["report"]["totals"]
    check(totals["A"]["low"] == 1145 and totals["A"]["high"] == 1465, "run %d: A total wrong" % n)
    check("sure money" in totals["A"]["plain_words"], "run %d: A must say sure money" % n)
    check("maybe money" in totals["B"]["plain_words"], "run %d: B must say maybe money" % n)

    _, listing = post("/api/listing", {"sessionId": sid, "partId": "p_diff"})
    draft_id = listing["draftId"]
    check("differential" in listing["draft"]["title"].lower(), "run %d: draft title off" % n)
    check(listing["cutout"]["box"], "run %d: cutout box missing" % n)

    status, _ = post("/api/listing/post", {"sessionId": sid, "draftId": draft_id})
    check(status == 400, "run %d: post-before-approve must be refused" % n)

    post("/api/listing/approve", {"sessionId": sid, "draftId": draft_id, "destinations": ["ebay"]})
    _, posted = post("/api/listing/post", {"sessionId": sid, "draftId": draft_id})
    check(posted["receipt"]["adapter"] == "mock-outbox", "run %d: mock receipt missing" % n)

    events = post_sse("/api/chat", {"sessionId": sid, "message": "Why is this part a B?"})
    reply = "".join(e.get("text", "") for e in events if e.get("type") == "token")
    check("headlight" in reply.lower(), "run %d: chat should explain the B part" % n)
    check(any(e.get("type") == "done" for e in events), "run %d: chat stream never finished" % n)

    print("run %d/%d: PASS (A=%s B=%s)" % (n, RUNS, totals["A"]["high"], totals["B"]["high"]))


def main():
    for n in range(1, RUNS + 1):
        one_run(n)
    print("ALL %d RUNS PASSED" % RUNS)


if __name__ == "__main__":
    main()
