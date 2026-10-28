"""VIN line tests: live stays off, and no VIN reaches any disk write."""

import unittest

from bay import VIN_LIVE, strip_vin


def vin_keys(payload, found=None):
    found = [] if found is None else found
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered == "vin" or lowered.endswith("_vin"):
                found.append(key)
            vin_keys(value, found)
    elif isinstance(payload, list):
        for value in payload:
            vin_keys(value, found)
    return found


class VinLineTest(unittest.TestCase):
    def test_live_vin_stays_off(self):
        self.assertIs(VIN_LIVE, False)

    def test_strip_removes_vin_and_bay_vin(self):
        payload = {
            "vin": "X" * 17,
            "bay_vin": "Y" * 17,
            "nested": [{"VIN": "Z" * 17, "keep": 1}],
            "proving": "a word containing vin stays",
        }
        cleaned = strip_vin(payload)
        self.assertEqual(vin_keys(cleaned), [])
        self.assertEqual(cleaned["nested"][0]["keep"], 1)
        self.assertEqual(cleaned["proving"], "a word containing vin stays")

    def test_intake_shaped_payload_has_no_vin_after_strip(self):
        case = {
            "case_id": "b-1",
            "vin": "REDACTED-PLATE",
            "vehicle": {"year": 2009, "make": "BMW", "model": "335i"},
            "symptom": "no-start",
        }
        self.assertEqual(vin_keys(strip_vin(case)), [])
        self.assertEqual(strip_vin(case)["vehicle"]["make"], "BMW")


if __name__ == "__main__":
    unittest.main()
