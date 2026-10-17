# Plato Scroll Audio

Full-cast audiobooks of Plato in David Horan's translation, for the read-along feature in Plato Scroll.

## Standing decisions
- Horan's Plato, all 33 works; footnotes are not read.
- A distinct voice per speaker, the same voice for a character in every work. Socrates sounds like an older man, and no other character sounds like him.
- Age comes from the voice itself, never from slowing it down; everyone reads at an audiobook pace.
- In narrated dialogues the narrator character reads the narration (Socrates in Republic, Charmides, Protagoras, Euthydemus, Lysis; Phaedo in Phaedo; Apollodorus in Symposium; Cephalus in Parmenides).
- Opening line in one phrase: "Plato's Alcibiades One, translated by David Horan."
- Traditional English classicist pronunciation of names.

## Layout
```
audition/       the test passage (Alcibiades I) and the cast sheet used for engine auditions
engines/        one renderer per voice engine; each writes per-line WAVs + speed.json
tools/master.py studio-style assembly: trim, high-pass, gentle compression, room tone, pauses, -19 LUFS
.github/workflows/audition.yml   renders the audition with every engine and commits results to the `samples` branch
```

## Engine
Kokoro-82M (Apache-2.0), chosen after auditioning Qwen3-TTS and Chatterbox (Oct 2026). Each character reads
with his own accent's pronunciation (`cast/cast.json`), names come from `engines/lexicon.py`.

## Producing audio
Edit `render/queue.json` and push: `{"works": ["alc1", ...], "dest": "samples" | "release", "tag": "audio-v1"}`.
`engines/kokoro_work.py` renders each work with studio mastering and writes `KEY-pN.mp3` plus
`KEY-pN.timing.json` (per-word start times for the read-along player) and `KEY.report.json`.
