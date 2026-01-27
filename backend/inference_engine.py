
import logging
import os
import uuid
import asyncio
from typing import List, Dict, AsyncGenerator
from PIL import Image

logger = logging.getLogger(__name__)

MERGED_MODEL_PATH = "/home/ec2-user/efs/vlm/experiments/phase3_qwen3_deepspeed/merged_model"

class VLLMInferenceEngine:
    def __init__(
        self,
        model_path: str = MERGED_MODEL_PATH,
        tensor_parallel_size: int = 1,
        max_model_len: int = 16384,
        gpu_memory_utilization: float = 0.90,
        max_num_seqs: int = 256,        # Increase batch size capacity
    ):
        self.model_path = model_path
        self.tensor_parallel_size = tensor_parallel_size
        self.max_model_len = max_model_len
        self.gpu_memory_utilization = gpu_memory_utilization
        self.max_num_seqs = max_num_seqs
        self.engine = None
        self.tokenizer = None

    def load_model(self):
        logger.info("Initializing vLLM Async Inference Engine (TP=1, Ray)")
        logger.info(f"Model path: {self.model_path}")
        
        try:
            from vllm.engine.async_llm_engine import AsyncLLMEngine
            from vllm.engine.arg_utils import AsyncEngineArgs

            engine_args = AsyncEngineArgs(
                model=self.model_path,
                tensor_parallel_size=1,  # TP=1 per replica
                gpu_memory_utilization=0.90,
                max_model_len=self.max_model_len,
                max_num_seqs=64,
                trust_remote_code=True,
                dtype="bfloat16",
                enable_prefix_caching=True,
                limit_mm_per_prompt={"image": 1},
                enforce_eager=True,
                distributed_executor_backend="mp",
                disable_log_stats=False,
            )
            
            self.engine = AsyncLLMEngine.from_engine_args(engine_args)
            logger.info("vLLM Async Engine initialized")
            
            try:
                self.tokenizer = self.engine.engine.get_tokenizer()
            except:
                from transformers import AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
            
        except Exception as e:
            logger.error(f"Failed to load async model: {e}")
            raise e

    async def predict(self, image_path: str, prompt: str, max_tokens: int = 1024) -> str:
        if not self.engine:
            raise RuntimeError("Engine not loaded.")

        from vllm import SamplingParams
        
        # Load Image (Async)
        def load_image_sync():
            return Image.open(image_path).convert("RGB")
            
        image = await asyncio.to_thread(load_image_sync)
        
        final_prompt = f"USER: <|image_pad|>\n{prompt}\nASSISTANT:"

        request_id = str(uuid.uuid4())
        sampling_params = SamplingParams(max_tokens=max_tokens, temperature=0.0)
        
        inputs = {
            "prompt": final_prompt,
            "multi_modal_data": {"image": image},
        }

        results_generator = self.engine.generate(
            prompt=inputs,
            sampling_params=sampling_params,
            request_id=request_id
        )
        
        final_output = None
        async for request_output in results_generator:
            final_output = request_output

        if final_output:
            return final_output.outputs[0].text
        return ""

    @property
    def model(self):
        return self.engine

# Instantiate
vllm_engine = VLLMInferenceEngine(
    tensor_parallel_size=1,
    gpu_memory_utilization=0.90,
    max_num_seqs=256,
)

