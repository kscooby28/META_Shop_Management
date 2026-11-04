# Build log

Work-order history moved here from the README in WO22 P3, so the README
speaks to a judge in sixty seconds and this file keeps the receipts.
Run instructions live in the README Quickstart now; model measurements
live in [evals.md](evals.md).

## Reading notes (WO22 P3)

- Retired wording: measurement notes before WO22 P3 said demo legs waited
  on the "Meta key rotation". That phrase is retired: every leg is now
  described as live when keys are present, or off with its reason. The
  moved sections below carry the new wording.
- First-run email is optional since WO22 P1 (one tap finishes setup);
  the WO3 section below predates that change.
- Live flags since WO22 P2: the Wonder and Image flags are on (live when
  keys are present); Voice and VIN stay off. The "flags stay off" lines
  in the moved Hybrid, Layout, and Approach sections describe the pre-P2
  build; the README model table is current.
- Studio image-edit stays demo (WO22 2.6 gated: the live shape is
  unverified and the client sends no cutout bytes).
- Cite the pooled 22/30, never 0/0 (see [evals.md](evals.md)).

## Demo video first

The three-minute demo video is what the judges watch, and it is the
acceptance test for this build. Every feature must earn its minutes on
camera: if it does not play on video, it is not done.

Priority order: the video first, the functional repository second. The
repository exists to make the video true — everything shown on camera
runs in this repo, end to end, on demo cache, with zero keys.

The video spine, one continuous journey: first-run setup, one question,
shop or DIY Garage. DIY Garage home. Register a parts car by photo and
VIN, confirm, done. The what-to-look-for moment: the mid-90s M3 parts
car surfaces the engine computer, no EWS, the E30 crowd wants it, $200.
Plain-money totals with the money grade beside every rule grade. A
listing draft behind the Approve gate — nothing posts without a human
saying so. Shop home. A Bay case:
symptom, codes, observations, ranked test plan. A pass and a fail, and
the plan re-ranks live with the evidence trail naming what changed it.
A decline card, professional, with a next step. Then the Compare beat:
both engines side by side on the same case, Muse Spark Open named on
screen with where it runs. Close.

The guided tour walks these beats in order: a Take the tour entry on
both home screens, eight taps, no hunting, no keys, every beat on demo
cache including a forced-demo Compare. It is the recording path and
the stranger's first-run path in one.

The rule for all future work: every work order from here is judged
against that spine. Does it play beautifully? Does it work flawlessly?
Does it take the fewest taps? A yes on all three is the bar.

The video shows only event-built features. Anything on the roadmap —
3D, watcher, exchange — is spoken as what is next, never shown
as if it already exists.

The submission itself: the demo video is submitted as a URL link and
the repository as a public URL. Both are required.

Tour narration: the self-playing tour speaks eight pre-rendered
MP3s (`web/assets/audio/tour-*.mp3`, manifest in
`eval_voice_results.json`), rendered at build time with Piper
en_US-libritts-high (LibriTTS data, CC BY 4.0). No runtime
text-to-speech, no model call, and unrelated to the Muse Voice
Transcribe demo leg, which is speech-to-text microphone input.

## Two doors (restructure note)

Two doors, one page: Shop opens the Bay repair bench, DIY Garage opens
cars, parts, values, and selling. The photo flow that used to sit
behind the Yard door now runs as DIY Garage steps 5-10, and Compare
hangs under the DIY Garage. Every step still runs on the demo cache
with zero keys, and nothing posts without the human Approve tap.
The old roadmap garage item is delivered by the DIY Garage door, so the
roadmap lists name only what is still ahead.

## The Bay side (Work Order 2)

The Bay side on the same page serves the shop's daily driver: structured
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

The Inventory view organizes an enthusiast's cars and parts: register each
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
`VIN_LIVE` switch in `bay.py`, which is off (no plate image tested,
privacy line holds) — flipping it later changes the data source, not the
interface. No fake VIN artifact exists anywhere, because a sample VIN
could collide with a real one.

## Usability pass (Work Order 5)

No new features: everything already built, made effortless. Sticky
navigation with mode homes (Shop home: case status plus New case and
Knowledge base; DIY Garage home: counts plus Register and Add part);
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
the Compare view. The eval harness compares the legs on the demo set;
the Compare view is where the open model actually runs.

What runs live today, and what waits (pre-WO22 P2 wording; the README
model table is current):

- Spark Open via Baseten: live when `BASETEN_API_KEY` is present in the
  local environment, one call per case, demo sample otherwise.
- Every Meta leg (Spark 1.3, SAM, Image, Voice, Wonder): demo cache
  in this demo build. Spark and Wonder already proved live in the
  evals below (Spark 11/15, Wonder 4 live opinions); the flags stay
  off so the demo runs with zero keys.
- Reading the WO16 table: its "every Spark 1.3 grade matched" line
  covers 0/0 grades (the leg stopped on a timeout); the follow-up
  revived Spark at 11/15. Cite the pooled 22/30, never 0/0.
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

## The flow (one web page, five steps)

The photo flow runs in the DIY Garage view:

1. **Intake** — upload car photos or load the demo car (anonymized Yard
   Case 4: a mid-2000s 3-series parts car). Muse Spark 1.3 identifies the car
   — year, make, model, trim only as far as the photo honestly supports —
   and grounds each money part it can see on a 0–1000 grid.
2. **Harvest map** — demo cache stands in for SAM 3.1 here (the SAM live
   leg closed after four probes with zero geometry; see
   [docs/evals.md](evals.md)), masking each grounded part and tracking it
   across the walk-around frames; Spark counts repeated parts. Every entry
   carries the frame it came from.
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
  by side. **Second opinion** (Bay/DIY Garage) — one hard call reviewed by
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
  customer data, no real VINs, no shop street address, no region naming,
  no secrets in the repo.
- **Demo runs 10 out of 10.** Cache behind every step: intake, harvest,
  comps, listing, chat. Verify with `python scripts/smoke_demo.py` while
  the server runs (10 full runs by default).
- **One working flow.** 3D explorer, marketplace watcher, and parts
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
  card never breaks. Live Muse Image studio edit stays demo until a live
  image-edit verifies (WO22: armed, 2.6 gated).
- **Voice notes, Wonder router shipped demo-safe.** Push-to-talk
  transcription lands text on a Bay case or an inventory note (text only,
  no voice loop); hard verdicts and plans get a visible Wonder Standard
  second opinion that never overwrites the primary call. Wonder is live
  when keys are present (WO22 P2); Voice stays off (no confirmed model
  id). The eval lab harness in [docs/evals.md](evals.md) compares all
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
  Wonder second-opinion router; isolated adapters, live when keys are
  present (Voice stays off: no confirmed model id).
- `spark_open.py` — Spark Open via Baseten for the Compare stage; live when
  `BASETEN_API_KEY` is present, demo sample otherwise.
- `scripts/eval_lab.py` — offline harness comparing all four engines; its
  table in `docs/evals.md` regenerates with `--write-readme`.
- `scripts/eval_scale.py` + `eval_scale_results.json` — Work Order 13 live
  measurement: every demo case through the rules engine and Spark Open
  live, with the matching `docs/evals.md` table beside the eval-lab table.
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
- `docs/evals.md` — model measurements (WO22 P3 move); `docs/build-log.md`
  is this file; `docs/video-plan.md` — the 3-minute shot plan.
