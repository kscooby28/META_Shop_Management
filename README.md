# Shop AI Copilot

Shop software built for the Meta AI Hackathon. Point your phone at any car —
and know what it is, what it is worth, and what to do next.

This repo ships the foundation plus the enthusiast (Yard) side's first flow:
photo in, car identified, harvest map with masks, A/B/C verdicts with visible
rules, plain-money totals, and a listing draft behind the Approve gate. The
shop-manager core (the Bay) shipped as Work Order 2 on the same scaffold.

## Demo video first

The three-minute demo video is what the judges watch, and it is the
acceptance test for this build. Every feature must earn its minutes on
camera: if it does not play on video, it is not done.

Priority order: the video first, the functional repository second. The
repository exists to make the video true — everything shown on camera
runs in this repo, end to end, on demo cache.

The video spine, one continuous journey: first-run setup, one question,
shop or enthusiast. Enthusiast home. Register a parts car by photo and
VIN, confirm, done. The what-to-look-for moment: the mid-90s M3 parts
car surfaces the engine computer, no EWS, the E30 crowd wants it, $200.
Inventory with plain-money totals. A listing draft behind the Approve
gate — nothing posts without a human saying so. Shop home. A Bay case:
symptom, codes, observations, ranked test plan. A pass and a fail, and
the plan re-ranks live with the evidence trail naming what changed it.
A decline card, professional, with a next step. Close.

The rule for all future work: every work order from here is judged
against that spine. Does it play beautifully? Does it work flawlessly?
Does it take the fewest taps? A yes on all three is the bar.

The video shows only event-built features. Anything on the roadmap —
garage, 3D, watcher, exchange — is spoken as what is next, never shown
as if it already exists.

The submission itself: the demo video is submitted as a URL link and
the repository as a public URL. Both are required.

## The Bay side (Work Order 2)

The Bay tab on the same page serves the shop's daily driver: structured
cases, ranked test plans, and labor math, all in plain words.

1. **Bay intake** — a VIN photo fills the blanks (read by Spark, kept in
   session memory only, never written to disk) or manual entry. Year, make,
   model, category; trim stays unknown unless a badge is readable. Symptom
   kept verbatim, fault codes as a list, observations, area, and the
   service asked for. Decline policies gate intake: the shop does no engine
   work on one BMW V8 generation it names in config (a no-start counts as
   potentially engine-related) and no oil changes — matches render a
   professional decline card with a next step instead of a plan, never an
   error.
2. **Test-plan engine** — symptom plus codes produce ranked tests stating
   what to check, how (Autel MK908 or by hand — never PIWIS), what to
   expect, and a pass/fail input. Every test shows its score breakdown, so
   the ranking is visible. The shop can reorder, edit, and add tests.
3. **Live re-ranking** — each pass/fail result rules causes out or raises
   suspicion, re-ranks the pending tests, and appends an evidence-trail
   entry naming exactly what changed and why.
4. **Job parts list** — shop-entered entries with sources, plain words.
   No bundled catalog, no invented numbers or prices.
5. **Labor math** — plan steps at $180/hr from shop standards or shop-set
   estimates only. Steps with no time on file are named, not guessed.
6. **Repair notes on demand** — anonymized samples plus the owner's local
   `shop_kb/` files (that slot ships empty and stays git-ignored). No
   factory content anywhere.

Demo cases (anonymized samples, verified portions only): the silent module
(2009 coupe, harness proven by hand, module condemned on evidence,
matched-set fix with exact index match), the fluid fix (2014 coupe,
clutch-circuit oil only, flawless hot drive; final creep/rescan gates
left open, never claimed), and the cylinder that followed (diesel SUV,
+3.02 mg/stroke stays on cylinder 4 after the injector swap).

## First-run identity + enthusiast inventory (Work Order 3)

On the very first open, and only then, one setup question: shop or
enthusiast, plus an email. The answer persists in a local-only browser
profile that is never sent anywhere; later opens route by it (shops open
the Bay, enthusiasts open the Inventory), and mode changes happen only as
a deliberate settings action. The same page serves phone and PC browsers.

The Inventory tab organizes an enthusiast's cars and parts: register each
car by picture, VIN photo, or hand entry; attach parts with honest
condition, an owner note, and a value that is comps-sourced or
owner-entered (unsourced values stay unknown and out of the totals);
per-car what-to-look-for notes from owner knowledge (silence when none
exists — desirability is never invented); plain-money totals. Selling is
a deliberate second step: any part can feed the unchanged listing draft
behind the Approve gate, still mock-post only. Demo seed: a driver plus
two 3-series parts cars and a mid-90s M3 parts car with the owner's
engine-computer note, all anonymized samples.

## Graphical pass + VIN experience (Work Order 4)

The page went photo-first with no new dependencies: the walk-around is a
strip in order with a large viewer carrying the masks and boxes; every
part entry has a cutout thumbnail linking to its source frame; verdict
cards show cutouts; A/B totals are distinct visual cards above the
plain-words text; the Bay plan is a checklist with a progress bar and big
pass/fail states; inventory cards carry owner photos (local only) or a
placeholder. Demo frames wear a DEMO badge; user photos never become demo
samples and never leave the machine in demo.

The VIN flow is complete as an experience and demo-only as a data source:
capture a plate photo, see the plate, get a vehicle card (year, make,
model, category, honest trim), confirm or edit into Bay intake or
inventory registration. The VIN itself is never shown, never stored, and
stripped before every disk write. Live Spark reads stay behind the
`VIN_LIVE` switch in `bay.py`, which is off until the owner confirms the
API key rotation — flipping it later changes the data source, not the
interface. No fake VIN artifact exists anywhere, because a sample VIN
could collide with a real one.

## Usability pass (Work Order 5)

No new features: everything already built, made effortless. Sticky
navigation with mode homes (Bay home: case status plus New case and
Knowledge base; Inventory home: counts plus Register and Add part);
guided first tasks per mode that check off inside the real flows and
never reappear after dismissal; big thumb-sized primary actions and a
large, separated Approve; a working bar that always says what is
happening; an offline banner when the page falls back to demo cache
(plus a settings switch to force offline demo); every empty view with a
titled next action; DEMO badges on every demo-backed view; drafts that
survive reloads (browser only); deletes and draft-discards behind one
plain confirmation; model names kept inside the expandable tool detail;
and a mobile panel with an obvious open and close.

## Valuation engine + money grade (Work Order 8)

Comps grew from a sample board into a real engine, built fresh from a
plain-words study of valuation patterns. Sold prices in get a
median-centered range with width from the data's own spread, net money
after a visible 13.25% fee share, and an advisory money grade with a
plain-words reason. Thin feeds (fewer than 3 solds), stale solds (older
than 400 days), and contradictory spans (3x or more) are named in notes,
never smoothed over; empty feeds yield no range at all. Shop-typed
ranges revalue through the same engine at merge time, and the demo board
carries per-part sold lists behind the same lows and highs the totals
have always used. The money grade sits beside the rule grade on every
verdict card; `rules.json` is untouched and remains the single grading
authority. No live eBay lookup, no scraping, no remembered prices.

## Hybrid architecture

Two model families power this build, split on purpose. Muse Spark 1.3
through the Meta Model API powers the core reasoning: intake, grounding,
verdict inputs, listing drafts, chat. Muse Spark Open, the open-weight
model, runs through Baseten as the Compare stage: after verdicts, the
same case re-grades through Spark Open side by side with the Spark 1.3
demo leg, each result labeled by its engine, in the running app under
the Compare tab. The eval harness compares the legs on the demo set;
the Compare view is where the open model actually runs.

What runs live today, and what waits:

- Spark Open via Baseten: live when `BASETEN_API_KEY` is present in the
  local environment, one call per case, demo sample otherwise.
- Every Meta leg (Spark 1.3, SAM, Image, Voice, Wonder): demo cache
  until the Meta key rotation is confirmed.
- Spark Open demo sample and the Spark 1.3 demo leg: always available,
  always labeled, so the Compare view runs 10 out of 10 with no keys.

The demo beat for the Compare stage: open a graded case, open Compare,
read the on-screen label naming Muse Spark Open and Baseten, and narrate
how and where the open model is used — second-look grading after
verdicts, beside the rule grade, never an overrule. The video shows it,
this section states it, and the submission points at both.

## Run it

No dependencies — standard library only.

    python server.py
    # open http://127.0.0.1:8765 in a browser

The Meta Model API key lives in the local `.env` file (see `.env.example`)
and is never committed, and the Baseten key (`BASETEN_API_KEY`) lives there
too when present. With no key, no network, or no credits, every step
falls back to the demo-mode cache and the flow still runs end to end.

## The flow (one web page, five steps)

1. **Intake** — upload car photos or load the demo car (anonymized Yard
   Case 4: a mid-2000s 3-series parts car). Muse Spark 1.3 identifies the car
   — year, make, model, trim only as far as the photo honestly supports —
   and grounds each money part it can see on a 0–1000 grid.
2. **Harvest map** — SAM 3.1 masks each grounded part and tracks it across
   the walk-around frames; Spark counts repeated parts. Every entry carries
   the frame it came from.
3. **Verdicts** — each part gets A (pull and list now), B (worth it if you
   are standing there), or C (leave it) from the rules in `rules.json`,
   shown next to every grade with all rule inputs. One-tap override; your
   call feeds back into the totals.
4. **Plain-money totals** — A parts and B parts added separately, in plain
   words: the sure money and the maybe money. Shop-side math uses $180/hr.
5. **Listing draft** — honest draft with flaws stated, cutout preview, then
   Edit / Approve / Post. Nothing posts without Approve, and this build
   posts only to a local mock outbox — nothing leaves the machine.

The right-hand **Shop Copilot** panel holds the chat thread (Spark with
streaming, case-file answers when offline), starter chips, and a
plain-language activity feed where every step expands to show the tool call
behind it.

## Rules that govern this build

- **Never guess.** Every fact is looked up and source-tagged, or the
  software says it lacks reliable data. No invented part numbers, prices,
  torque values, or labor times. Prices without a source are ignored.
- **Fresh, event-built code only.** No factory manual content, no real
  customer data, no real VINs, no shop street address (Gulf Coast only),
  no secrets in the repo.
- **Demo runs 10 out of 10.** Cache behind every step: intake, harvest,
  comps, listing, chat. Verify with `python scripts/smoke_demo.py` while
  the server runs (10 full runs by default).
- **One working flow.** Garage, 3D explorer, marketplace watcher, and parts
  exchange are roadmap, not this build. The pipeline is staged
  (photo → facts → verdict → artifact) so they arrive as later steps.

## Approach notes (what changed vs the brief, and why)

- **No live eBay sold comps.** The brief wants verdict inputs from real
  SOLD listings; without eBay credentials on hand, a live lookup would be a
  remembered price wearing a costume. So comps ship as an isolated adapter
  plus a fresh valuation engine: shop-typed ranges and the tagged demo sold
  board run through median-centered ranges, net-after-fees money, and an
  advisory money grade. A live eBay adapter stays a stub marked later step.
- **Studio backgrounds shipped demo-safe.** The listing card shows a studio photo above the cutout preview
  and falls back to the cutout whenever the studio step is unavailable, so the
  card never breaks. Live Muse Image waits on the Meta key rotation.
- **Voice notes, Wonder router shipped demo-safe.** Push-to-talk
  transcription lands text on a Bay case or an inventory note (text only,
  no voice loop); hard verdicts and plans get a visible Wonder Standard
  second opinion that never overwrites the primary call. Both live legs
  wait on the Meta key rotation. The eval lab harness below compares all
  four engines on the demo set.

- **Decline renderer ships early.** The verdict engine can already render a
  professional decline as a verdict card (never an error), covered by
  tests — the shop side reuses it next work order.

## Layout

- `server.py` — stdlib HTTP server: static page + JSON/SSE API, sessions.
- `meta_client.py` — Meta Model API adapter (Spark 1.3, SAM 3.1).
- `bay.py` — Bay engine: intake validation, decline gate, plan scoring and
  re-ranking, parts, labor math, local knowledge-base slot.
- `shop_kb/` — local repair-note slot (ships empty, content git-ignored).
- `verdict.py` + `rules.json` — visible, changeable A/B/C rules + totals.
- `comps.py` — valuation engine (ranges, nets, advisory money grade) plus
  the mock adapter feed; the live eBay adapter stays a stub.
- `listing.py` — drafts + mock post outbox.
- `studio.py`, `voice.py`, `wonder.py` — Image studio, voice notes, and the
  Wonder second-opinion router; isolated adapters, live flags off.
- `spark_open.py` — Spark Open via Baseten for the Compare stage; live when
  `BASETEN_API_KEY` is present, demo sample otherwise.
- `scripts/eval_lab.py` — offline harness comparing all four engines; its
  table below regenerates with `--write-readme`.
- `demo_cache.py` + `demo_cache/*.demo.json` — cache behind every step.
- `web/` — the one page (`index.html`, `app.js`, `profile.js`,
  `inventory.js`, `styles.css`) + sample frames.
- `inventory.py` + `demo_cache/inv_seed.demo.json` — demo seed, photo ID
  help, and comps value lookups (inventory data itself stays in the browser).
- `web/gallery.js` — pure strip/viewer model behind the photo gallery.
- `web/ux.js` — pure usability logic: drafts, guides, empty states, deletes.
- `tests/` — Python suites plus a Node driver for the browser logic
  (`tests/test_web_logic.py` runs it; Node is a test dependency).
  `scripts/smoke_demo.py` — 10× end-to-end over Yard, Bay, and inventory.

<!-- EVAL-LAB:START -->
## Eval lab

The same anonymized demo set through each engine. Demo legs are measured below; live legs are flagged off with exactly what would run them. Regenerate with `python scripts/eval_lab.py --write-readme`.

| engine | cases | grounding | agreement | cost | latency | status |
| --- | --- | --- | --- | --- | --- | --- |
| muse-spark-1.3 (demo leg) | 7 yard parts + intake | 7/7 boxes valid | 7/7 owner grades; bay order match, top score match | $0.00 (demo) | 2 ms (sampled) | live blocked: needs Meta key rotation confirmed |
| wonder-standard (demo leg) | 7 verdicts routed | n/a (reviewer, not grounder) | 7/7 router outcomes | $0.00 (demo) | shares the run above | live blocked: needs Meta key rotation confirmed |
| muse-spark-open-1026 | same demo set, when live | — | — | — | — | blocked: needs BASETEN_API_KEY in the local environment (endpoint https://inference.baseten.co/v1, model meta-models/muse-spark-open-1026) |
| glimmer | same demo set, when live | — | — | — | — | blocked: needs a confirmed hosted endpoint (GLIMMER_ENDPOINT); will not run local on a 12GB card |

- Meta key names checked (META_API_KEY, MODEL_API_KEY): present.
- BASETEN_API_KEY: missing.
- GLIMMER_ENDPOINT: unset, endpoint unconfirmed.
- Key names only were read; no values were printed or logged.
<!-- EVAL-LAB:END -->
