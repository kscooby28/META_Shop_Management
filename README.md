# Shop AI Copilot

I own a BMW performance shop. I built the assistant I wanted in my pocket:
one page that photographs a parts car and tells me what to pull, what it
will sell for, and what to do next — and that runs my repair bench the
same way, symptom to ranked tests to done. Built for the Meta Global AI
Developer Hackathon theme Build for Your World: a working shop owner's
daily driver, not a demo toy. Every claim carries its source, or the app
says it lacks reliable data.

## Demo video

Demo video (3 minutes max): VIDEO_URL

Watch the guided tour path: Take the tour on either home screen walks
eight taps — setup, register, knowledge, money, trust, re-rank, decline,
Compare — fully on demo cache including a forced-demo Compare, so it
plays with zero keys. Shot list and checklist: [docs/video-plan.md](docs/video-plan.md).

Screenshots: pending owner capture before submission (no secrets needed,
just the running app). Planned shots, into `docs/img/`:

- `docs/img/tour-money.png` — money grade beside rule grade (tour beat 4)
- `docs/img/compare.png` — Compare second look with the recorded live row
- `docs/img/bay-plan.png` — Bay plan with the evidence trail after pass/fail

## What it does

| Shop — fix it | DIY Garage — your cars and parts |
| --- | --- |
| Symptom plus codes in, ranked test plan out | Cars plus parts in, A/B/C verdicts out |
| Pass/fail re-ranks live with an evidence trail naming what changed | Every grade shows its rule plus an advisory money grade |
| Policy decline renders a professional card with a next step | Listing drafts sit behind the Approve gate: nothing posts without the human tap |
| Labor math at the $180/hr shop rate, unknowns named not guessed | Plain-money totals: sure money and maybe money, stated separately |

## How Meta models are used

With no keys, no network, or no credits, every leg serves the demo cache:
this demo build runs end to end on samples, every cached result wearing a
DEMO badge and no live result ever wearing one. Proven legs go
live when keys are present (`SHOP_DEMO=1` or the Settings
"Force offline demo" switch forces the cache). Full receipts:
[docs/evals.md](docs/evals.md).

| model | job | file | verified live status |
| --- | --- | --- | --- |
| Muse Spark 1.3 | photo identify plus 0-1000 grounding, Bay test plans, listing drafts, Copilot chat | `meta_client.py`, `server.py` | Live when keys are present. Verified: live identify plus pooled eval grades 22/30 |
| Muse Spark Open on Baseten | second-look grader in Compare (yard and inventory) | `spark_open.py`, `server.py` | Live when `BASETEN_API_KEY` is present. Verified: live grades including the recorded 19603 ms inventory run |
| Muse Wonder Standard | second opinion on hard yard verdicts and Bay plans | `wonder.py`, `server.py` | Live when keys are present (`muse-wonder-1.0` over `/chat/completions`). Verified: 4 live eval opinions |
| Muse Image | build-time scene and part art; listing studio photo | `studio.py`, `server.py` | 33 renders proven (`muse-image-1.0` over `/responses`). Studio image-edit stays demo: live shape unverified, client sends no cutout bytes |
| SAM 3.1 | attempted segmentation | `meta_client.py` (adapter kept as a documented attempt) | Not live: 4 probes, zero geometry. Demo cache stands in for SAM; the live harvest uses Spark grounding boxes |
| Voice Transcribe | Bay and inventory voice notes | `voice.py`, `server.py` | Off: no confirmed model id, zero live calls. Tour narration is build-time Piper TTS, unrelated |
| VIN plate read (Spark) | Bay and inventory VIN fill | `bay.py`, `server.py` | Off: no plate image tested, privacy line holds — the VIN is never shown or stored |

Pipeline, one line: photo → facts → rules verdict → model second look → human gate.

## Why it isn't a chatbot or an image analyzer

- Deterministic rules decide: `rules.json` grades every part A, B, or C,
  and the rule it used is shown on each card. No photo-in-answer-out.
- Models propose and second-look: Spark identifies, grounds, drafts, and
  chats; Spark Open re-grades beside the rule grade, never overruling it;
  Wonder reviews hard calls beside the primary call.
- Evidence trail plus never-guess contract: every re-rank names what
  changed and why; unsourced prices stay unknown and out of the totals.
- Human gate: drafts post only to a local mock outbox, and only after the
  Approve tap. Nothing posts without the human tap, ever.
- House rules hold: no region naming, no secrets, no VINs, no customer
  data, no shop address in the repo; standard library only.

## Quickstart

No keys, no signup: standard library only, Python 3.10 or newer, plus a
browser. No dependencies to install.

    git clone https://github.com/kscooby28/META_Shop_Management
    cd META_Shop_Management
    python server.py
    # macOS and Linux say python3 instead of python
    # open http://127.0.0.1:8765 in a browser
    # a phone on the same Wi-Fi uses python server.py
    # --host=0.0.0.0, then http://<this-pc-ip>:8765 on the phone

A working page shows two doors — Shop and DIY Garage, with Compare under
the DIY Garage — and, on the very first open, one question: shop or
DIY Garage. Answer it and the demo flows run end to end.

Live mode: copy `.env.example` to `.env` and add `META_API_KEY` (plus
`BASETEN_API_KEY` for the Spark Open second look). Proven legs go live
when keys are present; Settings shows the per-leg "Live models" line.
`SHOP_DEMO=1` or the Settings "Force offline demo" switch forces the
demo cache without touching keys. Never commit the real `.env`.

Verify a cold clone two ways: `python -m unittest` runs the suite (the
five browser suites need Node.js installed), and with the server running,
`python scripts/smoke_demo.py` replays ten demo flows against it.
Run the smoke test against a server with no keys (no .env), e.g. a clean checkout.

## Built during the event

Built October 26 to November 4 for the Meta Global AI Developer
Hackathon; first commit October 26. Open source under the MIT license —
see [LICENSE](LICENSE) (copyright kscooby28).

Contributors (every author in git history):

- kscooby28 — owner, BMW performance-shop owner; everything except the
  commit below.
- Muse (`Muse <muse@local>`) — commit `78931ba`: two-door restructure,
  self-playing tour with rendered voiceover, and craft polish.

Build tools, stated plainly: the `78931ba` commit above was authored by
Muse, and the WO22 submission hardening (tour repair, live-when-keys
legs, this README) was implemented with Muse Code.

Attribution: the guided-tour narration MP3s (`web/assets/audio/tour-*.mp3`)
were rendered at build time with Piper (`en_US-libritts-high`), a voice
model trained on the LibriTTS dataset (CC BY 4.0). The per-beat manifest
lives in `eval_voice_results.json`. Tour voice is pre-rendered audio, not
a Meta model call.

Work-order history: [docs/build-log.md](docs/build-log.md). Model
measurements: [docs/evals.md](docs/evals.md). Video shot plan:
[docs/video-plan.md](docs/video-plan.md).
