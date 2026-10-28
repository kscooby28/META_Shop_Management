"""Client for the Meta Model API (base https://api.meta.ai/v1).

Muse Spark 1.3 handles intake, car/part identification, grounding on a
0-1000 grid, counting, and structured JSON output. SAM 3.1 handles
phrase-to-pixel masks and boxes.

The API key is loaded from the local ``.env`` file or process environment
(``META_API_KEY`` preferred, ``MODEL_API_KEY`` as fallback) and is never
logged or stored. Any transport, auth, credit, timeout, or shape problem
raises :class:`MetaAPIError` so the caller can fall back to demo cache.
"""

import json
import os
import urllib.error
import urllib.request

API_BASE = "https://api.meta.ai/v1"
SPARK_MODEL = "muse-spark-1.3"
SAM_MODEL = "sam-3-1"
TIMEOUT_SECONDS = 12


class MetaAPIError(Exception):
    def __init__(self, message, kind="unreachable"):
        super().__init__(message)
        self.kind = kind  # unreachable | auth | credits | bad_response | demo


def _repo_root():
    return os.path.dirname(os.path.abspath(__file__))


def _read_dotenv(path):
    values = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and value:
                    values[key] = value
    except OSError:
        pass
    return values


def settings():
    dotenv = _read_dotenv(os.path.join(_repo_root(), ".env"))
    base = (
        os.environ.get("META_API_BASE")
        or dotenv.get("META_API_BASE")
        or API_BASE
    ).rstrip("/")
    return {
        "api_base": base,
        "spark_model": os.environ.get("SPARK_MODEL") or dotenv.get("SPARK_MODEL") or SPARK_MODEL,
        "sam_model": os.environ.get("SAM_MODEL") or dotenv.get("SAM_MODEL") or SAM_MODEL,
    }


def api_key_present():
    dotenv = _read_dotenv(os.path.join(_repo_root(), ".env"))
    key = (
        os.environ.get("META_API_KEY")
        or dotenv.get("META_API_KEY")
        or os.environ.get("MODEL_API_KEY")
        or dotenv.get("MODEL_API_KEY")
    )
    return bool(key and key.strip())


def _api_key():
    dotenv = _read_dotenv(os.path.join(_repo_root(), ".env"))
    key = (
        os.environ.get("META_API_KEY")
        or dotenv.get("META_API_KEY")
        or os.environ.get("MODEL_API_KEY")
        or dotenv.get("MODEL_API_KEY")
        or ""
    ).strip()
    if not key:
        raise MetaAPIError("no API key in local .env or environment", kind="auth")
    return key


def _post(path, payload):
    cfg = settings()
    url = cfg["api_base"] + path
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": "Bearer " + _api_key(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        lowered = detail.lower()
        if exc.code in (401, 403):
            raise MetaAPIError("API key rejected (%s)" % exc.code, kind="auth")
        if exc.code == 429 or "credit" in lowered or "quota" in lowered or "balance" in lowered:
            raise MetaAPIError("API credits exhausted (%s)" % exc.code, kind="credits")
        raise MetaAPIError("API error %s: %s" % (exc.code, detail), kind="unreachable")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise MetaAPIError("API unreachable: %s" % exc, kind="unreachable")


INTAKE_PROMPT = """You are the intake step of a salvage-harvest copilot. Look at the car photos.
Identify the car only as far as the photos honestly support: year (a single year
or a year range, else "unknown"), make, model, trim (often "unknown" unless a
badge is clearly visible). Never invent trim, part numbers, prices, or specs.

Then list each valuable salvage part you can actually see (lights, wheels,
mirrors, bumpers, grilles, glass, handles, badges). For each part give:
- id: short stable slug
- label: plain-words name
- category: lighting | wheel | body | glass | trim | interior | other
- box: [x1, y1, x2, y2] on a 0-1000 grid over the photo it came from
- point: [x, y] center of the part on the same 0-1000 grid
- source_tag: which photo it came from (use the provided file names)
- intact: "yes" | "no" | "unknown", plus intact_note in plain words
- count: how many of this repeated part are visible (Spark counting)

Reply with JSON only: {"car": {"year": ..., "make": ..., "model": ...,
"trim": ..., "notes": ...}, "parts": [...]}. Every field you cannot honestly
fill must be "unknown" with a short note saying so."""


def _as_data_url(image):
    data = image.get("data") or ""
    if data.startswith("data:"):
        return data
    mime = image.get("mime") or "image/jpeg"
    return "data:%s;base64,%s" % (mime, data)


def identify_car(images):
    """Run Spark intake: car ID plus grounded money parts."""
    cfg = settings()
    names = [img.get("name", "photo-%d" % i) for i, img in enumerate(images)]
    content = [
        {"type": "text", "text": INTAKE_PROMPT + "\nPhoto names in order: " + ", ".join(names)}
    ]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": _as_data_url(image)}})
    raw = _post(
        "/chat/completions",
        {
            "model": cfg["spark_model"],
            "messages": [{"role": "user", "content": content}],
            "response_format": {"type": "json_object"},
        },
    )
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        car = parsed["car"]
        parts = parsed["parts"]
        assert isinstance(car, dict) and isinstance(parts, list)
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        raise MetaAPIError("Spark returned an unexpected shape: %s" % exc, kind="bad_response")
    for part in parts:
        part.setdefault("source", "spark-live")
    car.setdefault("source", "spark-live")
    return {"car": car, "parts": parts}


def segment_parts(images, phrases, intake):
    """Run SAM masks for each grounded part, tracked across frames.

    Returns harvest-shaped data: parts with per-frame sightings (box, mask
    polygon on the 0-1000 grid, coverage) plus Spark counts. Merges SAM output
    back onto the intake parts so every entry keeps its source tag.
    """
    cfg = settings()
    sightings = {phrase: [] for phrase in phrases}
    for index, image in enumerate(images):
        frame = image.get("name", "photo-%d" % index)
        raw = _post(
            "/sam/segment",
            {
                "model": cfg["sam_model"],
                "image": _as_data_url(image),
                "phrases": phrases,
                "coordinate_grid": 1000,
            },
        )
        try:
            masks = raw["masks"]
            assert isinstance(masks, list)
        except (KeyError, AssertionError, TypeError) as exc:
            raise MetaAPIError("SAM returned an unexpected shape: %s" % exc, kind="bad_response")
        for mask in masks:
            phrase = mask.get("phrase", "")
            if phrase not in sightings:
                continue
            sightings[phrase].append(
                {
                    "frame": frame,
                    "box": mask.get("box"),
                    "polygon": mask.get("polygon"),
                    "coverage": mask.get("coverage"),
                    "score": mask.get("score"),
                    "source_tag": frame,
                    "source": "sam-live",
                }
            )
    parts = []
    for intake_part in intake.get("parts", []):
        label = intake_part.get("label", "")
        seen = sightings.get(label, [])
        if not seen:  # keep the intake grounding as the single sighting
            box = intake_part.get("box")
            seen = [
                {
                    "frame": intake_part.get("source_tag", "photo-0"),
                    "box": box,
                    "polygon": None,
                    "coverage": None,
                    "score": None,
                    "source_tag": intake_part.get("source_tag", "photo-0"),
                    "source": "spark-live",
                }
            ]
        parts.append(
            {
                "id": intake_part.get("id"),
                "label": label,
                "category": intake_part.get("category", "other"),
                "intact": intake_part.get("intact", "unknown"),
                "intact_note": intake_part.get("intact_note", ""),
                "count": intake_part.get("count", 1),
                "sightings": seen,
            }
        )
    return {"car": intake.get("car", {}), "parts": parts}


LISTING_PROMPT = """You write honest used-part listings. Given the part evidence and any
sourced comps as JSON, reply with JSON only: {"title": ..., "description": ...,
"condition": ...}. State visible flaws plainly; never invent fitment, part
numbers, or prices. If no sourced price exists, say so in the description and
suggest "make an offer". Plain words, no jargon."""


def draft_listing(part, comp, verdict_info, car):
    """Ask Spark to write the listing card. Raises MetaAPIError on problems."""
    cfg = settings()
    evidence = {"part": part, "comp": comp, "verdict": verdict_info, "car": car}
    raw = _post(
        "/chat/completions",
        {
            "model": cfg["spark_model"],
            "messages": [
                {"role": "system", "content": LISTING_PROMPT},
                {"role": "user", "content": json.dumps(evidence)},
            ],
            "response_format": {"type": "json_object"},
        },
    )
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        assert isinstance(parsed.get("title"), str) and isinstance(parsed.get("description"), str)
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        raise MetaAPIError("Spark listing draft unusable: %s" % exc, kind="bad_response")
    parsed.setdefault("condition", part.get("intact_note", ""))
    parsed["source"] = "spark-live"
    return parsed


CHAT_SYSTEM = """You are Shop Copilot, the assistant panel of a shop/harvest app for a
Gulf Coast shop. Answer in plain words, no jargon. Never guess: every fact
must come from the case summary provided or be marked as lacking reliable
data. Never invent part numbers, prices, torque values, or labor times. Keep
replies short. You are not braubus and must never claim to be."""


def _post_stream(path, payload):
    """POST a stream:true chat request, yielding text chunks. Raises MetaAPIError."""
    import time as _time

    cfg = settings()
    url = cfg["api_base"] + path
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": "Bearer " + _api_key(),
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        response = urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS + 18)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        lowered = detail.lower()
        if exc.code in (401, 403):
            raise MetaAPIError("API key rejected (%s)" % exc.code, kind="auth")
        if exc.code == 429 or "credit" in lowered or "quota" in lowered:
            raise MetaAPIError("API credits exhausted", kind="credits")
        raise MetaAPIError("API error %s" % exc.code, kind="unreachable")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise MetaAPIError("API unreachable: %s" % exc, kind="unreachable")
    deadline = _time.time() + TIMEOUT_SECONDS + 18
    try:
        with response:
            for raw_line in response:
                if _time.time() > deadline:
                    break
                line = raw_line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                    chunk = event["choices"][0]["delta"].get("content", "")
                except (ValueError, KeyError, IndexError, TypeError):
                    continue
                if chunk:
                    yield chunk
    except MetaAPIError:
        raise
    except Exception as exc:
        raise MetaAPIError("stream broke: %s" % exc, kind="unreachable")


def chat_stream(case_summary, history, user_message):
    """Yield Spark reply chunks for the Shop Copilot panel."""
    cfg = settings()
    messages = [{"role": "system", "content": CHAT_SYSTEM}]
    if case_summary:
        messages.append({"role": "system", "content": "Current case:\n" + case_summary})
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})
    yielded = False
    for chunk in _post_stream(
        "/chat/completions", {"model": cfg["spark_model"], "messages": messages, "stream": True}
    ):
        yielded = True
        yield chunk
    if not yielded:
        raise MetaAPIError("Spark returned an empty stream", kind="bad_response")


VIN_PROMPT = """You read a VIN plate photo for a repair shop. Reply with JSON only:
{"vin": ..., "year": ..., "make": ..., "model": ..., "trim": ..., "engine": ...,
"notes": ...}. Read only characters you can actually see; any field you cannot
honestly fill must be "unknown" with a short note saying so. Never invent trim,
engine codes, or VIN characters. Trim stays "unknown" unless a badge is clearly
readable in the photo."""


def read_vin_photo(image):
    """Ask Spark to read a VIN plate. Raises MetaAPIError on any problem."""
    cfg = settings()
    raw = _post(
        "/chat/completions",
        {
            "model": cfg["spark_model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VIN_PROMPT},
                        {"type": "image_url", "image_url": {"url": _as_data_url(image)}},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        },
    )
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        assert isinstance(parsed, dict) and isinstance(parsed.get("vin"), str)
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        raise MetaAPIError("Spark VIN read unusable: %s" % exc, kind="bad_response")
    for field in ("year", "make", "model", "trim", "engine"):
        parsed.setdefault(field, "unknown")
    parsed["source"] = "spark-live"
    return parsed


PLAN_PROMPT = """You draft a ranked diagnostic test plan for a repair shop that owns an
Autel MK908 scan tool (live data and special functions) and hand tools. The shop
does NOT have PIWIS: never write a step that needs it. Given the case as JSON
(symptom in the customer's own words, fault codes, observations, vehicle),
reply with JSON only: {"tests": [...]}. Each test: {"title", "what" (what to
check), "how" (how to check it with the Autel or by hand), "expected" (what a
good result looks like), "causes" (suspected causes this test addresses),
"eliminates_on_pass", "eliminates_on_fail", "suspects_on_fail",
"symptom_match" (true/false), "code_match" (true/false),
"rules_out_expensive" (true/false), "quick" (true/false)}. Plain words, no
jargon. Never invent part numbers, prices, torque values, or labor times. If
the evidence is thin, say so in a test's "what" instead of guessing."""


PART_PROMPT = """You identify one photographed car part for an enthusiast's inventory.
Reply with JSON only: {"label": ..., "condition": ..., "notes": ...}. Name the
part in plain words. State only the condition you can honestly see; anything
unclear must say so. Never invent part numbers, fitment, or prices."""


def describe_part(image):
    """Ask Spark to describe one part photo. Raises MetaAPIError."""
    cfg = settings()
    raw = _post(
        "/chat/completions",
        {
            "model": cfg["spark_model"],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PART_PROMPT},
                        {"type": "image_url", "image_url": {"url": _as_data_url(image)}},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        },
    )
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        assert isinstance(parsed.get("label"), str)
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        raise MetaAPIError("Spark part read unusable: %s" % exc, kind="bad_response")
    parsed.setdefault("condition", "unknown")
    parsed.setdefault("notes", "")
    parsed["source"] = "spark-live"
    return parsed


def draft_plan(case):
    """Ask Spark to draft the ranked test plan. Raises MetaAPIError."""
    cfg = settings()
    raw = _post(
        "/chat/completions",
        {
            "model": cfg["spark_model"],
            "messages": [
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": json.dumps(case)},
            ],
            "response_format": {"type": "json_object"},
        },
    )
    try:
        text = raw["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        assert isinstance(parsed.get("tests"), list) and parsed["tests"]
    except (KeyError, IndexError, AssertionError, ValueError, TypeError) as exc:
        raise MetaAPIError("Spark plan draft unusable: %s" % exc, kind="bad_response")
    return parsed["tests"]
