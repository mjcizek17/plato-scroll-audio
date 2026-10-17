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

## Engines under audition
| Engine | Licence | How voices are made |
|---|---|---|
| Kokoro-82M | Apache-2.0 | the existing blended cast (Socrates = george 0.55 + santa 0.45) |
| Qwen3-TTS 1.7B | Apache-2.0 | each character cast from a written brief (VoiceDesign), then cloned for every line (Base) |
| Chatterbox / Chatterbox Turbo | MIT (inaudible watermark) | clones a reference clip per character |

Results: `samples` branch, `audition/run-N/<engine>/*.mp3`, with `speed.json` (real-time factor on a 4-core runner).
