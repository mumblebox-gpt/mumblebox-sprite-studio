# Ownership

`application.py` wires feature services; `api.py` is the loopback-only adapter. Feature folders own their paired Python and browser behavior. `shell/` owns the fixed bars, tabs, theme, common controls and SVG icons.

`runtime/jobs.py` is the sole owner of Studio request identity, immutable recipes, preparation, queue submission, cancellation and restart reconciliation. `runtime/jobs.mjs` synchronizes the selected branch into the open graph before acknowledging execution. `runtime/graph.mjs` owns four non-overlapping node ranges: image 100–299, turnaround 300–499, RefMods 500–699, Enhance 700–899.

ComfyUI owns all inference and model memory. Enhance uses native CLIPLoader and TextGenerateV2. Studio's small result node records generated text and the native execution device; it does not load or run a language model. A GPU resource failure may prepare one CPU attempt with a distinct native prompt ID and another live graph acknowledgment. It never interrupts unrelated queue work. Validation or output-format errors do not trigger CPU retry.

`runtime/downloads.py` owns resumable, verified transfer and atomic promotion; `runtime/models.py` chooses only the requested components. `storage.py` owns SQLite and path containment. Feature services own reference import, Gallery metadata/Trash, crop review/export, RefMod bundles and strictly scoped temporary files.

Image drafts and generated recipes are separate. Enhance captures the brief, reference instructions and turnaround constraints and returns a candidate for review. Accept changes the editable prompt; Discard preserves it. Enhancement text jobs stay out of the image Gallery. Original references and requested camera metadata remain attached to image recipes.

H3 animation, game sprite processing, translations and automatic Foundry integration remain future work. Generated camera requests are not measured calibration, and no mesh reconstruction quality is claimed.
