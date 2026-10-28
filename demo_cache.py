"""Demo-mode cache behind every AI step.

Each step (``intake``, ``harvest``) has a checked-in anonymized demo response
in ``demo_cache/<step>.demo.json``. Live successes are also saved per session
under ``demo_cache/live/`` so a repeat run can replay them. Lookup order on
failure: this session's live cache, then the demo case. Nothing here contains
real customer data, real VINs, or factory manual content.
"""

import json
import os


class StepCache:
    def __init__(self, root):
        self.root = root
        self.demo_dir = os.path.join(root, "demo_cache")
        self.live_dir = os.path.join(self.demo_dir, "live")

    def load_demo(self, step):
        path = os.path.join(self.demo_dir, "%s.demo.json" % step)
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def save_live(self, session_id, step, payload):
        try:
            folder = os.path.join(self.live_dir, session_id)
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "%s.json" % step), "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except OSError:
            pass  # cache is best-effort; the live result still returns

    def load_live(self, session_id, step):
        path = os.path.join(self.live_dir, session_id, "%s.json" % step)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def fallback(self, session_id, step):
        """Newest good response for this session, else the demo case."""
        live = self.load_live(session_id, step) if session_id else None
        if live is not None:
            return live, "replayed this session's last live %s" % step
        return self.load_demo(step), "demo"

    def notice(self, step, error):
        kind = getattr(error, "kind", "unreachable")
        if kind == "demo":
            return "Demo case: showing the anonymized sample car, not your upload."
        if kind == "credits":
            return "API credits ran out, so this step uses the cached demo case."
        if kind == "auth":
            return "API key was not accepted, so this step uses the cached demo case."
        if kind == "bad_response":
            return "Live AI gave an unusable answer, so this step uses the cached demo case."
        return "Live AI is unreachable, so this step uses the cached demo case."
