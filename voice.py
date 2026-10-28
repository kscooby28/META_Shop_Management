"""Muse Voice Transcribe adapter: push-to-talk audio in, note text out.

Text replies only. There is no voice-conversation loop and no spoken
reply here: Transcribe is realtime speech-to-text, and this stack has no
text-to-speech endpoint, so none is built or faked. A voice note is a
note like any other: local, never sent anywhere except the transcription
API when live, and never bypassing the listing Approve gate.

Isolated adapter with its own transport and key loading, following the
meta_client pattern. VOICE_LIVE stays False until the owner confirms the
Meta API key rotation; while False every call serves the demo cache and
never touches the network. The live model id and endpoint path come from
the local environment (MUSE_VOICE_MODEL, MUSE_VOICE_PATH) and are never
guessed: live refuses when either is unset.
"""

import json
import os
import urllib.error
import urllib.request

from meta_client import MetaAPIError

# Live transcription stays OFF until the owner confirms the Meta API key
# rotation. While False, every mic press serves a demo-cache transcript
# and never calls the live API. Flipping this flag later changes the data
# source only; the interface does not change.
VOICE_LIVE = False
TIMEOUT_SECONDS = 30
KINDS = ("bay", "inv")


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
        "model": os.environ.get("MUSE_VOICE_MODEL") or dotenv.get("MUSE_VOICE_MODEL") or "",
        "path": os.environ.get("MUSE_VOICE_PATH") or dotenv.get("MUSE_VOICE_PATH") or "",
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


def transcribe_live(audio_b64, mime=""):
    """Ask Transcribe to turn audio into text. Live only.

    Raises MetaAPIError without touching the network unless the live flag
    is on, audio is present, and a model id and path are configured.
    """
    if not VOICE_LIVE:
        raise MetaAPIError("voice live is off until the key rotation", kind="unreachable")
    if not (audio_b64 or "").strip():
        raise MetaAPIError("no audio in request", kind="bad_response")
    cfg = _live_settings()
    if not cfg["model"] or not cfg["path"]:
        raise MetaAPIError(
            "voice live model/path unconfirmed; set MUSE_VOICE_MODEL and MUSE_VOICE_PATH",
            kind="unreachable",
        )
    body = json.dumps({
        "model": cfg["model"],
        "audio": audio_b64,
        "mime": mime or "audio/webm",
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
        raise MetaAPIError("voice API error %s" % exc.code, kind="unreachable")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise MetaAPIError("voice API unreachable: %s" % exc, kind="unreachable")
    try:
        text = raw["text"]
        assert isinstance(text, str) and text.strip()
    except (KeyError, AssertionError, TypeError) as exc:
        raise MetaAPIError("voice returned an unusable shape: %s" % exc, kind="bad_response")
    return {"text": text.strip(), "source": "voice-live"}


def demo_transcript(kind, root, audio_present=True):
    """Demo transcript for a bay case or an inventory note. Offline."""
    samples = {}
    try:
        with open(os.path.join(root, "demo_cache", "voice.demo.json"),
                  "r", encoding="utf-8") as fh:
            samples = json.load(fh).get("samples", {})
    except (OSError, ValueError):
        pass
    text = samples.get(kind) or samples.get("default") or ""
    note = "Transcript (demo sample)."
    if not audio_present:
        note = "No audio arrived, so a demo sample stands in. " + note
    return {"text": text, "note": note, "source": "demo-cache: voice sample"}


def transcribe(audio_b64, kind, root):
    """Gated entry: live transcription when on, else the demo sample."""
    if kind not in KINDS:
        raise MetaAPIError("target kind must be bay or inv", kind="bad_response")
    if not VOICE_LIVE:
        return dict(
            demo_transcript(kind, root, bool((audio_b64 or "").strip())),
            mode="demo-cache",
        )
    try:
        result = transcribe_live(audio_b64)
    except MetaAPIError:
        result = demo_transcript(kind, root, bool((audio_b64 or "").strip()))
        result["mode"] = "demo-cache"
        return result
    result["mode"] = "live"
    result["note"] = "Transcript, live."
    return result
