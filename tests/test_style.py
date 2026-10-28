"""Shared-style consistency checks (WO6): one card language, one button language.

Fails on any class the page uses but the stylesheet never defines, and on
any stylesheet class nothing uses. Four dynamic patterns build class names
at runtime; their expansions are stated here, which is the documented
exception the work order allows:
  grade- + verdict -> grade-A, grade-B, grade-C (overlay + verdict cards)
  part- + grade   -> part-A, part-B, part-C (harvest overlay groups)
  status + result -> status, pass, fail (test result pills)
  msg + who       -> msg, user, bot (chat thread bubbles)
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")

DYNAMIC = {
    "grade-": {"grade-A", "grade-B", "grade-C"},
    "part-": {"part-A", "part-B", "part-C"},
}

CLASSY = re.compile(r"^[A-Za-z][\w-]*$")
DEFINED_RE = re.compile(r"\.([A-Za-z][\w-]*)")
HTML_CLASS_RE = re.compile(r'class="([^"]+)"')
LITERAL_RE = re.compile(r"""["']([^"'\\]{1,80})["']""")


def defined_classes():
    css = open(os.path.join(WEB, "styles.css"), encoding="utf-8").read()
    return set(DEFINED_RE.findall(css))


def html_classes():
    html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
    out = set()
    for chunk in HTML_CLASS_RE.findall(html):
        out.update(chunk.split())
    return out


JS_ATTR_RE = re.compile(r"""class=["']([\w\s-]+)["']""")
JS_NAME_RE = re.compile(r"""className\s*=\s*["']([^"']*)["']""")
JS_LIST_RE = re.compile(r"""classList\.(?:add|remove|toggle)\(\s*["']([\w-]+)["']""")
JS_SETATTR_RE = re.compile(r"""setAttribute\(\s*["']class["']\s*,\s*["']([\w-]+)["']""")
JS_SELECTOR_RE = re.compile(r"""querySelector(?:All)?\(\s*["']([^"']+)["']""")
JS_BARE_RE = re.compile(r"""["']( ?[\w-]+ ?)["']""")
JS_SPLIT_RE = re.compile(r"""class=(["'])(?:["']\s*\+)?([^"']*?)["']([\w-]+)["']""")
# Literals that look like classes but are ids, events, attributes, or the
# word "class" itself; stripped from class statements before extraction.
JS_NOISE_RES = [
    re.compile(r"""\$\(["'][\w-]+["']\)"""),
    re.compile(r"""getElementById\(["'][\w-]+["']\)"""),
    re.compile(r"""getAttribute\(["'][\w-]+["']\)"""),
    re.compile(r"""addEventListener\(["'][\w-]+["']"""),
    re.compile(r"""showView\(["'][\w-]+["']\)"""),
    re.compile(r"""[!=]==?\s*["'][\w-]+["']"""),
    re.compile(r"""createElement\(["'][\w-]+["']\)"""),
    re.compile(r"""["']class["']"""),
]
# Two call sites pass a class name as a value instead of writing it at the
# class site: cutoutSVG stamps svg.thumb, and the totals card() feeds cls
# into div.totalcard. The test asserts the sites still exist, then counts
# the names used, so the exception cannot go stale silently.
INDIRECT = {"thumb": "cutoutSVG(", "total-a": 'card("A"', "total-b": 'card("B"'}


def js_sources():
    return {
        name: open(os.path.join(WEB, name), encoding="utf-8").read()
        for name in ("app.js", "profile.js", "inventory.js", "gallery.js", "ux.js")
    }


def js_classes():
    out = set()
    for name, src in js_sources().items():
        for cls, site in INDIRECT.items():
            if site in src:
                out.add(cls)
        lines = src.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if "className" in line or "classList" in line or "setAttribute" in line:
                # Whole statement: className ternaries span lines.
                stmt = line
                while ";" not in stmt and i + 1 < len(lines):
                    i += 1
                    stmt += " " + lines[i]
                if "className" not in stmt and "classList" not in stmt \
                        and '"class"' not in stmt and "'class'" not in stmt:
                    i += 1
                    continue  # setAttribute on data-*, not class
                for noise in JS_NOISE_RES:
                    stmt = noise.sub("", stmt)
                for chunk in JS_NAME_RE.findall(stmt):
                    out.update(chunk.split())
                out.update(JS_LIST_RE.findall(stmt))
                out.update(JS_SETATTR_RE.findall(stmt))
                for lit in JS_BARE_RE.findall(stmt):
                    token = lit.strip()
                    if CLASSY.match(token):
                        out.add(token)
            # Normalize escaped quotes: double-quoted JS strings carry
            # class=\"...\" which blinds the attribute patterns.
            clean = line.replace("\\'", "'").replace('\\"', '"')
            for noise in JS_NOISE_RES:
                clean = noise.sub("", clean)
            for chunk in JS_ATTR_RE.findall(clean):
                out.update(chunk.split())
            # Split literals: class names built by concatenation, where the
            # attribute opens in one literal and the name lands in a later
            # one ("<li class='" + (done ? "done" : "") + ..."). Only the
            # name right after an unclosed class= counts, so fallback
            # strings and escaped quotes on the same line stay out.
            for _, _, token in JS_SPLIT_RE.findall(clean):
                if token in DYNAMIC:
                    out.update(DYNAMIC[token])
                elif CLASSY.match(token):
                    out.add(token)
            for sel in JS_SELECTOR_RE.findall(line):
                out.update(DEFINED_RE.findall(sel))
            if '"status ' in line or "'status " in line:
                out.update({"status", "pass", "fail"})
            if '"msg "' in line or "'msg '" in line:
                out.update({"msg", "user", "bot"})
            i += 1
    for frag, expanded in DYNAMIC.items():
        if frag in out:
            out.discard(frag)
            out.update(expanded)
    return out


class StyleConsistencyTest(unittest.TestCase):
    def test_used_classes_are_defined(self):
        defined = defined_classes()
        missing_html = sorted(html_classes() - defined)
        missing_js = sorted(js_classes() - defined)
        self.assertEqual(missing_html, [], "markup uses undefined classes")
        self.assertEqual(missing_js, [], "script uses undefined classes")

    def test_no_orphan_styles(self):
        used = html_classes() | js_classes()
        orphans = sorted(defined_classes() - used)
        self.assertEqual(orphans, [], "stylesheet defines unused classes")

    def test_split_literal_classes_found(self):
        # Regression: guide-step classes built by concatenation ("done")
        # must be found, or dead-rule pruning deletes live styles.
        self.assertIn("done", js_classes())

    def test_indirect_sites_still_exist(self):
        src = "".join(js_sources().values())
        for cls, site in INDIRECT.items():
            self.assertIn(site, src, "indirect class %r lost its call site" % cls)


if __name__ == "__main__":
    unittest.main()
