"""Browser-logic suite: runs the Node driver against web/profile.js + web/inventory.js.

The first-run profile and the inventory live in the browser by design
(local-only, never sent anywhere), so their logic is tested where it runs:
Node executes the same files the page loads. Node is a documented test
dependency (see README); a missing Node fails loudly instead of skipping.
"""

import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class WebLogicTest(unittest.TestCase):
    def test_browser_suites(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required to run the browser-logic suite")
        driver = os.path.join(ROOT, "tests", "web_logic_driver.js")
        proc = subprocess.run(
            [node, driver], cwd=ROOT, capture_output=True, text=True, timeout=120
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, "web logic driver failed:\n%s" % output)
        self.assertIn("ALL", output)
        self.assertNotIn("FAIL", output)


if __name__ == "__main__":
    unittest.main()
