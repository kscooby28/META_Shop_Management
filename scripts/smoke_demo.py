"""End-to-end demo smoke: runs the whole flow N times against a live server.

Usage:  python scripts/smoke_demo.py [base_url] [runs]
Default: http://127.0.0.1:8765, 10 runs.

Each yard run: session → intake (demo) → harvest → comps → verdicts →
listing draft → approve → mock post → chat. Each bay run: session → bay
intake (demo case 1) → plan → pass → fail → parts → labor → kb, plus an
N63 no-start decline that must get no plan. Exits nonzero on the first
failure so "10 out of 10" is a real claim. Inventory runs cover the demo
seed, comps hit/miss/no-data, demo photo paths, and a sell-second listing
draft through approve into the mock outbox. Each spine run walks the video
journey in order on the server-reachable beats: seed → look-for data →
comps → listing gate → bay case → re-rank → close → decline. First-run
setup, registration taps, and totals math live in the browser by design;
tests/spine_driver.js covers those beats in the same order.
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


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as res:
        return res.status, json.loads(res.read().decode("utf-8"))


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
    diff_inputs = next(v["inputs"] for v in verdicts["report"]["verdicts"] if v["part_id"] == "p_diff")
    check(diff_inputs["money_grade"] == "A", "run %d: diff money grade off" % n)
    check(diff_inputs["sold_count"] == 5, "run %d: diff sold count off" % n)
    check(diff_inputs["reliable"], "run %d: diff must be reliable" % n)
    check("sure money" in totals["A"]["plain_words"], "run %d: A must say sure money" % n)
    check("maybe money" in totals["B"]["plain_words"], "run %d: B must say maybe money" % n)

    _, compare = post("/api/compare", {"sessionId": sid})
    check(len(compare["rows"]) == 7, "run %d: compare must cover 7 parts" % n)
    check(compare["mode13"] == "demo-cache", "run %d: spark 1.3 side must be demo" % n)
    check(compare["modeOpen"] in ("live", "demo-cache"), "run %d: open side unlabeled" % n)
    check(all(r["rule"] for r in compare["rows"]), "run %d: rule grades must pass through" % n)

    _, wonder = post("/api/wonder", {"sessionId": sid, "kind": "yard", "ref": "p_headlight"})
    check(wonder["escalated"], "run %d: borderline B must escalate" % n)
    check("headlight" in wonder["opinion"]["title"].lower(), "run %d: opinion title off" % n)
    check("demo-cache" in wonder["opinion"]["source"], "run %d: opinion must be demo-sourced" % n)

    _, listing = post("/api/listing", {"sessionId": sid, "partId": "p_diff"})
    draft_id = listing["draftId"]
    check("differential" in listing["draft"]["title"].lower(), "run %d: draft title off" % n)
    check(listing["cutout"]["box"], "run %d: cutout box missing" % n)
    check((listing["studio"] or {}).get("body", "").startswith("<svg"),
          "run %d: studio photo missing" % n)
    check("demo-cache" in (listing["studio"] or {}).get("source", ""),
          "run %d: studio must be demo-sourced" % n)

    status, _ = post("/api/listing/post", {"sessionId": sid, "draftId": draft_id})
    check(status == 400, "run %d: post-before-approve must be refused" % n)

    post("/api/listing/approve", {"sessionId": sid, "draftId": draft_id, "destinations": ["ebay"]})
    _, posted = post("/api/listing/post", {"sessionId": sid, "draftId": draft_id})
    check(posted["receipt"]["adapter"] == "mock-outbox", "run %d: mock receipt missing" % n)

    events = post_sse("/api/chat", {"sessionId": sid, "message": "Why is this part a B?"})
    reply = "".join(e.get("text", "") for e in events if e.get("type") == "token")
    check("headlight" in reply.lower(), "run %d: chat should explain the B part" % n)
    check(any(e.get("type") == "done" for e in events), "run %d: chat stream never finished" % n)
    demo_events = post_sse("/api/chat", {"sessionId": sid, "message": "Why is this part a B?", "demo": True})
    demo_modes = [e.get("mode") for e in demo_events if e.get("type") == "done"]
    check(demo_modes == ["demo-cache"], "run %d: forced demo chat must stay local" % n)

    print("run %d/%d: PASS (A=%s B=%s)" % (n, RUNS, totals["A"]["high"], totals["B"]["high"]))


def bay_run(n):
    _, session = post("/api/session", {})
    sid = session["sessionId"]

    _, intake = post("/api/bay/intake", {"sessionId": sid, "demoCase": "case1"})
    check(intake["mode"] == "demo-cache", "bay %d: intake not cached" % n)
    check(not intake["case"]["declined"], "bay %d: case1 must not decline" % n)
    check("BMW" in intake["case"]["vehicle"]["category"], "bay %d: category off" % n)
    check(intake["case"]["vehicle"]["trim"] == "unknown", "bay %d: trim must stay unknown" % n)

    _, plan = post("/api/bay/plan", {"sessionId": sid})
    order = [t["id"] for t in plan["plan"]["tests"]]
    check(order == ["t1", "t2", "t4", "t3", "t5"], "bay %d: ranking wrong: %s" % (n, order))
    check(plan["plan"]["tests"][0]["score"] == 9, "bay %d: top score wrong" % n)

    _, passed = post(
        "/api/bay/result", {"sessionId": sid, "testId": "t1", "result": "pass", "note": "12.1V"}
    )
    check("no power to module" in passed["plan"]["eliminated"], "bay %d: pass must rule out" % n)
    check(len(passed["plan"]["trail"]) == 1, "bay %d: trail must name the change" % n)

    _, failed = post("/api/bay/result", {"sessionId": sid, "testId": "t4", "result": "fail"})
    check("dead module" in failed["plan"]["suspected"], "bay %d: fail must suspect" % n)
    check(len(failed["plan"]["trail"]) == 2, "bay %d: trail must grow" % n)

    _, wonder = post("/api/wonder", {"sessionId": sid, "kind": "bay"})
    check(wonder["escalated"], "bay %d: split evidence must escalate" % n)
    check("one suspect standing" in " ".join(wonder["triggers"]), "bay %d: triggers off" % n)

    _, parts = post("/api/bay/parts", {"sessionId": sid})
    check(len(parts["parts"]) == 1, "bay %d: case1 parts wrong" % n)
    check(parts["parts"][0]["source"], "bay %d: part needs a source" % n)

    _, labor = post("/api/bay/labor", {"sessionId": sid})
    check("$165" in labor["labor"]["plain_words"], "bay %d: labor math wrong" % n)
    check("donor set index" in labor["labor"]["plain_words"], "bay %d: missing time must be named" % n)

    _, vnote = post(
        "/api/voice/note",
        {"sessionId": sid, "target": {"kind": "bay"}, "audio": None},
    )
    check(vnote["text"], "bay %d: voice note empty" % n)
    check(vnote["pinned"], "bay %d: voice note must pin to the open case" % n)
    check("demo-cache" in vnote["mode"], "bay %d: voice must be demo-sourced" % n)

    _, kb = get("/api/bay/kb?q=creep")
    check(len(kb["notes"]) == 1, "bay %d: kb search off" % n)

    # VIN live read is off: a plate photo must not trigger any API call,
    # and the case still opens from manual entry.
    _, vinoff = post(
        "/api/bay/intake",
        {
            "sessionId": sid,
            "manual": {
                "vehicle": {"year": 2011, "make": "BMW", "model": "328i"},
                "area": "electrical",
                "service_requested": "diagnose",
                "symptom": "intermittent no-crank",
                "codes": [],
            },
            "vinPhoto": {"name": "plate.png", "data": "data:image/png;base64,iVBORw0KGgo="},
        },
    )
    check(not vinoff["case"]["declined"], "bay %d: manual case must open" % n)
    check("key rotation" in vinoff["notice"], "bay %d: must say live read is off" % n)

    # Forced-demo plan on a manual case: empty hand-entry plan, no API call.
    _, manplan = post("/api/bay/plan", {"sessionId": sid, "demo": True})
    check(manplan["mode"] == "manual", "bay %d: forced demo must go manual" % n)
    check(manplan["plan"]["tests"] == [], "bay %d: forced demo starts empty" % n)

    # Decline path: N63 no-start never gets a plan.
    _, session2 = post("/api/session", {})
    sid2 = session2["sessionId"]
    _, declined = post(
        "/api/bay/intake",
        {
            "sessionId": sid2,
            "manual": {
                "vehicle": {"year": 2013, "make": "BMW", "model": "750i", "engine": "N63"},
                "area": "electrical",
                "service_requested": "diagnose",
                "symptom": "crank no start, nothing happens",
                "codes": [],
            },
        },
    )
    check(declined["case"]["declined"], "bay %d: N63 no-start must decline" % n)
    check(declined["case"]["decline"]["next_step"], "bay %d: decline needs a next step" % n)
    status, _ = post("/api/bay/plan", {"sessionId": sid2})
    check(status == 400, "bay %d: declined case must get no plan" % n)

    print("bay %d/%d: PASS" % (n, RUNS))


def inv_run(n):
    _, seed = get("/api/inv/seed")
    check(len(seed["seed"]["cars"]) == 4, "inv %d: seed must carry 4 cars" % n)
    check(len(seed["seed"]["parts"]) == 6, "inv %d: seed must carry 6 parts" % n)

    _, hit = post("/api/inv/comps", {"label": "engine computer", "demo": True})
    check(hit["comp"]["value"] == 200, "inv %d: demo comp must hit" % n)
    _, miss = post("/api/inv/comps", {"label": "trunk lid", "demo": True})
    check(miss["comp"]["value"] is None, "inv %d: demo miss must be no-data" % n)
    _, live = post("/api/inv/comps", {"label": "engine computer", "demo": False})
    check(live["comp"]["value"] is None, "inv %d: live must be no-data" % n)

    tiny = "data:image/png;base64,iVBORw0KGgo="
    _, ident = post("/api/inv/identify", {"photo": {"name": "t.png", "data": tiny}, "demo": True})
    check(ident["car"]["trim"] == "unknown", "inv %d: demo identify must stay honest" % n)
    _, vin = post("/api/inv/vin", {"photo": {"name": "t.png", "data": tiny}, "demo": True})
    check("vin" not in vin["vehicle"], "inv %d: demo vin must store nothing" % n)
    _, part = post("/api/inv/part-photo", {"photo": {"name": "t.png", "data": tiny}, "demo": True})
    check("demo sample" in part["part"]["label"], "inv %d: demo part must be tagged" % n)
    _, vnote = post("/api/voice/note", {"target": {"kind": "inv"}, "audio": None})
    check(vnote["text"], "inv %d: voice note empty" % n)
    check(not vnote["pinned"], "inv %d: inventory note pins in the browser, not the server" % n)

    _, session = post("/api/session", {})
    sid = session["sessionId"]
    _, listing = post(
        "/api/listing",
        {
            "sessionId": sid,
            "demo": True,
            "invPart": {"id": "ip-ecu", "label": "engine computer",
                        "condition": "used, untested", "value": 200,
                        "valueSource": "demo-sample: owner note"},
            "invCar": {"year": 1995, "make": "BMW", "model": "M3"},
        },
    )
    check("engine computer" in listing["draft"]["title"].lower(), "inv %d: draft title off" % n)
    check(listing["studio"] is None, "inv %d: photo-less draft must fall back" % n)
    post("/api/listing/approve", {"sessionId": sid, "draftId": listing["draftId"]})
    _, posted = post("/api/listing/post", {"sessionId": sid, "draftId": listing["draftId"]})
    check(posted["receipt"]["adapter"] == "mock-outbox", "inv %d: mock receipt missing" % n)
    print("inv %d/%d: PASS" % (n, RUNS))


def spine_run(n):
    tag = "spine %d" % n
    _, session = post("/api/session", {})
    sid = session["sessionId"]

    # Enthusiast home: seed cars, and the M3 look-for note behind them.
    _, seed = get("/api/inv/seed")
    cars = seed["seed"]["cars"]
    check(any("M3" in c.get("label", "") for c in cars), tag + ": M3 seed car missing")
    notes = seed["seed"]["knowledge"]
    check(len(notes) == 1 and notes[0]["value"] == 200, tag + ": engine-computer note off")
    check("EWS" in notes[0]["reason"], tag + ": note must say why, no EWS")

    # Plain-money comps behind the totals, then the listing gate.
    _, hit = post("/api/inv/comps", {"label": "engine computer", "demo": True})
    check(hit["comp"]["value"] == 200, tag + ": comp must price the note")
    _, listing = post(
        "/api/listing",
        {
            "sessionId": sid,
            "demo": True,
            "invPart": {"id": "ip-ecu", "label": "engine computer",
                        "condition": "used, untested", "value": 200,
                        "valueSource": "demo-sample: owner note"},
            "invCar": {"year": 1995, "make": "BMW", "model": "M3"},
        },
    )
    draft_id = listing["draftId"]
    status, _ = post("/api/listing/post", {"sessionId": sid, "draftId": draft_id})
    check(status == 400, tag + ": gate must block pre-approve post")
    post("/api/listing/approve", {"sessionId": sid, "draftId": draft_id})
    _, posted = post("/api/listing/post", {"sessionId": sid, "draftId": draft_id})
    check(posted["receipt"]["adapter"] == "mock-outbox", tag + ": mock receipt missing")

    # Shop home: case in, plan out, pass and fail re-rank it live.
    _, intake = post("/api/bay/intake", {"sessionId": sid, "demoCase": "case1"})
    check(not intake["case"]["declined"], tag + ": case1 must open")
    _, plan = post("/api/bay/plan", {"sessionId": sid})
    order = [t["id"] for t in plan["plan"]["tests"]]
    check(order == ["t1", "t2", "t4", "t3", "t5"], tag + ": ranking wrong")
    _, passed = post(
        "/api/bay/result", {"sessionId": sid, "testId": "t1", "result": "pass", "note": "12.1V"}
    )
    check(len(passed["plan"]["trail"]) == 1, tag + ": pass must trail")
    _, failed = post("/api/bay/result", {"sessionId": sid, "testId": "t4", "result": "fail"})
    check(bool(failed["plan"]["trail"][-1]["moved"]), tag + ": fail must move ranks")

    # Close: every test recorded, the plan is complete.
    for tid in ("t2", "t3", "t5"):
        post("/api/bay/result", {"sessionId": sid, "testId": tid, "result": "pass"})
    _, labor = post("/api/bay/labor", {"sessionId": sid})
    check("$" in labor["labor"]["plain_words"], tag + ": close needs plain labor")

    # Decline beat: professional verdict, next step, no plan.
    _, session2 = post("/api/session", {})
    sid2 = session2["sessionId"]
    _, declined = post(
        "/api/bay/intake",
        {
            "sessionId": sid2,
            "manual": {
                "vehicle": {"year": 2013, "make": "BMW", "model": "750i", "engine": "N63"},
                "area": "electrical",
                "service_requested": "diagnose",
                "symptom": "crank no start, nothing happens",
                "codes": [],
            },
        },
    )
    check(declined["case"]["declined"], tag + ": N63 no-start must decline")
    check(declined["case"]["decline"]["next_step"], tag + ": decline needs a next step")
    print("spine %d/%d: PASS" % (n, RUNS))


def main():
    for n in range(1, RUNS + 1):
        one_run(n)
    for n in range(1, RUNS + 1):
        bay_run(n)
    for n in range(1, RUNS + 1):
        inv_run(n)
    for n in range(1, RUNS + 1):
        spine_run(n)
    print("ALL %d YARD + %d BAY + %d INV + %d SPINE RUNS PASSED" % (RUNS, RUNS, RUNS, RUNS))


if __name__ == "__main__":
    main()
