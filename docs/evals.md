# Model evaluations

Every measurement run behind the README's model table, moved here from
the README in WO22 P3 so judges get the summary first and the receipts
second. The `eval_*_results.json` files are the records: the WO13 and
WO16 tables below render byte-identical from them (pinned by
`tests/test_eval_scale.py` and `tests/test_eval_meta.py`), and the
follow-up plus SAM notes quote their JSON records (pinned by their
suites).

Regenerate a table after a new live run with the same commands as before:

    python scripts/eval_lab.py --write-readme
    python scripts/eval_scale.py --write-readme
    python scripts/eval_meta.py --write-readme

(`--write-readme` now refreshes this file, not the README.)

## Reading guide

- Cite the pooled 22/30, never 0/0. The WO16 table's
  "None: every Spark 1.3 grade matched its rule grade" line covers 0/0
  grades: the Spark leg stopped on a verification timeout, so zero grades
  returned. The follow-up revived Spark at 11/15 and the Baseten yard leg
  at 6/7; pooled with WO16's 5/8 that is 22/30 with no part counted twice.
- The WO22 P3 move reworded demo-leg status lines to "live when keys are
  present" (eval-lab statuses, the WO13 intro, the WO13 engines_demo
  labels). Every measurement row, grade, latency, and reason below is
  untouched.
- SAM verdict: attempted four times, zero geometry returned, leg closed.
  The product harvests from Spark's own grounding boxes instead; the SAM
  adapter stays as a documented attempt.
- Voice and VIN sent zero live calls and stay off: Voice has no confirmed
  model id, VIN has no tested plate image.
- The guided tour runs fully on demo cache, including a forced-demo
  Compare, so it plays with zero keys. The Compare beat additionally shows
  the recorded live Baseten row verbatim (rules B vs Spark Open C on the
  spare coil, 19603 ms), labeled as a recorded live run, never as a demo
  sample.

<!-- EVAL-LAB:START -->
## Eval lab

The same anonymized demo set through each engine. Demo legs are measured below; live legs are flagged off with exactly what would run them. Regenerate with `python scripts/eval_lab.py --write-readme`.

| engine | cases | grounding | agreement | cost | latency | status |
| --- | --- | --- | --- | --- | --- | --- |
| muse-spark-1.3 (demo leg) | 7 yard parts + intake | 7/7 boxes valid | 7/7 owner grades; bay order match, top score match | $0.00 (demo) | 0 ms (sampled) | demo leg, blocked without key: live when keys are present |
| wonder-standard (demo leg) | 7 verdicts routed | n/a (reviewer, not grounder) | 7/7 router outcomes | $0.00 (demo) | shares the run above | demo leg, blocked without key: live when keys are present |
| muse-spark-open-1026 | same demo set, when live | — | — | — | — | blocked: needs BASETEN_API_KEY in the local environment (endpoint https://inference.baseten.co/v1, model meta-models/muse-spark-open-1026) |
| glimmer | same demo set, when live | — | — | — | — | blocked: needs a confirmed hosted endpoint (GLIMMER_ENDPOINT); will not run local on a 12GB card |

- Meta key names checked (META_API_KEY, MODEL_API_KEY): present.
- BASETEN_API_KEY: present.
- GLIMMER_ENDPOINT: unset, endpoint unconfirmed.
- Key names only were read; no values were printed or logged.
<!-- EVAL-LAB:END -->

The eval-lab table was measured on the owner machine with keys present; a
cold clone regenerates it keyless. Its status lines date from before the
WO16 live runs; the demo-leg statuses in the table are current as of
WO22 P3.

<!-- EVAL-SCALE:START -->
## Live evaluation at scale (Work Order 13)

Every demo case through both engines: the deterministic rules grade
and the Muse Spark Open live grade side by side, one live Baseten
call per case, no retries. Spark Open ran live because its key is
present and proven; Spark 1.3, SAM, Image, Voice, and Wonder stayed
on demo (this harness sends no Meta calls; live when keys are
present). Bay job
parts carry no pull-grade meaning in the product; they run here to
measure thin-evidence behavior from name and note alone. Inventory
conditions map to intact unless the text says unknown or untested.
Regenerate with `python scripts/eval_scale.py --write-readme`.

| case | part | rule grade | rule reason | Spark Open live grade | Spark Open reason | match |
| --- | --- | --- | --- | --- | --- | --- |
| yard-demo | driver mirror | A | Clear, wanted, worth listing: Intact, seen across frames, wanted, and priced above the list floor. | B | Intact yes in 2 frames but coverage only 0.0021 is very thin; high demand with $45-$65 (median $55) over 5 solds and net up to $56 with 15-min pull supports money grade B - worth it if you're standing there, not a priority pull. | NO |
| yard-demo | front bumper cover | A | Clear, wanted, worth listing: Intact, seen across frames, wanted, and priced above the list floor. | A | Intact yes in 2 frames at 0.0512 coverage, medium demand with $120-$180 (median $150) over 5 solds net up to $156; 40-min pull is justified by payout, so A - pull and list now. | yes |
| yard-demo | alloy wheel | A | Clear, wanted, worth listing: Intact, seen across frames, wanted, and priced above the list floor. | A | Intact yes with 0.0207 coverage over 3 frames, count 2, high demand with $80-$120 each (median $100) over 5 solds net up to $104; 30-min pull is reasonable for two wheels, so A - pull and list now. | yes |
| yard-demo | driver headlight | B | Good part, softer demand: Intact and not unwanted: grab it while you are there. | B | Intact yes but only 1 frame at 0.0072 coverage so evidence thin; high demand with $55-$75 (median $65) over 5 solds net up to $65 and 20-min pull keeps money grade B - pull if you're at the car. | yes |
| yard-demo | driver door handle | C | Seen once and unclear: Seen in only one frame and condition is unclear: not enough reliable evidence. | C | Intact unknown in 1 frame at 0.0012 coverage, demand unknown, no price and 0 solds on file with no pull time given; evidence too thin for any grade above C, so leave it. | yes |
| yard-demo | left taillight | C | Broken in the photo: The part looks broken, so leave it no matter what else is true. | C | Intact no - damaged - in 1 frame at 0.007 coverage, demand low, no price and 0 solds on file with no pull time; broken part with no market shown, so C - leave it. | yes |
| yard-demo | rear differential | A | Clear, wanted, worth listing: Intact, seen across frames, wanted, and priced above the list floor. | A | Intact yes with strongest 0.084 coverage across 2 frames, high demand with $900-$1100 (median $1000) over 5 solds net up to $954; 60-min pull is heavy but return is highest on car, so A - pull and list now. | yes |
| bay-case1 | Matched module set from one donor car: module, immobilizer, ignition switch, steering lock, key, and door cylinder | C | Seen once and unclear: Seen in only one frame and condition is unclear: not enough reliable evidence. | C | Evidence is too thin to justify pull — price_known false with no low/high/median, money_grade C, sold_count 0, demand unknown, frames_seen 0 with intact unknown, and valuation notes state no sample comp on demo board; case note adds risk that part numbers must match exactly and wrong index was already rejected/refunded. | yes |
| bay-case2 | Clutch-circuit oil, correct spec for this gearbox | C | Seen once and unclear: Seen in only one frame and condition is unclear: not enough reliable evidence. | C | Leave it: intact is unknown, 0 frames seen, demand is unknown with no source, price is unknown with no comps and 0 sold count, and pull time is not given - evidence is too thin to justify pulling clutch-circuit oil. | yes |
| inventory-demo | spare ignition coil | B | Good part, softer demand: Intact and not unwanted: grab it while you are there. | C | Keep as spare, not list: intact yes and used working when pulled but only $25 price_low/high from demo-sample: inventory seed, demand unknown with no demand_source, frames_seen 0 with no coverage, money_grade C with no sample comp, reliable false sold_count 0, pull_minutes null, evidence thin; plus owner_note says Kept as roadside spare for My driver car_label. | NO |
| inventory-demo | driver headlight | B | Good part, softer demand: Intact and not unwanted: grab it while you are there. | B | Intact yes lens clear with $65 price_low/high from demo-sample: inventory seed but demand unknown, frames_seen 0 best_coverage null, money_grade C no sample comp, reliable false sold_count 0, pull_minutes null pull_source empty so evidence thin prevents A; worth pulling if standing there given clear intact condition and moderate price. | yes |
| inventory-demo | rear differential | B | Good part, softer demand: Intact and not unwanted: grab it while you are there. | B | High $1000 price_low/high from demo-sample: inventory seed and intact yes turns smoothly by hand, owner_note says The $1000 reason this car exists, but demand unknown, frames_seen 0, money_grade C no sample comp, reliable false sold_count 0, pull_minutes null; evidence thin with no frames or comps prevents A, but B if onsite due to upside. | yes |
| inventory-demo | alloy wheel | B | Good part, softer demand: Intact and not unwanted: grab it while you are there. | C | Intact yes straight and true but only $40 price_low/high from demo-sample: inventory seed, demand unknown, frames_seen 0, money_grade C no sample comp, reliable false sold_count 0, pull_minutes null; thin evidence and low price for likely wheel pull effort, leave it. | NO |
| inventory-demo | trunk lid | C | Seen once and unclear: Seen in only one frame and condition is unclear: not enough reliable evidence. | C | Intact unknown and condition unknown with owner_note Haven't looked closely yet, price_known false no price_low/high, demand unknown, frames_seen 0, money_grade C no sample comp, reliable false sold_count 0, pull_minutes null; no evidence to justify pull, needs inspection first. | yes |
| inventory-demo | engine computer | C | Seen once and unclear: Seen in only one frame and condition is unclear: not enough reliable evidence. | B | Owner_note says Pull before anything else with $200 price_low/high from demo-sample: owner note but intact unknown, condition used untested, demand unknown, frames_seen 0, money_grade C no sample comp, reliable false sold_count 0, pull_minutes null; evidence thin and unverified prevents A, B only if onsite to inspect/test. | NO |

Agreement: 11/15 parts (11 agree, 15 compared). Live Baseten calls sent: 4. Live Meta calls attempted: 0.

- yard-demo: Spark Open live in 22817 ms, 7/7 parts graded.
- bay-case1: Spark Open live in 6366 ms, 1/1 parts graded.
- bay-case2: Spark Open live in 4377 ms, 1/1 parts graded.
- bay-case3: no call sent (no parts to grade, so no call was sent).
- inventory-demo: Spark Open live in 19603 ms, 6/6 parts graded.

Disagreements, with both reasons:
- yard-demo / driver mirror: rules say A (Clear, wanted, worth listing: Intact, seen across frames, wanted, and priced above the list floor.); Spark Open live says B (Intact yes in 2 frames but coverage only 0.0021 is very thin; high demand with $45-$65 (median $55) over 5 solds and net up to $56 with 15-min pull supports money grade B - worth it if you're standing there, not a priority pull.).
- inventory-demo / spare ignition coil: rules say B (Good part, softer demand: Intact and not unwanted: grab it while you are there.); Spark Open live says C (Keep as spare, not list: intact yes and used working when pulled but only $25 price_low/high from demo-sample: inventory seed, demand unknown with no demand_source, frames_seen 0 with no coverage, money_grade C with no sample comp, reliable false sold_count 0, pull_minutes null, evidence thin; plus owner_note says Kept as roadside spare for My driver car_label.).
- inventory-demo / alloy wheel: rules say B (Good part, softer demand: Intact and not unwanted: grab it while you are there.); Spark Open live says C (Intact yes straight and true but only $40 price_low/high from demo-sample: inventory seed, demand unknown, frames_seen 0, money_grade C no sample comp, reliable false sold_count 0, pull_minutes null; thin evidence and low price for likely wheel pull effort, leave it.).
- inventory-demo / engine computer: rules say C (Seen once and unclear: Seen in only one frame and condition is unclear: not enough reliable evidence.); Spark Open live says B (Owner_note says Pull before anything else with $200 price_low/high from demo-sample: owner note but intact unknown, condition used untested, demand unknown, frames_seen 0, money_grade C no sample comp, reliable false sold_count 0, pull_minutes null; evidence thin and unverified prevents A, B only if onsite to inspect/test.).
<!-- EVAL-SCALE:END -->

<!-- EVAL-META:START -->
## Meta-live evaluation (Work Order 16)

The same demo set as Work Order 13 through every live engine: Spark
1.3 grades, Wonder Standard second opinions through the router leg,
SAM 3.1 mask verification on the yard demo frame, and Spark Open
through Baseten as the baseline. One live call per case per engine,
no retries; auth or credit rejections stop that leg. Bay job parts
carry no pull-grade meaning in the product; they run here to measure
thin-evidence behavior from name and note alone. Regenerate with
`python scripts/eval_meta.py --write-readme`.

Model IDs, confirmed live: Spark muse-spark-1.3 (FAILED: API unreachable: <urlopen error timed out>), SAM sam-3.1 (corrected in code from sam-3-1; the live list names sam-3.1), Wonder muse-wonder-1.0 over /chat/completions (verification call ok).

| case | part | rule | Spark 1.3 live | match | Spark Open live | match |
| --- | --- | --- | --- | --- | --- | --- |
| yard-demo | driver mirror | A | — | no live grade | — | no live grade |
| yard-demo | front bumper cover | A | — | no live grade | — | no live grade |
| yard-demo | alloy wheel | A | — | no live grade | — | no live grade |
| yard-demo | driver headlight | B | — | no live grade | — | no live grade |
| yard-demo | driver door handle | C | — | no live grade | — | no live grade |
| yard-demo | left taillight | C | — | no live grade | — | no live grade |
| yard-demo | rear differential | A | — | no live grade | — | no live grade |
| bay-case1 | Matched module set from one donor car: module, immobilizer, ignition switch, steering lock, key, and door cylinder | C | — | no live grade | C | yes |
| bay-case2 | Clutch-circuit oil, correct spec for this gearbox | C | — | no live grade | C | yes |
| inventory-demo | spare ignition coil | B | — | no live grade | C | NO |
| inventory-demo | driver headlight | B | — | no live grade | C | NO |
| inventory-demo | rear differential | B | — | no live grade | B | yes |
| inventory-demo | alloy wheel | B | — | no live grade | C | NO |
| inventory-demo | trunk lid | C | — | no live grade | C | yes |
| inventory-demo | engine computer | C | — | no live grade | C | yes |

Agreement: Spark 1.3 vs rules 0/0, Spark Open vs rules 5/8, pooled live vs rules 5/8, Spark 1.3 vs Spark Open 0/0. Live Meta calls attempted: 7. Live Baseten calls sent: 4.

- yard-demo: Spark 1.3: no call (leg stopped: Spark verification failed: API unreachable: <urlopen error timed out>); Spark Open: FAILED (Baseten unreachable: <urlopen error timed out>); Wonder: live in 11999 ms, True on p_handle; SAM: FAILED (API error 404:).
- bay-case1: Spark 1.3: no call (leg stopped: Spark verification failed: API unreachable: <urlopen error timed out>); Spark Open: live in 8691 ms; Wonder: live in 27494 ms, partial on bay-case1; SAM: no call (leg stopped: SAM model not on the live list).
- bay-case2: Spark 1.3: no call (leg stopped: Spark verification failed: API unreachable: <urlopen error timed out>); Spark Open: live in 3195 ms; Wonder: live in 23134 ms, partial on bay-case2; SAM: no call (leg stopped: SAM model not on the live list).
- bay-case3: Spark 1.3: no call (leg stopped: Spark verification failed: API unreachable: <urlopen error timed out>); Spark Open: no call (no parts to grade, so no call was sent); Wonder: no call (no parts to review, so no call was sent); SAM: no call (leg stopped: SAM model not on the live list).
- inventory-demo: Spark 1.3: no call (leg stopped: Spark verification failed: API unreachable: <urlopen error timed out>); Spark Open: live in 10930 ms; Wonder: live in 10568 ms, True on ip-lid; SAM: no call (leg stopped: SAM model not on the live list).

Spark 1.3 disagreements, with both reasons:
- None: every Spark 1.3 grade matched its rule grade.

Spark Open disagreements, with both reasons:
- inventory-demo / spare ignition coil: rules say B (Good part, softer demand: Intact and not unwanted: grab it while you are there.); Spark Open live says C (intact yes and working when pulled but price is only $25 low from demo-sample seed, demand unknown, frames_seen 0, no sold comps, money_grade C and reliable false with pull_minutes null - thin evidence, not worth pull and list).
- inventory-demo / driver headlight: rules say B (Good part, softer demand: Intact and not unwanted: grab it while you are there.); Spark Open live says C (intact yes lens clear with $65 demo-sample seed price, but demand unknown, frames_seen 0, no sold comps, money_grade C and reliable false, pull effort unknown - thin demo-only evidence, leave it).
- inventory-demo / alloy wheel: rules say B (Good part, softer demand: Intact and not unwanted: grab it while you are there.); Spark Open live says C (intact yes straight and true but only $40 from demo-sample seed, demand unknown, frames_seen 0, no sold comps, money_grade C and reliable false, pull effort unknown - thin low-value evidence, leave it).

Wonder second opinions, live:
- yard-demo / p_handle (triggers: no reliable price, demand unsourced, condition unclear in photo): Agree with leave it — Seen only once with very small coverage and condition unclear. No sold prices and no demand source on file, so there is no reliable basis to pull it. Watch: Clearer or more photos showing it intact, plus sold prices or a sourced demand, and pull time on file could change this.
- bay-case1 / bay-case1 (triggers: no results recorded yet): Sound start, one ordering question — I agree with starting on module power and relay control. Both match the code and symptom, are marked quick, can clear their cause on a pass, and help avoid costly parts. I question putting the module in-versus-out compare ahead of the pin inspection. The compare clears nothing on a pass and is listed as taking longer, while the pin check can clear damaged pins. The donor index check last fits its low code and symptom match, but it must still be done before fitting. Watch: Recorded results would change my view. Good power and a relay click would clear those causes and raise the value of the pin and module checks. A power fail would point toward wiring as listed, and damaged pins found early would make the module compare less needed. A donor index mismatch would stop that path regardless of order.
- bay-case2 / bay-case2 (triggers: final gate still open: Final gate: hot brake-release creep in D and R, no results recorded yet): Plan covers the checks, but nothing is proven yet — The listed tests match the low pressure, oil, and creep concerns, and they include hot final gates. But the triggers say no results are recorded yet and the hot creep gate is still open, so there is no evidence any test passed. The oil change is also listed ahead of the cold creep check, so a cold baseline could be lost. Watch: Recorded passes for the hot creep in Drive and Reverse and the clean rescan after the hot drive, plus recorded results for the pressure and earlier creep checks, would change this. A cold creep result taken before the oil change would help show what changed.
- inventory-demo / ip-lid (triggers: no reliable price, demand unsourced, condition unclear in photo): Agree: leave it for now — Condition is unknown, demand is unknown with no source, and there is no known or reliable price. The money grade is C with no sample comp and a sold count of zero, so there is not enough solid evidence to justify taking it. Watch: Clear views showing the lid is intact, plus a sourced demand check and a reliable price, would change my mind.

SAM 3.1 yard-frame verification:
- yard-demo: FAILED (API error 404:).

VIN_LIVE gate: stays False (no demo VIN plate images exist, so 0 live VIN calls sent; the flip is unproven).
<!-- EVAL-META:END -->

<!-- EVAL-META-FOLLOWUP:START -->
### Follow-up: one retry pass on the three failed legs (WO16 follow-up)

One attempt per failed leg, plus one Spark image-payload test. Results in `eval_meta_followup_results.json`; the WO16 table above is untouched.

- Spark 1.3 usability: REVIVED. Verify live ok (17221 ms, finish stop, max_tokens headroom 16384, no truncation); per-case grades 11/15 vs rules. Disagreements: yard-demo driver mirror (rules A, live B), inventory-demo spare ignition coil (B/C), alloy wheel (B/C), engine computer (C/B).
- Baseten yard: REVIVED. Yard call live ok in 6953 ms (WO16 timed out at 45s; WO13 took 22s), 6/7 vs rules; only driver mirror disagrees (rules A, live B).
- SAM segment: path CONFIRMED, media rejected. POST /v1/responses with sam-3.1 parsed the request (no 404); HTTP 400 invalid_request_error: `image/svg+xml` unsupported, supported JPEG/PNG/GIF/WebP/ICO. Request ID 74ff9f0d-656a-4b63-97f6-1469943a201e. One attempt used; a future order may resend yard frame 1 as PNG.
- Spark image payload: shape PARSED, media rejected. The data-URI image_url part was structurally accepted (the error points at the part, not the shape); HTTP 400 on `image/svg+xml`, same supported list. Request ID a1a0560a-9902-43f8-b560-b3544eb63cd6. Shape proof only; VIN_LIVE stays False.

Pooled live vs rules updated: 22/30 (WO16 5/8 plus follow-up Spark 11/15 plus follow-up Baseten yard 6/7; no part counted twice). All four legs CLOSED: no further retry follows from this order.
<!-- EVAL-META-FOLLOWUP:END -->

<!-- EVAL-SAM-PNG:START -->
### SAM PNG resend: one segment call on yard frame 1 as PNG

Step 0: faithful PNG rendered in-session (headless Chrome screenshot of web/demo/frame1.svg at native 1000x1000, 37497 bytes, sha256 e993bcd9bbe8ee4eb390b916ee81ceb507e3a2cb7226202c67e08765bc58a59b). No redraw, no substitution.

The call: HTTP 200 in 7931 ms, request ID 11204ad8-1c5c-4b0d-bca2-517e1e7411ae, stream complete, but zero output deltas — verdict responded-empty. The path and PNG media are fully accepted (no 404, no 400); SAM returned no geometry for "driver mirror" on the line drawing.

SAM is NOT proven live (no geometry), so no rewire order follows and nothing follows. Leg closed. VIN_LIVE stays False. Full record in `eval_sam_png_results.json`.
<!-- EVAL-SAM-PNG:END -->

<!-- EVAL-SAM-FILEID:START -->
### SAM file_id probe: one real-photo segment call (2026-10-29)

Upload first, then segment by file_id, on a real photo (outside the repo, never committed): upload HTTP 200, file file-1682256530131941, 3159 ms. Segment: HTTP 200 in 1240 ms, request ID dfbf999f-a67a-4966-a725-54131cee74bd, stream complete, but zero output deltas — geometry ZERO. The file_id shape plus real content returns the same empty signature as the data-URL PNG probes.

SAM verdict: CLOSED AGAIN. No rewire follows. VIN_LIVE stays False. Full record in `eval_sam_fileid_results.json`.
<!-- EVAL-SAM-FILEID:END -->
