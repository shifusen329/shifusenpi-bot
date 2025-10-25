"""Tests for VLM REST API integration."""

import os
import sys
from pathlib import Path
import base64
import io

import pytest
from PIL import Image, ImageDraw, ImageFont

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vlm_client import VLMClient


@pytest.fixture
def vlm_client():
    """Create VLM client instance."""
    client = VLMClient()
    yield client
    client.close()


@pytest.fixture
def sample_image():
    """Create a simple test image."""
    # Create a 400x300 image with some shapes
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)

    # Draw some shapes
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black', width=2)
    draw.ellipse([200, 50, 300, 150], fill='blue', outline='black', width=2)
    draw.polygon([(100, 200), (150, 250), (50, 250)], fill='green', outline='black', width=2)

    # Add text
    draw.text((20, 10), "Test Image", fill='black')

    return img


@pytest.fixture
def sample_image_path(tmp_path, sample_image):
    """Save sample image to temporary file."""
    img_path = tmp_path / "test_image.jpg"
    sample_image.save(img_path)
    return img_path


class TestVLMClient:
    """Test suite for VLM client."""

    def test_client_initialization(self):
        """Test client initializes with credentials from .env."""
        client = VLMClient()
        assert client.base_url is not None
        assert client.api_key is not None
        assert client.model is not None
        client.close()

    def test_client_initialization_with_custom_values(self):
        """Test client initialization with custom values."""
        client = VLMClient(
            base_url="http://custom.url",
            api_key="custom-key",
            model="custom-model"
        )
        assert client.base_url == "http://custom.url"
        assert client.api_key == "custom-key"
        assert client.model == "custom-model"
        client.close()

    def test_client_missing_credentials(self, monkeypatch):
        """Test client raises error when credentials are missing."""
        monkeypatch.delenv("LITELLM_BASE_URL", raising=False)
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)

        with pytest.raises(ValueError, match="LITELLM_BASE_URL"):
            VLMClient()

    def test_encode_image_from_path(self, vlm_client, sample_image_path):
        """Test encoding image from file path."""
        encoded = vlm_client.encode_image(sample_image_path)
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        # Verify it's valid base64
        decoded = base64.b64decode(encoded)
        assert len(decoded) > 0

    def test_encode_image_from_pil(self, vlm_client, sample_image):
        """Test encoding PIL Image."""
        encoded = vlm_client.encode_image(sample_image)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_image_from_bytes(self, vlm_client, sample_image):
        """Test encoding from bytes."""
        buffer = io.BytesIO()
        sample_image.save(buffer, format="JPEG")
        img_bytes = buffer.getvalue()

        encoded = vlm_client.encode_image(img_bytes)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_context_manager(self, sample_image):
        """Test VLMClient works as context manager."""
        with VLMClient() as client:
            assert client.session is not None
            result = client.encode_image(sample_image)
            assert isinstance(result, str)


class TestVLMAPI:
    """Test suite for VLM API calls (requires live API)."""

    @pytest.mark.integration
    def test_analyze_image_basic(self, vlm_client, sample_image):
        """Test basic image analysis."""
        response = vlm_client.analyze_image(
            sample_image,
            prompt="What shapes and colors do you see?",
            max_tokens=200
        )

        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "message" in response["choices"][0]
        assert "content" in response["choices"][0]["message"]

        content = response["choices"][0]["message"]["content"]
        print(f"\n\nVLM Response:\n{content}\n")

    @pytest.mark.integration
    def test_get_text_response(self, vlm_client, sample_image):
        """Test getting text-only response."""
        text = vlm_client.get_text_response(
            sample_image,
            prompt="Describe what you see in one sentence."
        )

        assert isinstance(text, str)
        assert len(text) > 0
        print(f"\n\nVLM Text Response:\n{text}\n")

    @pytest.mark.integration
    def test_detect_objects(self, vlm_client, sample_image):
        """Test object detection."""
        objects = vlm_client.detect_objects(sample_image)

        assert isinstance(objects, str)
        assert len(objects) > 0
        print(f"\n\nDetected Objects:\n{objects}\n")

    @pytest.mark.integration
    def test_describe_scene(self, vlm_client, sample_image):
        """Test scene description."""
        description = vlm_client.describe_scene(sample_image)

        assert isinstance(description, str)
        assert len(description) > 0
        print(f"\n\nScene Description:\n{description}\n")

    @pytest.mark.integration
    def test_navigate_assistance(self, vlm_client, sample_image):
        """Test navigation assistance for robot."""
        guidance = vlm_client.navigate_assistance(sample_image)

        assert isinstance(guidance, str)
        assert len(guidance) > 0
        print(f"\n\nNavigation Guidance:\n{guidance}\n")

    @pytest.mark.integration
    def test_analyze_with_different_temperatures(self, vlm_client, sample_image):
        """Test API with different temperature settings."""
        temperatures = [0.0, 0.5, 1.0]

        for temp in temperatures:
            response = vlm_client.get_text_response(
                sample_image,
                prompt="What do you see?",
                temperature=temp,
                max_tokens=100
            )
            assert isinstance(response, str)
            print(f"\n\nTemperature {temp}:\n{response}\n")

    @pytest.mark.integration
    def test_analyze_real_camera_image(self, vlm_client, tmp_path):
        """Test with a real camera image (if available)."""
        # Try to capture from camera
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            config = picam2.create_still_configuration(
                main={"size": (640, 480)}
            )
            picam2.configure(config)
            picam2.start()

            # Capture image
            img_path = tmp_path / "camera_test.jpg"
            picam2.capture_file(str(img_path))
            picam2.stop()

            # Analyze
            result = vlm_client.describe_scene(img_path)
            assert isinstance(result, str)
            print(f"\n\nCamera Image Analysis:\n{result}\n")

        except ImportError:
            pytest.skip("Picamera2 not available")
        except Exception as e:
            pytest.skip(f"Camera not available: {e}")


class TestVLMErrors:
    """Test error handling."""

    @pytest.mark.integration
    def test_invalid_image_type(self, vlm_client):
        """Test error with invalid image type."""
        with pytest.raises(TypeError):
            vlm_client.encode_image(12345)

    @pytest.mark.integration
    def test_nonexistent_file(self, vlm_client):
        """Test error with nonexistent file."""
        with pytest.raises(FileNotFoundError):
            vlm_client.encode_image("/path/to/nonexistent/file.jpg")


# Manual test script
if __name__ == "__main__":
    print("=" * 60)
    print("VLM REST API Manual Test")
    print("=" * 60)

    # Create test image
    img = Image.new('RGB', (400, 300), color='lightblue')
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black', width=3)
    draw.ellipse([200, 100, 350, 250], fill='yellow', outline='black', width=3)
    draw.text((20, 10), "Robot Vision Test", fill='black')

    # Test VLM
    with VLMClient() as client:
        print(f"\nConnected to: {client.base_url}")
        print(f"Using model: {client.model}")

        print("\n" + "-" * 60)
        print("Test 1: Basic Image Analysis")
        print("-" * 60)
        response = client.get_text_response(
            img,
            prompt="What shapes and colors do you see in this image?"
        )
        print(f"Response: {response}")

        print("\n" + "-" * 60)
        print("Test 2: Object Detection")
        print("-" * 60)
        objects = client.detect_objects(img)
        print(f"Objects: {objects}")

        print("\n" + "-" * 60)
        print("Test 3: Navigation Assistance")
        print("-" * 60)
        nav = client.navigate_assistance(img)
        print(f"Navigation: {nav}")

    print("\n" + "=" * 60)
    print("Tests completed successfully!")
    print("=" * 60)
