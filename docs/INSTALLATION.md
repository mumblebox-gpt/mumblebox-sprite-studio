# Installation

Use a current local ComfyUI installation with `CLIPLoader`, `TextGenerateV2`, P-H3 image nodes and the quantized model support they require. Development qualification used ComfyUI 0.45.2 and its existing Python environment. Keep development and runtime folders outside OneDrive.

1. Clone this repository to a plain local directory.
2. In PowerShell 7, run `./tools/install.ps1 -ComfyRoot '<your existing ComfyUI root>'`.
3. For encoded still RefMods, separately install [ComfyUI-MiniMaxH3Mod](https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod), qualified at commit `517e8c419a8584fbf69fceb487bc39d83e6a6ec8` (0.2.6), using its installation instructions. Ordinary reference collections do not require encoding.
4. Restart that ComfyUI installation when its queue is idle, then open `workflows/Sprite Studio - Starter.json`.
5. Use the Studio interface's Generate or Enhance buttons. These rebuild and queue only the chosen independent branch. The graph branches are muted to prevent an accidental global Run from running everything.

The installer copies only the extension package to `custom_nodes/mumblebox_sprite_studio`, verifies hashes and preserves the previous extension under `user/mumblebox_sprite_studio/install_backups`. Existing workflows, settings, models, inputs, outputs and other extensions are preserved. Python dependencies are the existing Comfy environment's aiohttp, Pillow, NumPy, safetensors, PyTorch and psutil. No llama.cpp executable or GGUF model is required.

First use downloads only missing model files for the selected operation. Files are pinned by revision, byte count and SHA256; partial downloads resume. Verified alternate sources are used where catalogued. The Qwen Enhance checkpoint currently has one verified publisher source; its ModelScope mirror does not yet carry that quantization. Existing files that differ from the selected checksum are preserved and reported.

Review the separately downloaded model publishers' licenses. Apache-2.0 applies to this extension, not to all models it can use.

Runtime records and reference packages live in `user/mumblebox_sprite_studio`; normalized references use `input/sprite_studio`, and images use `output/sprite_studio/<run-id>`. Do not copy these private folders into a public checkout. Gallery Trash is recoverable; Purge Cache only clears owned abandoned scratch.

To roll back, stop the backend and restore the named previous extension directory from its install backup. Preserve the user folder and all model/input/output directories. Update by pulling this repository and rerunning the installer; automatic updating is not implemented.

Run tests from the repository with the Comfy environment's Python: `python -B -m unittest discover -s tests -v`. Check browser modules using `node --check`. Installed UI behavior and model execution require separate live qualification.
