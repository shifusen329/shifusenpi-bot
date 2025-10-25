"""VLM Client for LiteLLM Gateway integration."""

import os
import base64
from typing import Optional, Union, Dict, Any
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image
import io


class VLMClient:
    """Client for interacting with VLM via LiteLLM Gateway."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize VLM client.

        Args:
            base_url: LiteLLM gateway base URL
            api_key: API key for authentication
            model: Vision model to use
        """
        load_dotenv()

        self.base_url = base_url or os.getenv("LITELLM_BASE_URL")
        self.api_key = api_key or os.getenv("LITELLM_API_KEY")
        self.model = model or os.getenv("VISION_MODEL", "llama3.2-vision:90b-instruct-q4_K_M")

        if not self.base_url:
            raise ValueError("LITELLM_BASE_URL must be set in .env or provided")
        if not self.api_key:
            raise ValueError("LITELLM_API_KEY must be set in .env or provided")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def encode_image(self, image_source: Union[str, Path, bytes, Image.Image]) -> str:
        """
        Encode image to base64 string.

        Args:
            image_source: Image file path, bytes, or PIL Image

        Returns:
            Base64 encoded image string
        """
        if isinstance(image_source, (str, Path)):
            # Load from file path
            with open(image_source, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode("utf-8")

        elif isinstance(image_source, bytes):
            # Already bytes
            return base64.b64encode(image_source).decode("utf-8")

        elif isinstance(image_source, Image.Image):
            # PIL Image
            buffer = io.BytesIO()
            image_source.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

        else:
            raise TypeError(f"Unsupported image source type: {type(image_source)}")

    def analyze_image(
        self,
        image_source: Union[str, Path, bytes, Image.Image],
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze an image with a text prompt.

        Args:
            image_source: Image to analyze (file path, bytes, or PIL Image)
            prompt: Text prompt describing what to analyze
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            API response dictionary with analysis results
        """
        # Encode image
        image_b64 = self.encode_image(image_source)

        # Prepare request payload (OpenAI-compatible format)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # Make API request
        endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
        response = self.session.post(endpoint, json=payload)
        response.raise_for_status()

        return response.json()

    def get_text_response(
        self,
        image_source: Union[str, Path, bytes, Image.Image],
        prompt: str,
        **kwargs
    ) -> str:
        """
        Get text-only response from image analysis.

        Args:
            image_source: Image to analyze
            prompt: Analysis prompt
            **kwargs: Additional arguments for analyze_image()

        Returns:
            Text response from VLM
        """
        result = self.analyze_image(image_source, prompt, **kwargs)

        # Extract text from OpenAI-compatible response format
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]

        raise ValueError(f"Unexpected response format: {result}")

    def detect_objects(
        self,
        image_source: Union[str, Path, bytes, Image.Image]
    ) -> str:
        """
        Detect and describe objects in an image.

        Args:
            image_source: Image to analyze

        Returns:
            Description of detected objects
        """
        prompt = "List all objects you can see in this image. Be specific and detailed."
        return self.get_text_response(image_source, prompt)

    def describe_scene(
        self,
        image_source: Union[str, Path, bytes, Image.Image]
    ) -> str:
        """
        Get a detailed description of the scene.

        Args:
            image_source: Image to analyze

        Returns:
            Scene description
        """
        prompt = "Describe this scene in detail, including objects, colors, layout, and any notable features."
        return self.get_text_response(image_source, prompt)

    def navigate_assistance(
        self,
        image_source: Union[str, Path, bytes, Image.Image]
    ) -> str:
        """
        Get navigation assistance from image (for robot movement).

        Args:
            image_source: Camera view image

        Returns:
            Navigation guidance
        """
        prompt = """Analyze this image for robot navigation:
1. Identify obstacles and their positions (left, center, right)
2. Estimate distances if possible
3. Suggest safe movement directions
4. Warn about hazards (stairs, edges, fragile objects)
Be concise and actionable."""
        return self.get_text_response(image_source, prompt, max_tokens=500)

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
