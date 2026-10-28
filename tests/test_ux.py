"""Usability suite: runs the Node driver against web/ux.js.

Covers the behavior behind the Work Order 5 pass: drafts surviving
reload, guide dismissal persisting, every empty state naming a next
action, destructive actions requiring confirmation, and the tab/view
navigation skeleton standing up.
"""

import os
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class UxTest(unittest.TestCase):
    def test_ux_suites(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required to run the usability suite")
        driver = os.path.join(ROOT, "tests", "ux_driver.js")
        proc = subprocess.run(
            [node, driver], cwd=ROOT, capture_output=True, text=True, timeout=120
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, "ux driver failed:\n%s" % output)
        self.assertIn("ALL", output)
        self.assertNotIn("FAIL", output)


if __name__ == "__main__":
    unittest.main()
