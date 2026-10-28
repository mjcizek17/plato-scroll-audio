# Render queue order (2026-10-23, user's priority)

1. **Laws re-recording** — run 39994491897 (laws → audio-v1, laws-b → jowett-v1, epin → audio-v1): the Athenian Stranger now speaks with Socrates' voice. This run must have the runners to itself.
2. Plutarch & Platonists C–F (render/next/queue-C..F.json) — re-queue **one at a time, only after the Laws run has published**. Their earlier runs were cancelled on purpose: GitHub spread the few runners it grants across all queued runs and starved the Laws.

Please don't re-run ("Re-run all jobs") a produce run that has finished shards — it discards them (attempt 2 of the Laws lost 27 finished shards). To repair failed shards use ranges + reuse_run in render/queue.json instead.

## 2026-10-27 evening — figures and section numbers (user's request: "stop all recordings and fix this")
- The voices misread figures ("478" → "578", "186 B.C." → "eighteen-six"). From now on every figure is written out in words
  before it is spoken (text/numbers.py, via text/notes.py plan()), and bare page / chapter / section / verse numbers
  (Plutarch's "596 1 1", ".” 2 But…", the Golden Verses' line numbers) are not read at all.
- render/queue.json is now the repair: re-record the 823 paragraphs with figures in 80 published works (patch mode, ~14 h
  of audio) and splice them in. The Seneca batch (queue G) was cancelled for it and saved as render/next/queue-G-stoics.json —
  re-queue it after the repair run has published. Then run slice-notes on every published work (render/slice.json) to cut
  the spoken section numbers out of the paragraphs that were not re-recorded.
- The user dislikes the "Narrator" voice (cast/refs/narrator.wav: Hesiod, Xenophanes and 22 other works). Do not record
  any new work with it; a replacement is being auditioned.
