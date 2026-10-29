"""Credentials settings tests (WO15): profiles, mocks, gate, never-leaves.

Behavior runs in Node against web/credentials.js, the same file the page
loads; static scans pin the never-leaves rule (no network in the module,
no credential surface on the server) and the demo labels.
"""

import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


class CredentialsDriverTest(unittest.TestCase):
    def test_browser_suite(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required to run the credentials suite")
        driver = os.path.join(ROOT, "tests", "credentials_driver.js")
        proc = subprocess.run(
            [node, driver], cwd=ROOT, capture_output=True, text=True, timeout=120
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, "credentials driver failed:\n%s" % output)
        self.assertIn("ALL", output)
        self.assertNotIn("FAIL", output)


class NeverLeavesTest(unittest.TestCase):
    def test_module_makes_no_network_calls(self):
        src = read("web/credentials.js")
        for banned in ("fetch(", "XMLHttpRequest", "WebSocket", "http://",
                       "https://", "urlopen", "require(\"http", "require('http"):
            self.assertNotIn(banned, src, banned)

    def test_server_has_no_credential_surface(self):
        server = read("server.py")
        self.assertNotIn("credential", server.lower())
        for path in ("server.py", "listing.py", "bay.py", "verdict.py",
                     "comps.py", "meta_client.py", "spark_open.py"):
            src = read(path)
            self.assertNotIn("/api/ebay", src, path)
            self.assertNotIn("/api/credential", src, path)
            self.assertNotIn("mockEbay", src, path)

    def test_ui_renders_presence_only(self):
        app = read("web/app.js")
        self.assertIn("presenceLines", app)
        self.assertNotIn("Credentials.loadCreds", app)


class MockDemoTest(unittest.TestCase):
    def test_mock_labels(self):
        src = read("web/credentials.js")
        for phrase in ("demo-mock: fiction for the mock demo",
                       "Mock Distributor (demo)", "Mock Parts Store (demo)",
                       "mock-ebay-developer-api", "Cha-ching (demo mock)",
                       "never guessed"):
            self.assertIn(phrase, src, phrase)

    def test_gate_words(self):
        src = read("web/credentials.js")
        self.assertIn("approve the listing first", src)
        self.assertIn("approval.approved !== true", src)

    def test_page_loads_module(self):
        html = read("web/index.html")
        self.assertIn('<script src="credentials.js"></script>', html)
        self.assertLess(html.index("credentials.js"), html.index("app.js"))


if __name__ == "__main__":
    unittest.main()
