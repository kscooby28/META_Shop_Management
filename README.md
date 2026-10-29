# Shop AI Copilot

Shop software built for the Meta AI Hackathon. Point your phone at any car —
and know what it is, what it is worth, and what to do next.

For a repair shop, it is the repair bench: describe a symptom, get a
ranked test plan, record pass or fail. For a car enthusiast with parts
cars, it is the lot: photograph a car, learn which parts are worth
pulling and what they will sell for. Both sides share one brain that
never guesses — every claim carries its source, or the software says
it lacks reliable data.

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
runs in this repo, end to end, on demo cache, with zero keys.


The video spine, one continuous journey: first-run setup, one question,
shop or enthusiast. Enthusiast home. Register a parts car by photo and
VIN, confirm, done. The what-to-look-for moment: the mid-90s M3 parts
car surfaces the engine computer, no EWS, the E30 crowd wants it, $200.
Inventory with plain-money totals. A listing draft behind the Approve
gate — nothing posts without a human saying so. Shop home. A Bay case:
symptom, codes, observations, ranked test plan. A pass and a fail, and
the plan re-ranks live with the evidence trail naming what changed it.
A decline card, professional, with a next step. Then the Compare beat:
both engines side by side on the same case, Muse Spark Open named on
screen with where it runs. Close.

The guided tour walks these beats in order: a Take the tour entry on
both home screens, ten taps, no hunting, no keys, every beat on demo
cache including a forced-demo Compare. It is the recording path and
the stranger's first-run path in one.

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
plain-words reason, the sold count, and the reliability notes beside
it. Thin feeds (fewer than 3 solds), stale solds (older
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

## Credentials + auto-post, the mechanism (Work Order 15)

Settings holds two credential profiles, and the software does more
once a person adds their own. The shop tier holds a distributor or
warehouse login plus an email API credential, for live retailer
quotes and estimate emails. The DIY tier holds a local parts-store
login, in the shape of an AutoZone or O'Reilly website login, for
price checks, plus marketplace accounts including an eBay Developer
API slot, for posting. Every credential lives in the browser only,
next to the first-run profile: never sent to the server, never
logged, never committed, and the interface shows presence only, set
or not set, never the value.

The eBay auto-post loop is: picture, analyze the part, value it
against new and used, draft, the human Approve tap, then the API
posts — draft to listing to the cha-ching sale notification. What
the user provides for live posting is their eBay developer key plus
their eBay account authorization, and the adapter posts the
approved draft through the API. Automatic means the API does the
posting work, no manual listing on ebay.com — never post without
approval. Nothing posts without the human tap, ever. This order
ships the door plus the mock demo behind it: mock distributor and
store logins and a mock marketplace post in the real API shape, all
labeled demo. Live integrations come one at a time after this, each
on the user's own account with the platform rules sorted first.
Facebook Marketplace posting stays vision-only: named as roadmap,
never built here, because its platform rules and the
personal-profile line need resolving before any real build. The
eBay side is the user's own account posting plus the existing
comps engine — never scraped sold data, never remembered prices.

## Run it

No dependencies — standard library only. You need Python 3.10 or newer
and a browser. No keys, no signup, nothing else: the demo runs on cache.

    git clone https://github.com/kscooby28/META_Shop_Management
    cd META_Shop_Management
    python server.py
    # open http://127.0.0.1:8765 in a browser

A working page shows four tabs — Yard, Bay, Inventory, Compare — and, on
the very first open, one question: shop or enthusiast. Answer it and the
demo flows run end to end.

Keys are optional. The Meta Model API key lives in the local `.env` file
(see `.env.example`) and is never committed, and the Baseten key
(`BASETEN_API_KEY`) lives there too when present. With no key, no
network, or no credits, every step
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
   shown next to every grade with all rule inputs, plus an advisory money
   grade from the comps engine beside it. One-tap override; your
   call feeds back into the totals.
4. **Plain-money totals** — A parts and B parts added separately, in plain
   words: the sure money and the maybe money. Shop-side math uses $180/hr.
5. **Listing draft** — honest draft with flaws stated, studio photo over the
   cutout preview (cutout stays as the fallback), then
   Edit / Approve / Post. Nothing posts without Approve, and this build
   posts only to a local mock outbox — nothing leaves the machine.

The right-hand **Shop Copilot** panel holds the chat thread (Spark with
streaming, case-file answers when offline), starter chips, and a
plain-language activity feed where every step expands to show the tool call
behind it.

## Glossary (only what the demo shows)

- **Verdict** — the app's answer to pull it or leave it, with the money
  beside it. **A** means pull and list now, **B** means worth it if you
  are standing there, **C** means leave it.
- **Comp** — one comparable sale: what the same part actually sold for,
  with its source. The plural **comps** is the pile the price range is
  built from.
- **Money grade** — the comps engine's own A/B/C on the money alone,
  shown beside the rule grade. Advisory, never an overrule.
- **Re-rank** — the test plan resorting itself as pass/fail results come
  in, with the evidence trail naming what changed it.
- **Second look** (Compare) — both engines re-grading the same case side
  by side. **Second opinion** (Bay/Yard) — one hard call reviewed by
  Wonder Standard. Different stages, different names on purpose.
- **Studio photo** — the cleaned listing shot; **cutout** is the raw crop
  it falls back to. **Mock outbox** — the on-machine outbox demo posts
  land in; nothing ever leaves the machine from it.
- **DEMO badge** — this number came from the built-in sample set, not a
  live call. No badge, no sample: live results never wear it.
- **VIN** — the car's ID plate; a photo of it fills in year, make, model.
- **EWS** — the car's factory immobilizer. The demo's engine computer
  needs no EWS handshake, which is why **E30** owners — keepers of the
  1980s–early-90s 3-series — want it.

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
  tests — the shop side reuses it in the Bay.

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
- `scripts/eval_scale.py` + `eval_scale_results.json` — Work Order 13 live
  measurement: every demo case through the rules engine and Spark Open
  live, with the matching README table beside the eval-lab table.
- `yard_photos.py` — folder contract for the full-yard follow-up
  (the owner stages `yard-photos/` later; the slot stays empty and ignored).
- `demo_cache.py` + `demo_cache/*.demo.json` — cache behind every step.
- `web/` — the one page (`index.html`, `app.js`, `profile.js`,
  `inventory.js`, `styles.css`) + sample frames.
- `inventory.py` + `demo_cache/inv_seed.demo.json` — demo seed, photo ID
  help, and comps value lookups (inventory data itself stays in the browser).
- `web/gallery.js` — pure strip/viewer model behind the photo gallery.
- `web/ux.js` — pure usability logic: drafts, guides, empty states, deletes.
- `web/credentials.js` — local-only credential profiles plus the mock
  distributor, store, and marketplace adapters (all demo, no network).
- Guided tour (Work Order 12) — the Take the tour entry on both home
  screens walks the video spine beats in order on demo cache.
- `tests/` — Python suites plus a Node driver for the browser logic
  (`tests/test_web_logic.py` runs it; Node is a test dependency).
  `scripts/smoke_demo.py` — 10× end-to-end over Yard, Bay, and inventory.

<!-- EVAL-LAB:START -->
## Eval lab

The same anonymized demo set through each engine. Demo legs are measured below; live legs are flagged off with exactly what would run them. Regenerate with `python scripts/eval_lab.py --write-readme`.

| engine | cases | grounding | agreement | cost | latency | status |
| --- | --- | --- | --- | --- | --- | --- |
| muse-spark-1.3 (demo leg) | 7 yard parts + intake | 7/7 boxes valid | 7/7 owner grades; bay order match, top score match | $0.00 (demo) | 0 ms (sampled) | live blocked: needs Meta key rotation confirmed |
| wonder-standard (demo leg) | 7 verdicts routed | n/a (reviewer, not grounder) | 7/7 router outcomes | $0.00 (demo) | shares the run above | live blocked: needs Meta key rotation confirmed |
| muse-spark-open-1026 | same demo set, when live | — | — | — | — | blocked: needs BASETEN_API_KEY in the local environment (endpoint https://inference.baseten.co/v1, model meta-models/muse-spark-open-1026) |
| glimmer | same demo set, when live | — | — | — | — | blocked: needs a confirmed hosted endpoint (GLIMMER_ENDPOINT); will not run local on a 12GB card |

- Meta key names checked (META_API_KEY, MODEL_API_KEY): present.
- BASETEN_API_KEY: present.
- GLIMMER_ENDPOINT: unset, endpoint unconfirmed.
- Key names only were read; no values were printed or logged.
<!-- EVAL-LAB:END -->

<!-- EVAL-SCALE:START -->
## Live evaluation at scale (Work Order 13)

Every demo case through both engines: the deterministic rules grade
and the Muse Spark Open live grade side by side, one live Baseten
call per case, no retries. Spark Open ran live because its key is
present and proven; Spark 1.3, SAM, Image, Voice, and Wonder stayed
on demo because the Meta key rotation is still unconfirmed. Bay job
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
