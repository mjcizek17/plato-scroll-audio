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

## 2026-10-27 night — nothing renders until the user has approved the speech rules
- The user: "Let's perfect the audio before doing any more renders — think of all the things that can go wrong."
  Every run was cancelled (produce 48 = the figures repair, slice-notes, audition-voice). Nothing is queued; render/queue.json
  still holds the repair patch and will be pushed again, recomputed, when he says go.
- The produce workflow now stops itself before any rendering if anything in the queue is unsafe to read:
  tests/test_speech.py (the rules) and tools/speech_gate.py (count mismatches, figures left to a voice, the retired
  Narrator clip, uncast speakers). Run both locally before pushing a queue.
- Chatterbox takes whose forced alignment scores poorly (a dropped or garbled clause at a plausible length) are re-taken
  once (HV_ALIGN_MIN, engines/chatterbox_lines.py) and flagged in the assemble report.
- 13 of the 80 works in the repair queue are read by the retired Narrator clip (24 whole works, 25.5 h in all); the gate
  refuses to patch them in that voice. They need a new reader and a full re-record — the user chooses the voice from the
  Orphic Theogony audition (audition/old-reader.json) first.
