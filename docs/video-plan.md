# Demo video plan (3:00 max)

Recording path for video day. Every shot is real screen recording of
this repo plus the owner's real B-roll. No fake UI, no rendered car
presented as app output, no capability the app lacks.

## Shots in record order (180 seconds)

0. Intro snap-cut. The locked 10-second intro ends on the shutter
   snap; cut on that sound straight into the app landing below.
1. Door tap + first-run setup (~15s). Open on the street landing.
   Tap the shop or garage half. Answer the one first-run question.
2. Photo demo to result screen (~30s). Register a parts car by photo
   and VIN, confirm, land on the result screen.
3. Tap Take the tour; the 8 beats self-play (~75-110s). Beats advance
   on their own with pre-rendered voice; captions match the narration.
   Beat holds: chooser 9s, register 11s, knowledge 13s, money 10s,
   trust 12s, rerank 13s, decline 9s, compare 22s (muted holds total
   99s; voice-on advances on audio end plus 1.2s).
4. Manual outro close (~10s). The tour ends at Compare by design, so
   the outro is spoken over the sunset wide shot, not a 9th beat:
   "I own a BMW performance shop. I built the assistant I wanted in
   my pocket. Shop AI Copilot." Repo URL on screen.

## Pre-roll checklist

- Clear site data or set localStorage `tour.muted` to 0, and confirm
  the movie bar reads Mute voice: a muted rehearsal records silent.
- Flip Force offline demo in Settings before shot 2: a real photo
  otherwise attempts live identify, which is not deterministic.
- Seed the demo data; run the tour once as a timed dry run and keep
  the full take under 180 seconds.
- The Approve gate stays visible and unpressed on camera (trust beat);
  the mock cha-ching beat is the one tap the video shows.
- N63 stays off camera (tour uses the oil-change decline beat). No
  customer cars, customer data, or shop street address on camera.
- Live Compare is one honest take: start the call, cut to titles and
  B-roll, cut back to the result. Never hold on a live wait.

## Voice

Tour beats carry their own pre-rendered narration
(`web/assets/audio/tour-*.mp3`, Piper en_US-libritts-high, LibriTTS
CC BY 4.0). The video voiceover over B-roll and the outro follows the
Nov 2 office-hours narrator decision; it never claims a real sale and
never claims Meta text-to-speech.
