# Third-party sources

- P-H3-Image weights and official prompt upsampler: PrunaAI/P-H3-Image-Comfy, pinned revision44a0fb73f299da1bb715bdb5ff59ce3fd3c6f543. https://huggingface.co/PrunaAI/P-H3-Image-Comfy . Weights are downloaded separately; retain the repository's model license and terms.
- Original H3 video VAE: Comfy-Org/MiniMax-H3 revision54472221d27c695fca9621b0c3ed52f06c4af707. https://huggingface.co/Comfy-Org/MiniMax-H3 . Model license remains the publisher's MiniMax H3 community agreement.
- ComfyUI: https://github.com/Comfy-Org/ComfyUI . This extension uses native public nodes and HTTP/JavaScript integration; ComfyUI is supplied separately under its own license.
- ComfyUI-MiniMaxH3Mod0.2.6: https://github.com/Luisacaotica/ComfyUI-MiniMaxH3Mod commit517e8c419a8584fbf69fceb487bc39d83e6a6ec8. Copyright(c)2026 Luisa(luisacaotica), MIT. Installed separately with its full LICENSE. Studio's typed still-list join is its own small adapter; extraction, bundling and decoding remain upstream.
- Native Enhance model: https://huggingface.co/Comfy-Org/Qwen3.5 , Apache-2.0; quantized safetensors weights are downloaded separately. See docs/NATIVE-ENHANCE.md for the pinned file and digest. No llama.cpp code or runtime is used or bundled.
- Official Pruna image-prompting skill1.0.15 supplies turnaround wording guidance. The installed reference identifies its Square-Zero-Labs/video-prompting-skill adaptation under Apache2.0. No skill files are bundled in this extension.
- Pillow, NumPy, safetensors, PyTorch, aiohttp and psutil are existing environment dependencies. Their respective notices remain with the environment. No dependencies or model weights are vendored into this package.

The approved pixel logo and activity SVG are the local Sprite Studio design assets. Private runtime data and evidence are not distribution assets.
