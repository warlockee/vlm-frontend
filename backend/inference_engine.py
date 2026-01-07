"""
High-Performance vLLM Inference Engine for Qwen3-VL-32B
"""
import logging
import os
from typing import List, Dict
from PIL import Image

logger = logging.getLogger(__name__)

MERGED_MODEL_PATH = "/home/ec2-user/efs/vlm/experiments/phase3_qwen3_deepspeed/merged_model"


class VLLMInferenceEngine:
    def __init__(
        self,
        model_path: str = MERGED_MODEL_PATH,
        tensor_parallel_size: int = 8,
        max_model_len: int = 32768,
        gpu_memory_utilization: float = 0.90,
        max_num_seqs: int = 32,
    ):
        self.model_path = model_path
        self.tensor_parallel_size = tensor_parallel_size
        self.max_model_len = max_model_len
        self.gpu_memory_utilization = gpu_memory_utilization
        self.max_num_seqs = max_num_seqs
        self.llm = None

    def load_model(self):
        logger.info("Initializing vLLM Inference Engine")
        logger.info(f"Model path: {self.model_path}")
        logger.info(f"Tensor parallel size: {self.tensor_parallel_size}")

        try:
            from vllm import LLM

            # Use ray for distributed execution instead of multiprocessing
            self.llm = LLM(
                model=self.model_path,
                tensor_parallel_size=self.tensor_parallel_size,
                gpu_memory_utilization=self.gpu_memory_utilization,
                max_model_len=self.max_model_len,
                max_num_seqs=self.max_num_seqs,
                trust_remote_code=True,
                dtype="bfloat16",
                enable_prefix_caching=True,
                limit_mm_per_prompt={"image": 1},
                enforce_eager=True,  # Disable CUDA graphs for stability
                distributed_executor_backend="ray",  # Use Ray instead of multiprocessing
            )

            logger.info("vLLM model loaded successfully!")

        except Exception as e:
            logger.error(f"Failed to load model with vLLM: {e}")
            raise e

    def predict(self, image_path: str, prompt: str, max_tokens: int = 1024) -> str:
        if not self.llm:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        from vllm import SamplingParams
        import base64

        logger.info(f"Running vLLM inference on {image_path}")

        # Load and encode image as base64
        img = Image.open(image_path).convert("RGB")
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Use OpenAI-compatible format for vLLM VLM
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        sampling_params = SamplingParams(
            max_tokens=max_tokens,
            temperature=0.0,
            top_p=1.0,
        )

        outputs = self.llm.chat(
            messages=[messages],
            sampling_params=sampling_params,
        )

        return outputs[0].outputs[0].text

    @property
    def model(self):
        return self.llm


vllm_engine = VLLMInferenceEngine(
    tensor_parallel_size=8,
    gpu_memory_utilization=0.90,
    max_num_seqs=32,
)
