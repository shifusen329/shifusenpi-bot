"""Async Robot Brain - Non-blocking vision + personality LLM architecture.

Architecture:
1. Periodic async VLM calls → structured scene understanding (JSON)
2. Separate personality LLM → natural dialogue responses
3. Real-time Hailo → immediate obstacle avoidance
4. All async, non-blocking
"""

import asyncio
import time
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue

import numpy as np
from PIL import Image
import aiohttp


@dataclass
class SceneUnderstanding:
    """Structured scene data from VLM."""
    timestamp: float
    objects: List[Dict[str, Any]]  # [{name, position, confidence}, ...]
    scene_type: str  # "indoor", "outdoor", "room_type"
    obstacles: List[str]
    people_count: int
    safe_directions: List[str]  # ["left", "forward", "right"]
    description: str  # Human-readable summary
    confidence: float


@dataclass
class PersonalityResponse:
    """Response from personality LLM."""
    text: str
    emotion: str  # "happy", "concerned", "neutral", etc.
    action_suggested: Optional[str] = None


class AsyncRobotBrain:
    """Non-blocking robot brain with async API calls."""

    def __init__(
        self,
        vlm_url: str,
        vlm_model: str,
        llm_url: str,
        llm_model: str,
        api_key: str,
        personality: str = "friendly",
        vlm_interval: float = 3.0
    ):
        """
        Initialize async robot brain.

        Args:
            vlm_url: VLM API endpoint (for vision)
            vlm_model: Vision model name
            llm_url: LLM API endpoint (for personality)
            llm_model: Personality LLM model name
            api_key: API key for both
            personality: Robot personality type
            vlm_interval: Seconds between VLM calls
        """
        self.vlm_url = vlm_url
        self.vlm_model = vlm_model
        self.llm_url = llm_url
        self.llm_model = llm_model
        self.api_key = api_key
        self.personality = personality
        self.vlm_interval = vlm_interval

        # State
        self.running = False
        self.current_frame: Optional[np.ndarray] = None
        self.latest_scene: Optional[SceneUnderstanding] = None

        # Async components
        self.session: Optional[aiohttp.ClientSession] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None

        # Queues
        self.scene_queue = queue.Queue(maxsize=5)
        self.response_queue = queue.Queue(maxsize=10)

        # Stats
        self.vlm_calls = 0
        self.llm_calls = 0

    def start(self):
        """Start async processing."""
        if self.running:
            return

        self.running = True

        # Start event loop in background thread
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

        print("[AsyncBrain] Started with async API calls")

    def stop(self):
        """Stop async processing."""
        if not self.running:
            return

        self.running = False

        if self.loop:
            asyncio.run_coroutine_threadsafe(self._cleanup(), self.loop)

        if self.thread:
            self.thread.join(timeout=5.0)

        print("[AsyncBrain] Stopped")

    def _run_event_loop(self):
        """Run asyncio event loop in background thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Run main coroutine
        self.loop.run_until_complete(self._async_main())

    async def _async_main(self):
        """Main async coroutine."""
        async with aiohttp.ClientSession() as session:
            self.session = session

            # Start periodic vision processing
            vision_task = asyncio.create_task(self._vision_loop())

            # Wait until stopped
            while self.running:
                await asyncio.sleep(0.1)

            # Cancel tasks
            vision_task.cancel()

    async def _vision_loop(self):
        """Periodic vision processing with VLM."""
        print("[AsyncBrain] Vision loop started")

        while self.running:
            try:
                if self.current_frame is not None:
                    # Call VLM asynchronously
                    scene = await self._analyze_scene_async(self.current_frame)

                    if scene:
                        self.latest_scene = scene
                        try:
                            self.scene_queue.put_nowait(scene)
                        except queue.Full:
                            pass  # Drop old scene data

                        print(f"[AsyncBrain] Scene: {scene.scene_type}, "
                              f"objects: {len(scene.objects)}, "
                              f"people: {scene.people_count}")

                # Wait for next interval
                await asyncio.sleep(self.vlm_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[AsyncBrain] Vision loop error: {e}")
                await asyncio.sleep(1.0)

        print("[AsyncBrain] Vision loop ended")

    async def _analyze_scene_async(self, frame: np.ndarray) -> Optional[SceneUnderstanding]:
        """
        Analyze scene with VLM (async, structured output).

        Args:
            frame: Camera frame

        Returns:
            Structured scene understanding
        """
        try:
            # Convert frame to base64
            if isinstance(frame, np.ndarray):
                img = Image.fromarray(frame)
            else:
                img = frame

            import io
            import base64
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG')
            img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Structured prompt for VLM
            prompt = """Analyze this image from a robot's perspective and respond with JSON:
{
  "objects": [{"name": "...", "position": "left/center/right", "distance": "near/far", "confidence": 0.0-1.0}],
  "scene_type": "indoor/outdoor/kitchen/living_room/...",
  "obstacles": ["obstacle1", "obstacle2"],
  "people_count": 0,
  "safe_directions": ["left", "forward", "right"],
  "description": "Brief description of scene",
  "confidence": 0.0-1.0
}

Be concise and focus on navigation-relevant information."""

            # API payload
            payload = {
                "model": self.vlm_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.3  # Low temp for structured output
            }

            # Async API call
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            async with self.session.post(
                f"{self.vlm_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']

                    # Parse JSON response
                    scene_data = self._parse_scene_json(content)
                    self.vlm_calls += 1
                    return scene_data

                else:
                    print(f"[AsyncBrain] VLM API error: {response.status}")
                    return None

        except Exception as e:
            print(f"[AsyncBrain] Scene analysis error: {e}")
            return None

    def _parse_scene_json(self, content: str) -> SceneUnderstanding:
        """Parse VLM JSON response into structured data."""
        try:
            # Extract JSON from markdown code blocks if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            data = json.loads(content)

            return SceneUnderstanding(
                timestamp=time.time(),
                objects=data.get('objects', []),
                scene_type=data.get('scene_type', 'unknown'),
                obstacles=data.get('obstacles', []),
                people_count=data.get('people_count', 0),
                safe_directions=data.get('safe_directions', []),
                description=data.get('description', ''),
                confidence=data.get('confidence', 0.5)
            )

        except json.JSONDecodeError as e:
            print(f"[AsyncBrain] JSON parse error: {e}")
            # Fallback: use raw text as description
            return SceneUnderstanding(
                timestamp=time.time(),
                objects=[],
                scene_type='unknown',
                obstacles=[],
                people_count=0,
                safe_directions=[],
                description=content,
                confidence=0.3
            )

    async def get_personality_response_async(
        self,
        user_input: str,
        scene_context: Optional[SceneUnderstanding] = None
    ) -> PersonalityResponse:
        """
        Get personality-driven response from LLM (async).

        Args:
            user_input: User's command or question
            scene_context: Current scene understanding

        Returns:
            Personality response with emotion and suggested action
        """
        try:
            # Build context
            context_parts = [
                f"You are a {self.personality} robot assistant.",
                f"Current scene: {scene_context.description if scene_context else 'Unknown'}",
            ]

            if scene_context:
                context_parts.append(f"Objects visible: {[obj['name'] for obj in scene_context.objects]}")
                context_parts.append(f"People present: {scene_context.people_count}")
                context_parts.append(f"Obstacles: {scene_context.obstacles}")

            system_prompt = " ".join(context_parts)

            # User prompt with structured response request
            user_prompt = f"""{user_input}

Respond with JSON:
{{
  "text": "Your natural language response",
  "emotion": "happy/concerned/neutral/excited/confused",
  "action_suggested": "move_forward/turn_left/stop/none"
}}"""

            # API payload
            payload = {
                "model": self.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.8  # Higher temp for personality
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Async API call
            async with self.session.post(
                f"{self.llm_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']

                    # Parse response
                    response_data = self._parse_personality_json(content)
                    self.llm_calls += 1
                    return response_data

                else:
                    print(f"[AsyncBrain] LLM API error: {response.status}")
                    return PersonalityResponse(
                        text="I'm having trouble thinking right now.",
                        emotion="confused"
                    )

        except Exception as e:
            print(f"[AsyncBrain] Personality response error: {e}")
            return PersonalityResponse(
                text="Sorry, I encountered an error.",
                emotion="concerned"
            )

    def _parse_personality_json(self, content: str) -> PersonalityResponse:
        """Parse personality LLM JSON response."""
        try:
            # Extract JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            data = json.loads(content)

            return PersonalityResponse(
                text=data.get('text', content),
                emotion=data.get('emotion', 'neutral'),
                action_suggested=data.get('action_suggested')
            )

        except json.JSONDecodeError:
            # Fallback: use raw text
            return PersonalityResponse(
                text=content,
                emotion='neutral'
            )

    def update_frame(self, frame: np.ndarray):
        """Update current camera frame (non-blocking)."""
        self.current_frame = frame

    def get_personality_response(
        self,
        user_input: str,
        scene_context: Optional[SceneUnderstanding] = None
    ) -> PersonalityResponse:
        """
        Synchronous wrapper for personality response.

        Args:
            user_input: User command/question
            scene_context: Current scene

        Returns:
            Personality response
        """
        if not self.loop:
            return PersonalityResponse(text="System not ready", emotion="confused")

        # Run coroutine in event loop
        future = asyncio.run_coroutine_threadsafe(
            self.get_personality_response_async(user_input, scene_context),
            self.loop
        )

        try:
            return future.result(timeout=5.0)
        except Exception as e:
            print(f"[AsyncBrain] Sync wrapper error: {e}")
            return PersonalityResponse(text="Error processing request", emotion="confused")

    def get_latest_scene(self) -> Optional[SceneUnderstanding]:
        """Get most recent scene understanding."""
        return self.latest_scene

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "running": self.running,
            "vlm_calls": self.vlm_calls,
            "llm_calls": self.llm_calls,
            "latest_scene_age": time.time() - self.latest_scene.timestamp if self.latest_scene else None,
            "scene_queue_size": self.scene_queue.qsize()
        }

    async def _cleanup(self):
        """Cleanup async resources."""
        if self.session:
            await self.session.close()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
