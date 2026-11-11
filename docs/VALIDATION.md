# Development preview validation

Version 0.1.0-dev.4, November 11, 2026. Tested in the existing ComfyUI Desktop with ComfyUI 0.45.2, Python 3.13 and an RTX 4080 SUPER with 16 GiB VRAM and approximately 64 GB system RAM. This is a development preview, not a claim that every exposed model setting fits every machine.

## Automated checks

45 Python contract tests pass. Coverage includes immutable image recipes and seed handling, reference numbering, crop/export bounds, RefMod validation, first-use download verification/resume/alternate-source faults, Gallery Trash/restore, cache ownership, native request identity, cancellation and restart races. New Enhance cases cover native graph wiring, one CPU retry after eligible GPU errors, distinct attempt IDs, no retry for malformed content, canceled pending retries, stale completion races and exclusion of text jobs from Gallery. All 16 JavaScript modules pass syntax checks.

The public starter has 35 nodes in four independent groups, with no cross-branch connections. Generation branches are muted against accidental global Run. It contains generic prompts and a reference placeholder, no private recipes, image IDs or local paths. The installed package's 47 source files were hash-checked against the source.

## Installed behavior

- Clicking Enhance downloaded and SHA256-verified the 7.34 GB native Qwen checkpoint on first use. A complete robot prompt suggestion then finished on `cuda:0` in 4.1 seconds, as reported by the native result receipt and corroborated by the Comfy log. This is one observed run, not a benchmark average.
- Accept copied the reviewed candidate into the prompt; Discard preserved the prior prompt. The image preview stayed available during enhancement. No llama.cpp process was used.
- CPU support received a bounded native smoke test: a one-token response completed with execution device `cpu`. A longer CPU diagnostic was interrupted after seven generated tokens because it was very slow. A full CPU enhancement is **not** performance-qualified. Automatic fallback control flow is fault-tested; there is no separate CPU workflow or mode.
- All seven tabs were checked for labeled SVG button icons. Visible counts ranged from 13 to 102 buttons per tab. Theme and favorite toggles retained their icons and restored their prior states. Dark and light themes received visual review in the actual Desktop.
- A fresh 1024-square W4A8 image generated successfully after native text execution, confirming that Comfy could transition back to the image workload.
- A fresh INT8 4096 × 1024 reference-led turnaround completed in 24.8 seconds. Its four-view crop review opened with icon-labeled controls. These two regression outputs were moved to recoverable Trash after testing, and the original drafts, graph inputs, theme, Gallery selection and preview were restored.
- An observed stale-module update failure was repaired with cache revalidation. The installed Settings help now correctly describes native GPU-first Enhance.

Earlier local qualification covered both image precisions, both official upsampler precisions, four-picture references, character and aircraft turnarounds, still RefMod encode/decode/import, reviewed crop ZIPs, Gallery reuse/Trash, model unloading and bounded cache purge. Those earlier runs are historical evidence; they are not represented as rerun for every preview change.

## Limits

CPU fallback is a last resort and may be extremely slow for this 9B checkpoint. Full CPU suggestion latency is not qualified. Generated turnaround angles and details can differ from requests; there is no calibrated-camera or mesh-quality claim. H3 animation, game sprite production, translations, automatic updates and Foundry integration remain future work. Private evidence and user assets are excluded from the repository.
