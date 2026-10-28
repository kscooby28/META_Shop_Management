# Shop knowledge base (local slot, ships empty)

This folder is where the owner's shop keeps its own repair notes for the Bay
side: test tips, known-good readings, and lessons from finished cases.

- Files here are read only by a demo running in the owner's shop.
- Nothing in this folder ships inside the submission except this README:
  `shop_kb/*.json` is git-ignored.
- Format: one JSON note (or a list of notes) per file:
  `{"title": "...", "body": "..."}`.
- Every note served from here is source-tagged with its file name.
- Never put factory manual content, customer names, VINs, phone numbers,
  addresses, or personal data in these files.
