# Shop AI Copilot

Shop software built for the Meta AI Hackathon. Point your phone at any car —
and know what it is, what it is worth, and what to do next.

This repo ships the foundation plus the enthusiast (Yard) side's first flow:
photo in, car identified, harvest map with masks, A/B/C verdicts with visible
rules, plain-money totals, and a listing draft behind the Approve gate. The
shop-manager core (the Bay) comes next as a second work order.

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
- `verdict.py` + `rules.json` — visible, changeable A/B/C rules + totals.
- `comps.py` — sold-comp adapters (mock ships; real one slots in).
- `listing.py` — drafts + mock post outbox.
- `demo_cache.py` + `demo_cache/*.demo.json` — cache behind every step.
- `web/` — the one page (`index.html`, `app.js`, `styles.css`) + sample frames.
- `tests/` — verdict engine tests. `scripts/smoke_demo.py` — 10× end-to-end.
