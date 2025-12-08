"""
视觉语言模型 (VLM) 描述模块
用于对 PDF 中提取出来的图像生成上下文描述
"""

import base64
import os
import time
from typing import Dict, List, Optional

import requests

from logger_config import get_logger

try:
    from transformers import pipeline

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class ImageCaptioner:
    """统一的图像描述接口，支持 HuggingFace Transformers 与 Ollama"""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2-VL-7B-Instruct",
        provider: str = "transformers",
        device: Optional[str] = None,
        prompt_prefix: str = (
            "你是一名林业病理学专家，请详细描述图像中的关键对象、场景、"
            "文字与统计信息，突出与松材线虫病相关的知识点。"
        ),
        ollama_host: str = "http://localhost:11434",
        timeout: int = 120,
    ):
        self.logger = get_logger("ImageCaptioner")
        self.model_name = model_name
        self.provider = provider
        self.device = device
        self.prompt_prefix = prompt_prefix
        self.ollama_host = ollama_host.rstrip("/")
        self.timeout = timeout
        self._pipeline = None

        if provider == "transformers":
            self._initialize_transformer_pipeline()
        elif provider == "ollama":
            self.logger.info(f"使用 Ollama 图像描述: {self.model_name}")
        else:
            raise ValueError(f"不支持的图片描述提供方: {provider}")

    def _initialize_transformer_pipeline(self):
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "未检测到 transformers 依赖，无法启用图像描述功能。"
            )

        generation_kwargs: Dict = {"trust_remote_code": True}
        if self.device is not None:
            generation_kwargs["device"] = self.device

        self._pipeline = pipeline(
            task="image-to-text", model=self.model_name, **generation_kwargs
        )
        self.logger.info(f"已加载视觉模型: {self.model_name}")

    def caption_image(self, image_path: str, prompt: Optional[str] = None) -> str:
        """为单张图像生成描述"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"找不到图像: {image_path}")

        final_prompt = prompt or self.prompt_prefix

        if self.provider == "transformers":
            return self._caption_with_transformers(image_path, final_prompt)
        if self.provider == "ollama":
            return self._caption_with_ollama(image_path, final_prompt)

        raise ValueError(f"未知 provider: {self.provider}")

    def caption_batch(
        self, image_paths: List[str], prompt: Optional[str] = None
    ) -> Dict[str, str]:
        """批量生成描述"""
        captions: Dict[str, str] = {}
        for image_path in image_paths:
            try:
                captions[image_path] = self.caption_image(image_path, prompt)
            except Exception as exc:  # pragma: no cover - 日志诊断用
                self.logger.warning(
                    f"生成图像描述失败: {os.path.basename(image_path)} - {exc}"
                )
        return captions

    def _caption_with_transformers(self, image_path: str, prompt: str) -> str:
        if not self._pipeline:
            raise RuntimeError("Transformers pipeline 未初始化")

        try:
            result = self._pipeline(image_path, prompt=prompt)
        except TypeError:
            # 有些模型不接受 prompt 参数
            result = self._pipeline({"image": image_path, "prompt": prompt})
        except Exception:
            # 回退到无 prompt 推理
            result = self._pipeline(image_path)

        if isinstance(result, list) and result:
            text = result[0].get("generated_text") or result[0].get("text") or ""
            return text.strip()

        return ""

    def _check_ollama_health(self) -> bool:
        """检查 Ollama 服务是否健康"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _caption_with_ollama(self, image_path: str, prompt: str, max_retries: int = 3) -> str:
        """使用 Ollama 生成图片描述，支持重试"""
        with open(image_path, "rb") as file:
            image_b64 = base64.b64encode(file.read()).decode("utf-8")

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                # 在重试前检查 Ollama 是否健康
                if attempt > 0:
                    self.logger.info(f"第 {attempt + 1} 次重试，检查 Ollama 服务...")
                    for wait_time in range(10):  # 等待最多10秒
                        if self._check_ollama_health():
                            self.logger.info("Ollama 服务已恢复")
                            break
                        time.sleep(1)
                    else:
                        self.logger.warning("Ollama 服务未恢复，继续尝试...")

                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()

            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.HTTPError) as e:
                last_error = e
                self.logger.warning(
                    f"Ollama 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                    self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            except Exception as e:
                last_error = e
                self.logger.error(f"未预期的错误: {e}")
                break

        # 所有重试都失败
        self.logger.error(f"所有重试均失败，最后错误: {last_error}")
        return ""


__all__ = ["ImageCaptioner", "TRANSFORMERS_AVAILABLE"]

