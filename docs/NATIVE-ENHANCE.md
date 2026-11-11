# Native Enhance research

Verified November 11, 2026 against installed ComfyUI 0.45.2 and publisher sources.

[ComfyUI's official Qwen3.5 guide](https://docs.comfy.org/tutorials/llm/qwen/qwen3_5) documents native text generation and prompt optimization. Installed `nodes_textgen.py` exposes TextGenerateV2, system-prompt override, sampling controls, output limit and thinking toggle. `comfy/sd.py` auto-detects Qwen3.5 and executes CLIP generation on the patcher's selected load device. CLIPLoader's default delegates device and offload management to Comfy; `cpu` explicitly selects the fallback device.

Selected checkpoint: [Comfy-Org/Qwen3.5](https://huggingface.co/Comfy-Org/Qwen3.5), `text_encoders/qwen3.5_9b_w4a8_gptq.safetensors`, revision `a3f61d217d07c6936174625ce5d06e6079e9393e`, 7,343,591,088 bytes, SHA256 `4cc6a1543ad2061806da46f35f90cadb4801dcba246c44782cf42ec0feb6407c`. The publisher marks this model Apache-2.0. It is a quantized native safetensors checkpoint, not the previous GGUF helper.

The official repository also offers smaller BF16 variants, but this build selects the 4-bit checkpoint to honor the quantized workflow requirement. ModelScope's corresponding official repository currently lists BF16 variants only; no verified matching quantized alternate is invented. Other model components retain their digest-matched ModelScope fallbacks.

Enhance requests a short JSON-wrapped suggestion, thinking off, at most 640 output tokens. The app validates the prompt length and complete JSON before offering it for review. Reference notes and turnaround locks are sent as separate context fields. The helper receives text instructions, not the reference pixels; image generation still receives the actual reference pictures. The official P-H3 upsampler is a separate feature and model.

GPU is preferred through native Comfy management. A bounded CPU retry is eligible only for GPU resource/backend failures. Native CPU selection is reported explicitly rather than mislabeled as GPU. The 9B quantized model is much slower on CPU; this is a last-resort path, not the normal interactive experience. Runtime qualification is recorded in [VALIDATION.md](VALIDATION.md).
