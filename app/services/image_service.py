"""
图片生成服务模块
使用火山方舟 Doubao Seedream 生成小红书风格配图
"""
import os
import asyncio
import base64
import uuid
import random
import httpx
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class ImageService:
    """图片生成服务类"""

    XHS_STYLE_PROMPT = (
        "小红书竖版配图，3:4，明亮精致，主体突出，留白干净，不要文字和水印。"
        "画面内容：{content}"
    )

    FALLBACK_PROMPTS = [
        "小红书风格，明亮温暖的生活场景，咖啡和书本，柔和自然光，3:4竖版构图",
        "小红书风格，创意工作台，文具和绿植，ins风格，3:4竖版构图",
        "小红书风格，清新简约的扁平插画，渐变色背景，3:4竖版构图",
    ]

    def __init__(self):
        self.api_key = os.getenv("IMAGE_API_KEY", "")
        self.base_url = os.getenv(
            "IMAGE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
        ).rstrip("/")
        self.model = os.getenv("IMAGE_MODEL", "doubao-seedream-5-0-flash-260915")
        # Seedream 5.0 flash 的 1.5K 3:4 推荐像素
        self.size = os.getenv("IMAGE_SIZE", "1344x1792")
        
        self.image_dir = Path("static/images/generated")
        self.image_dir.mkdir(parents=True, exist_ok=True)

        if not self.api_key:
            raise ValueError("IMAGE_API_KEY 未配置")

    def _build_api_url(self) -> str:
        return f"{self.base_url}/images/generations"

    def _save_image(self, image_base64: str, prefix: str = "xhs") -> str:
        """保存 base64 图片到本地"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}_{timestamp}_{unique_id}.png"
        
        file_path = self.image_dir / filename
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_base64))
        
        return f"/static/images/generated/{filename}"

    async def _call_seedream_api(self, prompt: str) -> Optional[str]:
        """调用火山方舟 Seedream 图片生成接口，返回图片的 base64。"""
        url = self._build_api_url()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": self.size,
            "response_format": "b64_json",
            "output_format": "png",
            "watermark": False,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

                data = result.get("data") or []
                if not data:
                    print("[ImageService] API 响应中未找到图片数据")
                    return None

                image_base64 = data[0].get("b64_json")
                if image_base64:
                    return image_base64

                image_url = data[0].get("url")
                if image_url:
                    download = await client.get(image_url)
                    download.raise_for_status()
                    return base64.b64encode(download.content).decode("ascii")

                print("[ImageService] API 响应中未找到图片数据")
                return None

        except httpx.HTTPStatusError as e:
            body = e.response.text[:300]
            print(f"[ImageService] HTTP 错误: {e.response.status_code} {body}")
            return None
        except Exception as e:
            print(f"[ImageService] 请求异常: {e}")
            return None

    async def generate_single_image(
        self,
        prompt: str,
        optimize_for_xhs: bool = True,
    ) -> Optional[str]:
        """生成单张图片（失败时使用备用提示词重试一次）"""
        current_prompt = self.XHS_STYLE_PROMPT.format(content=prompt) if optimize_for_xhs else prompt
        
        print(f"[ImageService] 生成图片: {prompt[:50]}...")
        
        # 首次尝试
        image_base64 = await self._call_seedream_api(current_prompt)
        if image_base64:
            image_path = self._save_image(image_base64)
            print(f"[ImageService] 图片生成成功: {image_path}")
            return image_path
        
        # 使用备用提示词重试
        print(f"[ImageService] 首次失败，使用备用提示词重试...")
        await asyncio.sleep(1)
        
        fallback_prompt = random.choice(self.FALLBACK_PROMPTS)
        image_base64 = await self._call_seedream_api(fallback_prompt)
        if image_base64:
            image_path = self._save_image(image_base64)
            print(f"[ImageService] 备用提示词成功: {image_path}")
            return image_path
        
        print(f"[ImageService] 图片生成失败，跳过")
        return None

    async def generate_images(
        self,
        visual_points: List[str],
        optimize_for_xhs: bool = True,
    ) -> List[str]:
        """批量生成配图（并行）"""
        if not visual_points:
            return []

        tasks = [
            self.generate_single_image(prompt=point, optimize_for_xhs=optimize_for_xhs)
            for point in visual_points
        ]
        results = await asyncio.gather(*tasks)

        image_paths = [path for path in results if path is not None]
        print(f"[ImageService] 成功生成 {len(image_paths)}/{len(visual_points)} 张图片")
        return image_paths


# 单例实例
image_service = ImageService()
