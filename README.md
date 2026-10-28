# Shop AI Copilot

Shop software built for the Meta AI Hackathon. Point your phone at any car —
and know what it is, what it is worth, and what to do next.

This repo ships the foundation plus the enthusiast (Yard) side's first flow:
photo in, car identified, harvest map with masks, A/B/C verdicts with visible
rules, plain-money totals, and a listing draft behind the Approve gate. The
shop-manager core (the Bay) shipped as Work Order 2 on the same scaffold.

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

## Run it

No dependencies — standard library only.

    python server.py
    # open http://127.0.0.1:8765 in a browser

The Meta Model API key lives in the local `.env` file (see `.env.example`)
and is never committed. With no key, no network, or no credits, every step
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

- **No live eBay sold comps yet.** The brief wants verdict inputs from real
  SOLD listings; without eBay credentials on hand, a live lookup would be a
  remembered price wearing a costume. So comps ship as an isolated adapter:
  the mock returns the tagged sample board in demo mode and honest
  "no reliable data" in live mode. Shop-typed comps (source-tagged) work
  today; the real adapter slots into `comps.py` later.
- **Studio backgrounds deferred.** The listing card crops a cutout preview
  from the source frame; Muse Image backgrounds stay a later step per the
  short work order.
- **Voice notes, Wonder router, eval lab deferred** per the short work
  order. They are pipeline stages with cache slots waiting, not rewrites.
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
- `comps.py` — sold-comp adapters (mock ships; real one slots in).
- `listing.py` — drafts + mock post outbox.
- `demo_cache.py` + `demo_cache/*.demo.json` — cache behind every step.
- `web/` — the one page (`index.html`, `app.js`, `styles.css`) + sample frames.
- `tests/` — verdict engine tests. `scripts/smoke_demo.py` — 10× end-to-end.
