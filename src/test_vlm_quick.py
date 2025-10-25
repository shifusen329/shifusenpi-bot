#!/usr/bin/env python3
"""Quick VLM API test script."""

from vlm_client import VLMClient
from PIL import Image, ImageDraw
import sys


def create_test_image():
    """Create a simple test image."""
    img = Image.new('RGB', (640, 480), color='skyblue')
    draw = ImageDraw.Draw(img)

    # Draw robot environment simulation
    draw.rectangle([50, 300, 200, 450], fill='brown', outline='black', width=3)  # Box
    draw.ellipse([400, 200, 550, 350], fill='red', outline='black', width=3)     # Ball
    draw.polygon([(300, 400), (350, 450), (250, 450)], fill='green', outline='black', width=3)  # Triangle

    # Draw "floor"
    draw.line([0, 460, 640, 460], fill='gray', width=5)

    draw.text((10, 10), "Robot Camera View", fill='black')

    return img


def main():
    """Run quick VLM test."""
    print("=" * 70)
    print(" VLM REST API Quick Test")
    print("=" * 70)

    # Create test image
    print("\n[1/4] Creating test image...")
    img = create_test_image()
    img.save("/tmp/vlm_test.jpg")
    print("      Saved to /tmp/vlm_test.jpg")

    # Initialize client
    print("\n[2/4] Connecting to VLM API...")
    try:
        client = VLMClient()
        print(f"      Connected to: {client.base_url}")
        print(f"      Using model: {client.model}")
    except Exception as e:
        print(f"      ERROR: {e}")
        print("\n      Please check your .env file configuration:")
        print("      - LITELLM_BASE_URL")
        print("      - LITELLM_API_KEY")
        print("      - VISION_MODEL")
        sys.exit(1)

    # Test object detection
    print("\n[3/4] Testing object detection...")
    try:
        objects = client.detect_objects(img)
        print(f"\n      Objects detected:")
        print(f"      {objects}")
    except Exception as e:
        print(f"      ERROR: {e}")
        sys.exit(1)

    # Test navigation assistance
    print("\n[4/4] Testing navigation assistance...")
    try:
        nav = client.navigate_assistance(img)
        print(f"\n      Navigation guidance:")
        print(f"      {nav}")
    except Exception as e:
        print(f"      ERROR: {e}")
        sys.exit(1)

    client.close()

    print("\n" + "=" * 70)
    print(" All tests passed successfully! ✓")
    print("=" * 70)


if __name__ == "__main__":
    main()
