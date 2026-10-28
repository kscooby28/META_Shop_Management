"""Shop AI Copilot backend: intake, harvest map, verdicts, plain-money totals.

Standard library only. Serves the single web page in ``web/`` and a small
JSON API. Every AI step tries the Meta Model API first and falls back to the
local demo cache so the flow runs end to end even when the API is unreachable.
"""

import json
import os
import re
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from bay import (
    build_case,
    categorize,
    edit_plan,
    labor_math,
    load_bay_case,
    load_kb,
    new_plan,
    normalize_part,
    ranked_tests,
    record_result,
    search_kb,
    strip_vin,
    validate_intake,
    VIN_LIVE,
)
from comps import get_adapter as get_comps_adapter
from demo_cache import StepCache
from inventory import comp_for_label, load_seed
from listing import build_live_draft, demo_draft, get_post_adapter
from meta_client import (
    MetaAPIError,
    chat_stream,
    describe_part,
    draft_plan,
    identify_car,
    read_vin_photo,
    segment_parts,
)
from verdict import evaluate, load_rules, render_decline, save_rules

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(ROOT, "web")
RULES_PATH = os.path.join(ROOT, "rules.json")
MAX_BODY_BYTES = 15 * 1024 * 1024

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}

_sessions = {}
_sessions_lock = threading.Lock()


def new_session_id():
    return "s-%d-%d" % (int(time.time() * 1000), os.getpid())


def get_session(session_id):
    with _sessions_lock:
        return _sessions.get(session_id)


def put_session(session_id, data):
    with _sessions_lock:
        _sessions[session_id] = data


class Handler(BaseHTTPRequestHandler):
    server_version = "ShopCopilot/0.1"

    def log_message(self, *args):  # keep test output clean
        pass

    # -- helpers ---------------------------------------------------------
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _serve_static(self, path):
        rel = urllib.parse.unquote(path.split("?", 1)[0].lstrip("/"))
        if not rel or rel == "index.html":
            rel = "index.html"
        full = os.path.realpath(os.path.join(WEB_DIR, rel))
        if not full.startswith(os.path.realpath(WEB_DIR) + os.sep) and full != os.path.join(
            os.path.realpath(WEB_DIR), "index.html"
        ):
            self.send_error(403)
            return
        if not os.path.isfile(full):
            self.send_error(404)
            return
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- routes ----------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            from meta_client import api_key_present, settings

            self._send_json(
                {
                    "ok": True,
                    "api_base": settings()["api_base"],
                    "api_key_present": api_key_present(),
                    "spark_model": settings()["spark_model"],
                    "sam_model": settings()["sam_model"],
                }
            )
        elif parsed.path == "/api/rules":
            self._send_json({"ok": True, "rules": load_rules(RULES_PATH)})
        elif parsed.path == "/api/bay/kb":
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
            self._send_json({"ok": True, "notes": search_kb(ROOT, query)})
        elif parsed.path == "/api/inv/seed":
            try:
                seed = load_seed(ROOT)
            except (OSError, ValueError):
                self._send_json({"ok": False, "error": "demo seed missing"}, status=500)
                return
            self._send_json({"ok": True, "seed": seed})
        else:
            self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            payload = self._read_json()
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=413)
            return
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "invalid JSON body"}, status=400)
            return
        if parsed.path == "/api/session":
            self._api_session(payload)
        elif parsed.path == "/api/intake":
            self._api_intake(payload)
        elif parsed.path == "/api/harvest":
            self._api_harvest(payload)
        elif parsed.path == "/api/comps":
            self._api_comps(payload)
        elif parsed.path == "/api/verdicts":
            self._api_verdicts(payload)
        elif parsed.path == "/api/listing":
            self._api_listing(payload)
        elif parsed.path == "/api/listing/approve":
            self._api_listing_approve(payload)
        elif parsed.path == "/api/listing/post":
            self._api_listing_post(payload)
        elif parsed.path == "/api/chat":
            self._api_chat(payload)
        elif parsed.path == "/api/bay/intake":
            self._api_bay_intake(payload)
        elif parsed.path == "/api/bay/plan":
            self._api_bay_plan(payload)
        elif parsed.path == "/api/bay/result":
            self._api_bay_result(payload)
        elif parsed.path == "/api/bay/plan/edit":
            self._api_bay_plan_edit(payload)
        elif parsed.path == "/api/bay/parts":
            self._api_bay_parts(payload)
        elif parsed.path == "/api/bay/labor":
            self._api_bay_labor(payload)
        elif parsed.path == "/api/inv/identify":
            self._api_inv_identify(payload)
        elif parsed.path == "/api/inv/vin":
            self._api_inv_vin(payload)
        elif parsed.path == "/api/inv/part-photo":
            self._api_inv_part_photo(payload)
        elif parsed.path == "/api/inv/comps":
            self._api_inv_comps(payload)
        else:
            self._send_json({"ok": False, "error": "unknown endpoint"}, status=404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/rules":
            self._send_json({"ok": False, "error": "unknown endpoint"}, status=404)
            return
        try:
            payload = self._read_json()
        except (ValueError, json.JSONDecodeError):
            self._send_json({"ok": False, "error": "invalid JSON body"}, status=400)
            return
        try:
            rules = save_rules(RULES_PATH, payload.get("rules"))
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        self._send_json({"ok": True, "rules": rules})

    # -- api -------------------------------------------------------------
    def _api_session(self, payload):
        session_id = new_session_id()
        put_session(session_id, {"created": time.time()})
        self._send_json({"ok": True, "sessionId": session_id})

    def _api_intake(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        if session is None:
            session_id = new_session_id()
            session = {"created": time.time()}
        images = payload.get("images") or []
        if not images:
            self._send_json({"ok": False, "error": "upload at least one photo first"}, status=400)
            return
        demo_only = bool(payload.get("demo"))
        cache = StepCache(ROOT)
        mode = "live"
        notice = ""
        try:
            if demo_only:
                raise MetaAPIError("demo case requested", kind="demo")
            result = identify_car(images)
            cache.save_live(session_id, "intake", result)
        except MetaAPIError as exc:
            mode = "demo-cache"
            notice = cache.notice("intake", exc)
            result = cache.load_demo("intake")
        session["intake"] = result
        session["intake_mode"] = mode
        session["image_names"] = [img.get("name", "photo-%d" % i) for i, img in enumerate(images)]
        put_session(session_id, session)
        self._send_json(
            {"ok": True, "sessionId": session_id, "mode": mode, "notice": notice, "intake": result}
        )

    def _api_harvest(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        if session is None or "intake" not in session:
            self._send_json({"ok": False, "error": "run intake first"}, status=400)
            return
        demo_only = bool(payload.get("demo"))
        cached_intake = session["intake"]
        cache = StepCache(ROOT)
        mode = "live"
        notice = ""
        try:
            if demo_only or session.get("intake_mode") != "live":
                raise MetaAPIError("intake came from demo cache", kind="demo")
            images = payload.get("images") or []
            phrases = [p.get("label", "") for p in cached_intake.get("parts", [])]
            result = segment_parts(images, phrases, cached_intake)
            cache.save_live(session_id, "harvest", result)
        except MetaAPIError as exc:
            mode = "demo-cache"
            notice = cache.notice("harvest", exc)
            result = cache.load_demo("harvest")
        session["harvest"] = result
        session["harvest_mode"] = mode
        put_session(session_id, session)
        self._send_json(
            {"ok": True, "sessionId": session_id, "mode": mode, "notice": notice, "harvest": result}
        )

    def _api_comps(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        if session is None or "harvest" not in session:
            self._send_json({"ok": False, "error": "run harvest first"}, status=400)
            return
        parts = session["harvest"].get("parts", [])
        # Samples are allowed only when the harvest itself came from demo cache.
        allow_samples = session.get("harvest_mode") != "live"
        adapter = get_comps_adapter(ROOT)
        found = adapter.lookup([p.get("id") for p in parts], allow_samples)
        session["comps"] = found
        session["comps_mode"] = "demo-cache" if allow_samples else "live-adapter"
        put_session(session_id, session)
        notice = ""
        if allow_samples:
            notice = "Demo case: sample comps from the Yard Case 4 board, not live sold listings."
        else:
            notice = "No real sold-data adapter is connected yet, so parts without shop comps have no reliable price."
        self._send_json(
            {
                "ok": True,
                "sessionId": session_id,
                "mode": session["comps_mode"],
                "adapter": adapter.name,
                "notice": notice,
                "comps": found,
            }
        )

    def _merged_inputs(self, session, part_inputs):
        merged = {}
        comps = session.get("comps") or {}
        for part in session.get("harvest", {}).get("parts", []):
            pid = part.get("id")
            entry = dict(comps.get(pid) or {})
            entry.update(part_inputs.get(pid) or {})  # shop-typed comps win
            merged[pid] = entry
        return merged

    def _api_verdicts(self, payload):
        if payload.get("declineCode"):
            try:
                card = render_decline(payload.get("declineCode"))
            except KeyError:
                self._send_json({"ok": False, "error": "unknown decline code"}, status=400)
                return
            self._send_json({"ok": True, "decline": card})
            return
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        if session is None or "harvest" not in session:
            self._send_json({"ok": False, "error": "run harvest first"}, status=400)
            return
        part_inputs = self._merged_inputs(session, payload.get("partInputs") or {})
        session["shop_inputs"] = payload.get("partInputs") or {}
        parts = session["harvest"].get("parts", [])
        rules = load_rules(RULES_PATH)
        report = evaluate(parts, rules, part_inputs)
        report["modes"] = {
            "intake": session.get("intake_mode", "unknown"),
            "harvest": session.get("harvest_mode", "unknown"),
            "comps": session.get("comps_mode", "unknown"),
        }
        session["verdicts"] = report
        put_session(session_id, session)
        self._send_json({"ok": True, "sessionId": session_id, "report": report})

    def _api_listing(self, payload):
        inv = payload.get("invPart")
        if inv is not None:
            # Sell second: an inventory item feeds a draft. No harvest needed.
            session_id, session = self._bay_session(payload)
            part_id = inv.get("id") or "inv-part"
            part = {
                "id": part_id,
                "label": inv.get("label") or "part",
                "intact": "unknown",
                "intact_note": inv.get("condition") or "",
                "sightings": [],
            }
            comp = {
                "price_low": inv.get("value"),
                "price_high": inv.get("value"),
                "price_source": inv.get("valueSource") or "",
            }
            verdict_info = None
            car = payload.get("invCar") or {}
            force_demo = bool(payload.get("demo"))
        else:
            session_id = payload.get("sessionId")
            session = get_session(session_id) if session_id else None
            if session is None or "harvest" not in session:
                self._send_json({"ok": False, "error": "run harvest first"}, status=400)
                return
            part_id = payload.get("partId")
            part = next(
                (p for p in session["harvest"].get("parts", []) if p.get("id") == part_id), None
            )
            if part is None:
                self._send_json({"ok": False, "error": "unknown part"}, status=400)
                return
            comp = (session.get("comps") or {}).get(part_id, {})
            verdict_info = next(
                (v for v in session.get("verdicts", {}).get("verdicts", []) if v.get("part_id") == part_id),
                None,
            )
            car = session.get("harvest", {}).get("car", {})
            force_demo = False
        mode = "live"
        notice = ""
        try:
            if force_demo or session.get("harvest_mode") != "live":
                raise MetaAPIError("harvest came from demo cache", kind="demo")
            draft = build_live_draft(part, comp, verdict_info, car)
            StepCache(ROOT).save_live(session_id, "listing-%s" % part_id, draft)
        except MetaAPIError as exc:
            mode = "demo-cache"
            notice = StepCache(ROOT).notice("listing", exc)
            draft = demo_draft(part, comp, verdict_info, car)
        draft_id = "d-%d" % int(time.time() * 1000)
        drafts = session.setdefault("drafts", {})
        drafts[draft_id] = {
            "part_id": part_id,
            "title": draft.get("title", ""),
            "description": draft.get("description", ""),
            "condition": draft.get("condition", ""),
            "price_hint": draft.get("price_hint"),
            "price_source": draft.get("price_source", ""),
            "source": draft.get("source", mode),
            "status": "draft",
            "destinations": [],
        }
        put_session(session_id, session)
        self._send_json(
            {
                "ok": True,
                "sessionId": session_id,
                "mode": mode,
                "notice": notice,
                "draftId": draft_id,
                "draft": drafts[draft_id],
                "cutout": self._cutout_spec(part),
            }
        )

    def _cutout_spec(self, part):
        sightings = part.get("sightings") or []
        best = max(sightings, key=lambda s: (s.get("score") or 0)) if sightings else {}
        return {
            "frame": best.get("frame", ""),
            "box": best.get("box"),
            "source_tag": best.get("source_tag", ""),
            "note": "Cutout preview crops this box from the source frame. Studio background is a later step.",
        }

    def _api_listing_approve(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        drafts = (session or {}).get("drafts") or {}
        draft = drafts.get(payload.get("draftId"))
        if draft is None:
            self._send_json({"ok": False, "error": "draft not found; draft one first"}, status=400)
            return
        # Edit path: the human's text wins.
        if payload.get("title") is not None:
            draft["title"] = payload.get("title")
        if payload.get("description") is not None:
            draft["description"] = payload.get("description")
        destinations = payload.get("destinations") or []
        draft["destinations"] = [d for d in destinations if d in ("ebay", "exchange")]
        draft["status"] = "approved"
        put_session(session_id, session)
        self._send_json({"ok": True, "sessionId": session_id, "draft": draft})

    def _api_listing_post(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        drafts = (session or {}).get("drafts") or {}
        draft = drafts.get(payload.get("draftId"))
        if draft is None:
            self._send_json({"ok": False, "error": "draft not found; draft one first"}, status=400)
            return
        if draft.get("status") != "approved":
            self._send_json(
                {"ok": False, "error": "press Approve first: nothing posts without approval"}, status=400
            )
            return
        receipt = get_post_adapter(ROOT).post(session_id, draft, draft.get("destinations") or [])
        draft["status"] = "posted-mock"
        draft["receipt"] = receipt
        put_session(session_id, session)
        self._send_json({"ok": True, "sessionId": session_id, "draft": draft, "receipt": receipt})

    # -- bay -------------------------------------------------------------
    def _bay_session(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        if session is None:
            session_id = new_session_id()
            session = {"created": time.time()}
            put_session(session_id, session)
        return session_id, session

    def _api_bay_intake(self, payload):
        session_id, session = self._bay_session(payload)
        demo_case = payload.get("demoCase")
        notices = []
        mode = "live"
        if demo_case in ("case1", "case2", "case3"):
            try:
                manual = load_bay_case("intake", demo_case, ROOT)
            except (OSError, ValueError):
                self._send_json({"ok": False, "error": "demo case missing"}, status=500)
                return
            mode = "demo-cache"
            notices.append("Demo case: anonymized Bay sample, no customer data, no VIN.")
        else:
            manual = payload.get("manual") or {}
            problems = validate_intake(manual)
            if problems:
                self._send_json(
                    {"ok": False, "error": "case needs work: " + "; ".join(problems)}, status=400
                )
                return
            vin_photo = payload.get("vinPhoto")
            if vin_photo:
                if not VIN_LIVE:
                    notices.append(
                        "VIN live read is off until the key rotation, "
                        "so the case uses manual entry only."
                    )
                    vin_photo = None
            if vin_photo:
                try:
                    read = read_vin_photo(vin_photo)
                    vehicle = manual.setdefault("vehicle", {})
                    for field in ("year", "make", "model", "trim", "engine"):
                        if not (vehicle.get(field) or "") and read.get(field) not in (None, "", "unknown"):
                            vehicle[field] = read[field]
                    tags = vehicle.setdefault("source_tags", ["manual-entry"])
                    if "vin-photo" not in tags:
                        tags.append("vin-photo")
                    session_vin = read.get("vin")
                    if session_vin and session_vin != "unknown":
                        session.setdefault("bay_vin", session_vin)  # memory only, never disk
                except MetaAPIError:
                    mode = "demo-cache"
                    notices.append("Could not read the VIN plate, so the case uses manual entry only.")
        vehicle = manual.get("vehicle", manual)
        intake = {
            "symptom": manual.get("symptom", ""),
            "codes": manual.get("codes") or [],
            "observations": manual.get("observations") or [],
            "area": manual.get("area", "not sure"),
            "service_requested": manual.get("service_requested", ""),
            "engine": (vehicle.get("engine") if isinstance(vehicle, dict) else manual.get("engine")) or "",
        }
        case_id = "b-%d" % int(time.time() * 1000)
        case = build_case(case_id, vehicle if isinstance(vehicle, dict) else {}, intake)
        if not case["declined"]:
            case["stakes"] = manual.get("stakes", "")
            case["stakes_source"] = manual.get("stakes_source", "")
        else:
            notices.append("Shop policy declines this job, so there is no test plan.")
        bay = session.setdefault("bay", {})
        bay["case"] = case
        bay["plan"] = None
        bay["added_parts"] = []
        bay["standards"] = {}
        bay["demo_case"] = demo_case if demo_case in ("case1", "case2", "case3") else None
        bay["modes"] = {"intake": mode}
        put_session(session_id, session)
        StepCache(ROOT).save_live(session_id, "bay-intake-%s" % case_id, strip_vin(case))
        self._send_json(
            {
                "ok": True,
                "sessionId": session_id,
                "mode": mode,
                "notice": " ".join(notices),
                "case": case,
            }
        )

    def _bay_plan_view(self, plan):
        return {
            "tests": ranked_tests(plan),
            "results": plan["results"],
            "notes": plan["notes"],
            "eliminated": plan["eliminated"],
            "suspected": plan["suspected"],
            "trail": plan["trail"],
        }

    def _api_bay_plan(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        bay = (session or {}).get("bay") or {}
        case = bay.get("case")
        if case is None:
            self._send_json({"ok": False, "error": "create a bay case first"}, status=400)
            return
        if case.get("declined"):
            self._send_json({"ok": False, "error": "case declined: no test plan"}, status=400)
            return
        if payload.get("demo") and not bay.get("demo_case"):
            bay["plan"] = new_plan(case, [])
            bay["modes"]["plan"] = "manual"
            put_session(session_id, session)
            self._send_json(
                {
                    "ok": True,
                    "sessionId": session_id,
                    "mode": "manual",
                    "notice": "Offline demo: add the tests by hand below; the ranking still works.",
                    "plan": self._bay_plan_view(bay["plan"]),
                }
            )
            return
        mode = "live"
        notice = ""
        raw_tests = None
        if bay.get("demo_case"):
            try:
                raw_tests = load_bay_case("plan", bay["demo_case"], ROOT)["tests"]
                mode = "demo-cache"
                notice = "Demo case: sample plan from the Bay cache."
            except (OSError, ValueError, KeyError):
                raw_tests = None
        if raw_tests is None and not bay.get("demo_case"):
            try:
                raw_tests = draft_plan(case)
                StepCache(ROOT).save_live(session_id, "bay-plan-%s" % case["case_id"], strip_vin(raw_tests))
            except MetaAPIError as exc:
                mode = "manual"
                notice = (
                    StepCache(ROOT).notice("plan", exc)
                    + " Add the tests by hand below; the ranking still works."
                )
        if raw_tests is None and bay.get("demo_case"):
            self._send_json({"ok": False, "error": "demo plan missing"}, status=500)
            return
        if raw_tests is not None:
            bay["plan"] = new_plan(case, raw_tests)
        else:
            bay["plan"] = new_plan(case, [])
        bay["modes"]["plan"] = mode
        put_session(session_id, session)
        self._send_json(
            {
                "ok": True,
                "sessionId": session_id,
                "mode": mode,
                "notice": notice,
                "plan": self._bay_plan_view(bay["plan"]),
            }
        )

    def _api_bay_result(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        bay = (session or {}).get("bay") or {}
        plan = bay.get("plan")
        if plan is None:
            self._send_json({"ok": False, "error": "draft a plan first"}, status=400)
            return
        try:
            record_result(plan, payload.get("testId"), payload.get("result"), payload.get("note", ""))
        except KeyError:
            self._send_json({"ok": False, "error": "unknown test"}, status=400)
            return
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        put_session(session_id, session)
        self._send_json({"ok": True, "sessionId": session_id, "plan": self._bay_plan_view(plan)})

    def _api_bay_plan_edit(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        bay = (session or {}).get("bay") or {}
        plan = bay.get("plan")
        if plan is None:
            self._send_json({"ok": False, "error": "draft a plan first"}, status=400)
            return
        try:
            edit_plan(plan, payload.get("tests"), payload.get("order"))
        except (ValueError, TypeError) as exc:
            self._send_json({"ok": False, "error": "bad plan edit: %s" % exc}, status=400)
            return
        put_session(session_id, session)
        self._send_json({"ok": True, "sessionId": session_id, "plan": self._bay_plan_view(plan)})

    def _api_bay_parts(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        bay = (session or {}).get("bay") or {}
        if not bay.get("case"):
            self._send_json({"ok": False, "error": "create a bay case first"}, status=400)
            return
        base = []
        note = ""
        if bay.get("demo_case"):
            try:
                cached = load_bay_case("parts", bay["demo_case"], ROOT)
                base = cached.get("parts", [])
                note = cached.get("note", "")
            except (OSError, ValueError):
                pass
        added = payload.get("add")
        if isinstance(added, dict):
            part = normalize_part(added)
            if part is None:
                self._send_json({"ok": False, "error": "name the part"}, status=400)
                return
            if not part["source"]:
                part["source"] = "shop-entered"
            bay.setdefault("added_parts", []).append(part)
            put_session(session_id, session)
        self._send_json(
            {
                "ok": True,
                "sessionId": session_id,
                "parts": base + bay.get("added_parts", []),
                "note": note,
            }
        )

    def _api_bay_labor(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        bay = (session or {}).get("bay") or {}
        plan = bay.get("plan")
        if plan is None:
            self._send_json({"ok": False, "error": "draft a plan first"}, status=400)
            return
        standards = bay.setdefault("standards", {})
        for test_id, entry in (payload.get("standards") or {}).items():
            if not isinstance(entry, dict):
                continue
            try:
                minutes = float(entry.get("minutes")) if entry.get("minutes") not in (None, "") else None
            except (TypeError, ValueError):
                continue
            if minutes is None:
                standards.pop(test_id, None)
            else:
                standards[test_id] = {
                    "minutes": minutes,
                    "source": entry.get("source") or "shop-set estimate",
                }
        put_session(session_id, session)
        self._send_json({"ok": True, "sessionId": session_id, "labor": labor_math(plan, standards)})

    # -- inventory -------------------------------------------------------
    def _api_inv_identify(self, payload):
        if payload.get("demo"):
            return self._send_json(
                {
                    "ok": True,
                    "mode": "demo-cache",
                    "notice": "Demo sample identification.",
                    "car": load_seed(ROOT)["sampleIdentify"],
                }
            )
        photo = payload.get("photo")
        if not photo:
            self._send_json({"ok": False, "error": "attach a photo first"}, status=400)
            return
        try:
            found = identify_car([photo])
        except MetaAPIError:
            self._send_json(
                {"ok": False, "error": "could not identify the car offline; enter it by hand"},
                status=400,
            )
            return
        self._send_json({"ok": True, "mode": "live", "notice": "", "car": found["car"]})

    def _api_inv_vin(self, payload):
        if payload.get("demo") or not VIN_LIVE:
            notice = "Demo sample vehicle; no VIN stored."
            if payload.get("photo") and not VIN_LIVE and not payload.get("demo"):
                notice = (
                    "VIN live read is off until the key rotation, "
                    "so this is the demo sample. Confirm or edit by hand."
                )
            return self._send_json(
                {
                    "ok": True,
                    "mode": "demo-cache",
                    "notice": notice,
                    "vehicle": load_seed(ROOT)["sampleVin"],
                }
            )
        photo = payload.get("photo")
        if not photo:
            self._send_json({"ok": False, "error": "attach a VIN photo first"}, status=400)
            return
        try:
            read = read_vin_photo(photo)
        except MetaAPIError:
            self._send_json(
                {"ok": False, "error": "could not read the plate offline; enter it by hand"},
                status=400,
            )
            return
        read.pop("vin", None)  # identification only; the VIN itself is not kept
        self._send_json({"ok": True, "mode": "live", "notice": "", "vehicle": read})

    def _api_inv_part_photo(self, payload):
        if payload.get("demo"):
            return self._send_json(
                {
                    "ok": True,
                    "mode": "demo-cache",
                    "notice": "Demo sample description; enter the real condition by hand.",
                    "part": load_seed(ROOT)["samplePart"],
                }
            )
        photo = payload.get("photo")
        if not photo:
            self._send_json({"ok": False, "error": "attach a part photo first"}, status=400)
            return
        try:
            part = describe_part(photo)
        except MetaAPIError:
            self._send_json(
                {"ok": False, "error": "could not describe the part offline; enter it by hand"},
                status=400,
            )
            return
        self._send_json({"ok": True, "mode": "live", "notice": "", "part": part})

    def _api_inv_comps(self, payload):
        label = payload.get("label") or ""
        try:
            seed = load_seed(ROOT)
        except (OSError, ValueError):
            seed = {}
        found = comp_for_label(seed, label, allow_samples=bool(payload.get("demo")))
        self._send_json(
            {
                "ok": True,
                "mode": "demo-cache" if payload.get("demo") else "live-adapter",
                "comp": found,
            }
        )

    # -- chat ------------------------------------------------------------
    def _case_summary(self, session):
        if not session or "harvest" not in session:
            return "No case yet. The user has not run intake."
        car = session["harvest"].get("car", {})
        lines = [
            "Car: %s %s %s, trim %s."
            % (car.get("year", "?"), car.get("make", "?"), car.get("model", "?"), car.get("trim", "?"))
        ]
        verdicts = (session.get("verdicts") or {}).get("verdicts", [])
        if verdicts:
            for v in verdicts:
                inputs = v.get("inputs", {})
                lines.append(
                    "Part %s: grade %s (%s) by rule '%s'. Inputs: intact=%s, frames=%s, demand=%s, price=%s."
                    % (
                        v.get("label"),
                        v.get("verdict"),
                        v.get("verdict_means"),
                        v.get("rule_name"),
                        inputs.get("intact"),
                        inputs.get("frames_seen"),
                        inputs.get("demand"),
                        inputs.get("price_high") if inputs.get("price_known") else "no reliable price",
                    )
                )
            totals = (session.get("verdicts") or {}).get("totals", {})
            for grade in ("A", "B"):
                if grade in totals:
                    lines.append("Total %s: %s" % (grade, totals[grade].get("plain_words")))
        else:
            parts = session["harvest"].get("parts", [])
            lines.append("Harvested %d parts, no verdicts yet." % len(parts))
        bay = (session or {}).get("bay") or {}
        case = bay.get("case")
        if case:
            if case.get("declined"):
                lines.append("Bay case %s declined: %s" % (case.get("case_id"), case["decline"]["title"]))
            else:
                vehicle = case.get("vehicle", {})
                lines.append(
                    "Bay case %s: %s, symptom: %s Codes: %s."
                    % (
                        case.get("case_id"),
                        vehicle.get("category", "?"),
                        case.get("symptom", "?"),
                        ", ".join(case.get("codes", [])) or "none",
                    )
                )
                plan = bay.get("plan")
                if plan:
                    pending = [t for t in ranked_tests(plan) if t.get("standing") == "pending"]
                    done = len(plan.get("results", {}))
                    lines.append(
                        "Plan: %d of %d tests recorded. Top next: %s."
                        % (
                            done,
                            len(plan.get("tests", [])),
                            pending[0]["title"] if pending else "none left",
                        )
                    )
                    if plan.get("trail"):
                        lines.append("Last change: %s" % plan["trail"][-1]["caused_by"])
        return "\n".join(lines)

    def _local_chat_answer(self, session, message):
        text = (message or "").lower()
        bay = (session or {}).get("bay") or {}
        want_bay = bay.get("case") and any(
            key in text for key in ("test", "plan", "case", "bay", "creep", "cylinder", "module", "rank")
        )
        if want_bay:
            return self._local_bay_answer(bay, text)
        if "identify" in text or "what car" in text or "what is this car" in text:
            if not session or "harvest" not in session:
                return "No car yet — upload photos or load the demo car, then press Identify."
            car = session["harvest"].get("car", {})
            return "This one reads as a %s %s %s. Trim: %s — %s" % (
                car.get("year", "?"),
                car.get("make", "?"),
                car.get("model", "?"),
                car.get("trim", "?"),
                car.get("trim_note", ""),
            )
        if "why" in text and ("b" in text or "grade" in text or "verdict" in text):
            verdicts = (session.get("verdicts") or {}).get("verdicts", []) if session else []
            if not verdicts:
                return "No verdicts yet — run the flow first, then ask me about any grade."
            b_parts = [v for v in verdicts if v.get("verdict") == "B"]
            if not b_parts:
                return "Nothing graded B in this run. The grades are: " + ", ".join(
                    "%s is %s" % (v.get("label"), v.get("verdict")) for v in verdicts
                )
            v = b_parts[0]
            inputs = v.get("inputs", {})
            return "The %s is B (%s) because of the rule '%s': %s Inputs: condition %s, seen in %s frame(s), demand %s, price %s." % (
                v.get("label"),
                v.get("verdict_means"),
                v.get("rule_name"),
                v.get("rule_explain"),
                inputs.get("intact"),
                inputs.get("frames_seen"),
                inputs.get("demand"),
                ("$%d" % inputs.get("price_high")) if inputs.get("price_known") else "no reliable price",
            )
        if "list" in text:
            if not session or "harvest" not in session:
                return "Run the flow first, then pick a part and press Draft listing."
            return "Pick a part in the listing card below and press Draft listing. You can edit it, then Approve, then Post — nothing posts without your approval."
        if session and "verdicts" in session:
            totals = session["verdicts"].get("totals", {})
            return "%s %s (Live AI is unreachable, so this answer comes from the case on file.)" % (
                totals.get("A", {}).get("plain_words", ""),
                totals.get("B", {}).get("plain_words", ""),
            )
        return "I can help with this case once it exists: upload photos or load the demo car and run the flow. (Live AI is unreachable, so I am answering from the case file only.)"

    def _local_bay_answer(self, bay, text):
        case = bay.get("case") or {}
        if case.get("declined"):
            return "This case is declined: %s %s" % (
                case["decline"]["title"],
                case["decline"]["next_step"],
            )
        plan = bay.get("plan")
        if not plan or not plan.get("tests"):
            vehicle = case.get("vehicle", {})
            return "Bay case is open on a %s. Draft the plan to get ranked tests." % (
                vehicle.get("category", "car")
            )
        pending = [t for t in ranked_tests(plan) if t.get("standing") == "pending"]
        done = len(plan.get("results", {}))
        if "why" in text or "rank" in text:
            if not pending:
                return "Every test is recorded. %d done, %d ruled-out causes." % (
                    done,
                    len(plan.get("eliminated", [])),
                )
            top = pending[0]
            parts = top.get("score_parts", {})
            return "Next up is '%s' with %d points: symptom match %d, code match %d, rules out an expensive job %d, quick %d, shop boost %d, suspected-cause bonus %d. %d of %d tests recorded." % (
                top["title"],
                top.get("score", 0),
                parts.get("symptom_match", 0),
                parts.get("code_match", 0),
                parts.get("rules_out_expensive", 0),
                parts.get("quick", 0),
                parts.get("shop_boost", 0),
                parts.get("suspected_cause", 0),
                done,
                len(plan.get("tests", [])),
            )
        last = plan["trail"][-1]["caused_by"] if plan.get("trail") else "no results yet"
        return "Bay case: %d of %d tests recorded. %s" % (done, len(plan.get("tests", [])), last)

    def _api_chat(self, payload):
        session_id = payload.get("sessionId")
        session = get_session(session_id) if session_id else None
        message = (payload.get("message") or "").strip()
        if not message:
            self._send_json({"ok": False, "error": "empty message"}, status=400)
            return
        history = ((session or {}).get("chat") or [])[-10:]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def emit(event):
            chunk = ("data: %s\n\n" % json.dumps(event)).encode("utf-8")
            self.wfile.write(chunk)
            self.wfile.flush()

        summary = self._case_summary(session)
        if payload.get("demo"):
            reply = self._local_chat_answer(session, message)
            emit({"type": "mode", "mode": "demo-cache"})
            emit({"type": "token", "text": reply})
            if session is not None:
                trail = session.setdefault("chat", [])
                trail.append({"role": "user", "content": message})
                trail.append({"role": "assistant", "content": reply})
                put_session(session_id, session)
            emit({"type": "done", "mode": "demo-cache"})
            return
        try:
            emit({"type": "mode", "mode": "live"})
            full = []
            for piece in chat_stream(summary, history, message):
                full.append(piece)
                emit({"type": "token", "text": piece})
            reply = "".join(full)
            mode = "live"
        except MetaAPIError:
            reply = self._local_chat_answer(session, message)
            mode = "demo-cache"
            emit({"type": "mode", "mode": mode})
            emit({"type": "token", "text": reply})
        if session is not None:
            trail = session.setdefault("chat", [])
            trail.append({"role": "user", "content": message})
            trail.append({"role": "assistant", "content": reply})
            put_session(session_id, session)
        emit({"type": "done", "mode": mode})


def run(host="127.0.0.1", port=8765):
    server = ThreadingHTTPServer((host, port), Handler)
    print("Shop AI Copilot at http://%s:%d  (Ctrl+C to stop)" % (host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    import sys

    host = "127.0.0.1"
    port = 8765
    for arg in sys.argv[1:]:
        match = re.match(r"--port=(\d+)$", arg)
        if match:
            port = int(match.group(1))
    run(host=host, port=port)
