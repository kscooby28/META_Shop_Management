"""Bay side tests: intake, declines, ranking, re-ranking, labor, KB."""

import json
import os
import tempfile
import unittest

from bay import (
    build_case,
    categorize,
    edit_plan,
    labor_math,
    load_bay_case,
    load_kb,
    match_decline,
    new_plan,
    ranked_tests,
    record_result,
    search_kb,
    strip_vin,
    validate_intake,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def manual(**over):
    base = {
        "vehicle": {"year": 2009, "make": "BMW", "model": "335i", "trim": "", "engine": ""},
        "area": "electrical",
        "service_requested": "diagnose",
        "symptom": "Module will not communicate.",
        "codes": ["U0100"],
        "observations": [],
    }
    base.update(over)
    return base


class BayIntakeTest(unittest.TestCase):
    def test_valid_manual_passes(self):
        self.assertEqual(validate_intake(manual()), [])

    def test_missing_symptom_fails(self):
        bad = manual(symptom="  ")
        self.assertTrue(any("symptom" in p for p in validate_intake(bad)))

    def test_bad_year_fails(self):
        bad = manual()
        bad["vehicle"]["year"] = "not a year"
        self.assertTrue(any("year" in p for p in validate_intake(bad)))

    def test_codes_must_be_a_list(self):
        self.assertTrue(any("codes" in p for p in validate_intake(manual(codes="U0100"))))

    def test_bad_area_fails(self):
        self.assertTrue(any("area" in p for p in validate_intake(manual(area="teleportation"))))

    def test_category_and_trim_honesty(self):
        cat = categorize(manual()["vehicle"])
        self.assertEqual(cat["category"], "BMW · 335i")
        self.assertEqual(cat["trim"], "unknown")
        self.assertTrue(cat["shop_make"])

    def test_demo_make_still_matches_shop(self):
        cat = categorize({"year": 2009, "make": "BMW (demo sample)", "model": "3-series"})
        self.assertTrue(cat["shop_make"])

    def test_outside_make_gets_a_note(self):
        cat = categorize({"year": 2010, "make": "Honda", "model": "Civic"})
        self.assertFalse(cat["shop_make"])
        self.assertTrue(any("outside" in n for n in cat["notes"]))


class BayDeclineTest(unittest.TestCase):
    def test_n63_engine_work_declines(self):
        self.assertEqual(
            match_decline({"engine": "N63", "area": "engine", "symptom": "uses oil", "service_requested": ""}),
            "n63-engine",
        )

    def test_n63_no_start_declines_outside_engine_area(self):
        self.assertEqual(
            match_decline(
                {"engine": "n63tu", "area": "electrical", "symptom": "crank no start, nothing", "service_requested": ""}
            ),
            "n63-engine",
        )

    def test_n63_brakes_does_not_decline(self):
        self.assertIsNone(
            match_decline(
                {"engine": "N63", "area": "brakes", "symptom": "squeal when stopping", "service_requested": ""}
            )
        )

    def test_oil_change_declines(self):
        self.assertEqual(
            match_decline({"engine": "", "area": "maintenance", "symptom": "", "service_requested": "oil change please"}),
            "oil-change",
        )

    def test_decline_renders_inside_case(self):
        bad = manual(service_requested="Oil change")
        case = build_case(
            "b-1",
            bad["vehicle"],
            {"symptom": bad["symptom"], "codes": [], "observations": [], "area": "maintenance",
             "service_requested": "Oil change", "engine": ""},
        )
        self.assertTrue(case["declined"])
        self.assertEqual(case["decline"]["verdict"], "declined")
        self.assertTrue(case["decline"]["next_step"])
        self.assertIn("category", case["vehicle"])


class BayPlanTest(unittest.TestCase):
    def setUp(self):
        intake = load_bay_case("intake", "case1", ROOT)
        vehicle = intake["vehicle"]
        self.case = build_case(
            "b-test",
            vehicle,
            {"symptom": intake["symptom"], "codes": intake["codes"],
             "observations": intake["observations"], "area": intake["area"],
             "service_requested": intake["service_requested"], "engine": vehicle.get("engine", "")},
        )
        self.raw = load_bay_case("plan", "case1", ROOT)["tests"]

    def test_initial_ranking_is_visible_and_ordered(self):
        plan = new_plan(self.case, self.raw)
        order = [t["id"] for t in ranked_tests(plan)]
        self.assertEqual(order, ["t1", "t2", "t4", "t3", "t5"])
        top = ranked_tests(plan)[0]
        self.assertEqual(top["score"], 9)
        self.assertEqual(top["score_parts"]["symptom_match"], 3)

    def test_rerank_on_pass_rules_out_and_trails(self):
        plan = new_plan(self.case, self.raw)
        record_result(plan, "t1", "pass", "12.1V steady")
        self.assertIn("no power to module", plan["eliminated"])
        self.assertEqual(plan["trail"][-1]["caused_by"],
                         "Check module power pins with a meter passed, so ruled out: no power to module.")
        self.assertEqual(plan["notes"]["t1"], "12.1V steady")

    def test_rerank_on_fail_suspects_and_trails(self):
        plan = new_plan(self.case, self.raw)
        record_result(plan, "t4", "fail")
        self.assertIn("dead module", plan["suspected"])
        self.assertIn("now suspected: dead module", plan["trail"][-1]["caused_by"])

    def test_bad_result_rejected(self):
        plan = new_plan(self.case, self.raw)
        with self.assertRaises(ValueError):
            record_result(plan, "t1", "maybe")
        with self.assertRaises(KeyError):
            record_result(plan, "nope", "pass")

    def test_case3_fail_rules_out_injector_and_raises_cylinder(self):
        intake = load_bay_case("intake", "case3", ROOT)
        vehicle = intake["vehicle"]
        case = build_case(
            "b-3", vehicle,
            {"symptom": intake["symptom"], "codes": intake["codes"],
             "observations": intake["observations"], "area": intake["area"],
             "service_requested": intake["service_requested"], "engine": vehicle.get("engine", "")},
        )
        plan = new_plan(case, load_bay_case("plan", "case3", ROOT)["tests"])
        before = {t["id"]: t["score"] for t in ranked_tests(plan)}
        self.assertEqual(before["t2"], 6)
        record_result(plan, "t1", "fail", "deviation stayed on 4")
        self.assertIn("bad injector", plan["eliminated"])
        self.assertIn("cylinder-side fault", plan["suspected"])
        after = {t["id"]: t["score"] for t in ranked_tests(plan)}
        self.assertEqual(after["t2"], 11)
        self.assertEqual([t["id"] for t in ranked_tests(plan)][0], "t2")
        self.assertTrue(plan["trail"][-1]["moved"])

    def test_shop_can_reorder_and_edit(self):
        plan = new_plan(self.case, self.raw)
        edit_plan(plan, None, ["t5", "t4", "t3", "t2", "t1"])
        self.assertEqual(plan["manual_order"][0], "t5")
        edited = [dict(t, title="renamed") if t["id"] == "t1" else t for t in plan["tests"]]
        edit_plan(plan, edited, None)
        self.assertEqual(next(t for t in plan["tests"] if t["id"] == "t1")["title"], "renamed")
        self.assertTrue(any("edited" in e["caused_by"] for e in plan["trail"]))


class BayLaborTest(unittest.TestCase):
    def test_known_times_add_up(self):
        intake = load_bay_case("intake", "case1", ROOT)
        vehicle = intake["vehicle"]
        case = build_case(
            "b-1", vehicle,
            {"symptom": intake["symptom"], "codes": intake["codes"],
             "observations": intake["observations"], "area": intake["area"],
             "service_requested": intake["service_requested"], "engine": vehicle.get("engine", "")},
        )
        plan = new_plan(case, load_bay_case("plan", "case1", ROOT)["tests"])
        report = labor_math(plan, {})
        self.assertEqual(report["total_minutes"], 55)
        self.assertIn("$165", report["plain_words"])
        self.assertIn("Verify the donor set index before fitting", report["plain_words"])

    def test_shop_standard_fills_the_gap(self):
        plan = new_plan({"case_id": "b-x"}, [{"id": "t1", "title": "look"}])
        report = labor_math(plan, {"t1": {"minutes": 30, "source": "shop-set estimate"}})
        self.assertIn("$90", report["plain_words"])
        bare = labor_math(plan, {})
        self.assertIn("no shop time on file", bare["lines"][0]["line"])

    def test_unsourced_minutes_do_not_count(self):
        plan = new_plan({"case_id": "b-x"}, [{"id": "t1", "title": "look", "minutes": 30}])
        report = labor_math(plan, {})
        self.assertIsNone(report["lines"][0]["minutes"])


class BayKbTest(unittest.TestCase):
    def test_samples_ship(self):
        notes = load_kb(ROOT)
        self.assertEqual(len(notes), 3)
        self.assertTrue(all(n["source"] == "demo-sample: Bay KB" for n in notes))

    def test_search_finds_fluid_note(self):
        found = search_kb(ROOT, "creep")
        self.assertEqual(len(found), 1)
        self.assertIn("fully hot", found[0]["body"])

    def test_local_slot_reads_tagged_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "shop_kb"))
            with open(os.path.join(tmp, "shop_kb", "tip.json"), "w", encoding="utf-8") as fh:
                json.dump({"title": "shop tip", "body": "check ground first"}, fh)
            notes = load_kb(tmp)
            self.assertEqual(len(notes), 1)
            self.assertEqual(notes[0]["source"], "local shop file: tip.json")

    def test_vin_never_survives_strip(self):
        payload = {"vin": "X" * 17, "nested": [{"vin": "Y" * 17, "keep": 1}]}
        self.assertEqual(strip_vin(payload), {"nested": [{"keep": 1}]})


if __name__ == "__main__":
    unittest.main()
