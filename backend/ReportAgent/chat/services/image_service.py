from .base_service import BaseService
import os
import requests
from typing import Dict, Any, Optional
import json

class ImageService(BaseService):
    def __init__(self):
        super().__init__()
        self.image_generation_token = os.getenv('BEARER_TOKEN_FOR_THE_AI_GENERATION_SERVICE')
        self.image_generation_url = "http://localhost:5001/Generation/image"

    def generate_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates an image using the AI Generation Service
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.image_generation_token}",
                "Content-Type": "application/json"
            }

            # API 스펙에 맞춘 정확한 페이로드 구성
            payload = {
                "userId": str(params.get("userId", "260")),
                "prompt": str(params.get("prompt", "")),
                "aspectRatio": int(params.get("aspectRatio", 0)),
                "useIppy": bool(params.get("useIppy", False)),
                "usePepe": bool(params.get("usePepe", False)),
                "useCoco": bool(params.get("useCoco", False)),
                "useMfer": bool(params.get("useMfer", False)),
                "useMilady": bool(params.get("useMilady", False)),
                "usePepenobi": bool(params.get("usePepenobi", False)),
                "useBoop": bool(params.get("useBoop", False)),
                "useMonadpepe": bool(params.get("useMonadpepe", False)),
                "usePatty": bool(params.get("usePatty", False)),
                "useClaude": bool(params.get("useClaude", False)),
                "useBlueArbpepe": bool(params.get("useBlueArbpepe", False)),
                "useStoryMushy": bool(params.get("useStoryMushy", False)),
                "useFate": bool(params.get("useFate", False)),
                "usePipi": bool(params.get("usePipi", False)),
                "useBopr": bool(params.get("useBopr", False)),
                "useSparky": bool(params.get("useSparky", False))
            }

            print(f"Sending request with payload: {json.dumps(payload, indent=2)}")

            response = requests.post(
                self.image_generation_url,
                json=payload,
                headers=headers,
                verify=False,
                timeout=60
            )

            print(f"Server response code: {response.status_code}")
            print(f"Server response text: {response.text}")

            if response.status_code == 200:
                response_data = response.json()
                return {
                    "status": "success",
                    "data": response_data
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to generate image: {response.status_code}",
                    "details": response.text
                }

        except Exception as e:
            print(f"Exception in generate_image: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"Error generating image: {str(e)}"
            }