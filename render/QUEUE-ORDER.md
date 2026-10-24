# Render queue order (2026-10-23, user's priority)

1. **Laws re-recording** — run 39994491897 (laws → audio-v1, laws-b → jowett-v1, epin → audio-v1): the Athenian Stranger now speaks with Socrates' voice. This run must have the runners to itself.
2. Plutarch & Platonists C–F (render/next/queue-C..F.json) — re-queue **one at a time, only after the Laws run has published**. Their earlier runs were cancelled on purpose: GitHub spread the few runners it grants across all queued runs and starved the Laws.

Please don't re-run ("Re-run all jobs") a produce run that has finished shards — it discards them (attempt 2 of the Laws lost 27 finished shards). To repair failed shards use ranges + reuse_run in render/queue.json instead.
