"""Muse Image studio adapter: cutout in, studio-background listing photo out.

Isolated adapter with its own transport and key loading, following the
meta_client pattern. IMAGE_LIVE stays False until the owner confirms the
Meta API key rotation; while False every call serves the demo cache and
never touches the network. The live model id and endpoint path come from
the local environment (MUSE_IMAGE_MODEL, MUSE_IMAGE_PATH) and are never
guessed: live refuses when either is unset, so flipping the flag later is
safe and changes the data source only. No new runtime dependencies.
"""

import json
import os
import re
import urllib.error
import urllib.request
import xml.sax.saxutils as saxutils

from meta_client import MetaAPIError

# Live studio stays OFF until the owner confirms the Meta API key rotation.
# While False, the listing card serves demo-cache studio photos and never
# calls the live API. Flipping this flag later changes the data source
# only; the interface does not change.
IMAGE_LIVE = False
TIMEOUT_SECONDS = 20

SVG_OUTER_OPEN = re.compile(r"\A\s*<svg[^>]*>", re.DOTALL)
SVG_OUTER_CLOSE = re.compile(r"</svg>\s*\Z", re.DOTALL)
DEMO_FRAME = re.compile(r"\Ademo-frame-(\d+)\Z")

CANVAS = 800
BACKDROP = "#f4f4f2"
MAX_PART = 560


def _live_settings():
    dotenv = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                  "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                if key.strip() and value.strip():
                    dotenv[key.strip()] = value.strip().strip("'").strip('"')
    except OSError:
        pass
    base = (
        os.environ.get("META_API_BASE") or dotenv.get("META_API_BASE")
        or "https://api.meta.ai/v1"
    ).rstrip("/")
    return {
        "api_base": base,
        "model": os.environ.get("MUSE_IMAGE_MODEL") or dotenv.get("MUSE_IMAGE_MODEL") or "",
        "path": os.environ.get("MUSE_IMAGE_PATH") or dotenv.get("MUSE_IMAGE_PATH") or "",
    }


def _api_key():
    values = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                  "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip("'").strip('"')
    except OSError:
        pass
    key = (
        os.environ.get("META_API_KEY") or values.get("META_API_KEY")
        or os.environ.get("MODEL_API_KEY") or values.get("MODEL_API_KEY") or ""
    ).strip()
    if not key:
        raise MetaAPIError("no API key in local .env or environment", kind="auth")
    return key


def request_studio_render(cutout_data_url, label):
    """Ask Muse Image for a studio-background render. Live only.

    Raises MetaAPIError without touching the network unless the live flag
    is on, a model id is configured, and a key is present.
    """
    if not IMAGE_LIVE:
        raise MetaAPIError("studio live is off until the key rotation", kind="unreachable")
    if not cutout_data_url:
        raise MetaAPIError("no cutout bytes in request", kind="bad_response")
    cfg = _live_settings()
    if not cfg["model"] or not cfg["path"]:
        raise MetaAPIError(
            "studio live model/path unconfirmed; set MUSE_IMAGE_MODEL and MUSE_IMAGE_PATH",
            kind="unreachable",
        )
    body = json.dumps({
        "model": cfg["model"],
        "image": cutout_data_url,
        "prompt": "Clean e-commerce studio photo of this used car part (%s): "
                  "seamless light-gray backdrop, soft shadow, centered, no text, "
                  "no watermark, honest condition, nothing added or removed." % (label or "part"),
    }).encode("utf-8")
    request = urllib.request.Request(
        cfg["api_base"] + cfg["path"],
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
            raise MetaAPIError("API key rejected (%s)" % exc.code, kind="auth")
        raise MetaAPIError("studio API error %s" % exc.code, kind="unreachable")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise MetaAPIError("studio API unreachable: %s" % exc, kind="unreachable")
    try:
        data_url = raw["image"]
        assert isinstance(data_url, str) and data_url.startswith("data:")
    except (KeyError, AssertionError, TypeError) as exc:
        raise MetaAPIError("studio returned an unusable shape: %s" % exc, kind="bad_response")
    return {
        "kind": "image",
        "body": data_url,
        "note": "Studio photo, rendered live.",
        "source": "image-live",
    }


def composite_svg(frame_svg, box, label):
    """Deterministic demo composite: clean backdrop + cropped source frame.

    Pure function of its inputs: no network, no timestamps, no randomness.
    The nested svg reuses the shipped demo frame's own artwork cropped to
    the cutout box, centered on a studio backdrop with a floor shadow and
    a plain caption. Badged as a demo composite by the caller.
    """
    x1, y1, x2, y2 = [int(v) for v in box]
    w, h = max(1, x2 - x1), max(1, y2 - y1)
    scale = min(MAX_PART / w, MAX_PART / h)
    dw, dh = w * scale, h * scale
    x = (CANVAS - dw) / 2
    y = (CANVAS - 60 - dh) / 2
    inner = SVG_OUTER_OPEN.sub("", frame_svg or "")
    inner = SVG_OUTER_CLOSE.sub("", inner)
    caption = saxutils.escape((label or "part") + " — demo composite")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800" '
        'width="100%%" role="img" aria-label="%s">'
        '<rect width="800" height="800" fill="%s"/>'
        '<ellipse cx="400" cy="%d" rx="%d" ry="26" fill="#000" opacity="0.12"/>'
        '<svg x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
        'viewBox="%d %d %d %d">%s</svg>'
        '<text x="400" y="752" text-anchor="middle" font-size="26" '
        'fill="#5c564c" font-family="sans-serif">%s</text>'
        "</svg>"
    ) % (caption, BACKDROP, int(y + dh + 34), int(dw / 2), x, y, dw, dh,
         x1, y1, w, h, inner, caption)


def _frame_source(frame, root):
    match = DEMO_FRAME.match(frame or "")
    if not match:
        return None
    path = os.path.join(root, "web", "demo", "frame%s.svg" % match.group(1))
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def demo_lookup(part_id, cutout, root, label=""):
    """Demo studio photo: checked-in sample first, else build the composite.

    Returns a studio dict ({kind, body, note, source}) or None when no
    cutout box exists — the caller then falls back to the cutout preview.
    """
    box = (cutout or {}).get("box")
    if not box or len(box) != 4:
        return None
    samples = {}
    try:
        with open(os.path.join(root, "demo_cache", "studio.demo.json"),
                  "r", encoding="utf-8") as fh:
            samples = json.load(fh).get("samples", {})
    except (OSError, ValueError):
        pass
    if part_id in samples:
        return {
            "kind": "svg",
            "body": samples[part_id],
            "note": "Studio photo (demo sample).",
            "source": "demo-cache: studio sample",
        }
    frame_svg = _frame_source((cutout or {}).get("frame"), root)
    if frame_svg is None:
        return None
    return {
        "kind": "svg",
        "body": composite_svg(frame_svg, box, label or part_id),
        "note": "Studio photo (demo composite of the source frame).",
        "source": "demo-cache: studio composite (built)",
    }
