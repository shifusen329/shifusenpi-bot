#!/usr/bin/env python3
"""Demo: Autonomous wandering robot.

Roomba-style exploration with vision, personality, and chaos.
"""

import sys
import time
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent))

from async_brain import AsyncRobotBrain
from autonomous_agent import AutonomousAgent
from dotenv import load_dotenv


def movement_callback(command: dict):
    """Handle movement commands from agent."""
    action = command.get('action', 'UNKNOWN')
    print(f"  🤖 Movement: {action} {command}")


def demo_autonomous_agent():
    """Run autonomous agent demo."""
    print("=" * 70)
    print(" AUTONOMOUS AGENT DEMO")
    print(" (Roomba-style but with AI and questionable decisions)")
    print("=" * 70)

    # Load credentials
    load_dotenv()
    base_url = os.getenv('LITELLM_BASE_URL')
    api_key = os.getenv('LITELLM_API_KEY')
    vision_model = os.getenv('VISION_MODEL')

    if not all([base_url, api_key, vision_model]):
        print("\n⚠️  No API credentials, running in simulation mode\n")

        # Create mock brain
        class MockBrain:
            def get_latest_scene(self):
                # Simulate scene data
                import random
                from async_brain import SceneUnderstanding

                objects = []
                if random.random() < 0.7:
                    objects.append({
                        "name": random.choice(["chair", "table", "cup", "book"]),
                        "position": random.choice(["left", "center", "right"]),
                        "distance": random.choice(["near", "far"]),
                        "confidence": 0.8
                    })

                return SceneUnderstanding(
                    timestamp=time.time(),
                    objects=objects,
                    scene_type=random.choice(["indoor", "living_room", "kitchen"]),
                    obstacles=["chair"] if random.random() < 0.3 else [],
                    people_count=1 if random.random() < 0.2 else 0,
                    safe_directions=random.choice([
                        ["forward", "left"],
                        ["forward", "right"],
                        ["left", "right"],
                        ["backward"]
                    ]),
                    description="Simulated scene",
                    confidence=0.7
                )

            def get_personality_response(self, text, scene_context=None):
                from async_brain import PersonalityResponse
                import random

                responses = [
                    "Hmm, interesting!",
                    "I should probably investigate that.",
                    "This looks fun!",
                    "Better be careful here.",
                    "What's that over there?"
                ]

                return PersonalityResponse(
                    text=random.choice(responses),
                    emotion=random.choice(["curious", "happy", "concerned"]),
                    action_suggested=random.choice(["move_forward", "turn_left", None])
                )

        brain = MockBrain()

    else:
        # Real brain with API
        print(f"\nInitializing AI brain:")
        print(f"  VLM: {vision_model}")
        print(f"  Gateway: {base_url}\n")

        brain = AsyncRobotBrain(
            vlm_url=base_url,
            vlm_model=vision_model,
            llm_url=base_url,
            llm_model=vision_model,
            api_key=api_key,
            personality="friendly",
            vlm_interval=5.0
        )
        brain.start()

    # Create autonomous agent
    print("Creating autonomous agent...\n")

    print("Choose personality:")
    print("  1. Curious (explores and investigates everything)")
    print("  2. Cautious (careful, avoids obstacles)")
    print("  3. Chaotic (random, unpredictable)")

    try:
        choice = input("\nPersonality (1-3, default=1): ").strip() or "1"

        personality_map = {
            "1": "curious",
            "2": "cautious",
            "3": "chaotic"
        }

        personality = personality_map.get(choice, "curious")

    except (EOFError, KeyboardInterrupt):
        personality = "curious"

    print(f"\nSelected: {personality} personality\n")

    agent = AutonomousAgent(
        brain=brain,
        movement_callback=movement_callback,
        personality=personality
    )

    try:
        agent.start()

        print("\n" + "=" * 70)
        print(" ROBOT IS NOW AUTONOMOUS!")
        print(" Watch it wander, investigate, and occasionally get stuck.")
        print(" Press Ctrl+C to stop")
        print("=" * 70 + "\n")

        # Run for demo duration
        start_time = time.time()
        demo_duration = 60.0  # 1 minute demo

        while time.time() - start_time < demo_duration:
            # Print status every 10 seconds
            if int(time.time() - start_time) % 10 == 0:
                status = agent.get_status()
                print(f"\n📊 Status after {int(time.time() - start_time)}s:")
                print(f"   Mode: {status['mode']}")
                print(f"   Goal: {status['current_goal']}")
                print(f"   Decisions: {status['decisions_made']}")
                print(f"   Investigated: {status['objects_investigated']}")
                print(f"   Close calls: {status['close_calls']}\n")

            time.sleep(1)

        print("\n" + "=" * 70)
        print(" DEMO COMPLETE")
        print("=" * 70)

        # Final stats
        status = agent.get_status()
        print(f"\nFinal Statistics:")
        print(f"  Total runtime: {status['uptime']}s")
        print(f"  Decisions made: {status['decisions_made']}")
        print(f"  Objects investigated: {status['objects_investigated']}")
        print(f"  Close calls: {status['close_calls']}")
        print(f"  Times stuck: {status['stuck_counter']}")

    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")

    finally:
        agent.stop()

        if hasattr(brain, 'stop'):
            brain.stop()

        print("\nRobot stopped safely. ✓")


def show_architecture():
    """Show autonomous agent architecture."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║         AUTONOMOUS AGENT ARCHITECTURE                    ║
╚═══════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────┐
│                  DECISION LOOP (2 Hz)                    │
└────────────┬─────────────────────────────────────────────┘
             │
             ▼
    ┌────────────────┐
    │  Observe       │  ← Get scene from VLM (cached)
    │  Environment   │  ← Get obstacles from Hailo
    └────────┬───────┘
             │
             ▼
    ┌────────────────┐
    │  Think         │  ← Current goal (explore/investigate/follow)
    │  (AI Agent)    │  ← Personality traits
    └────────┬───────┘  ← Safety constraints
             │
             ▼
    ┌────────────────┐
    │  Act           │  ← Generate movement command
    │  (Movement)    │  ← Execute for duration
    └────────┬───────┘
             │
             │ Feedback
             └─────────────┐
                           ▼
                ┌──────────────────┐
                │  Learn/Adapt     │
                │  - Stuck counter │
                │  - Object memory │
                └──────────────────┘

BEHAVIORS:
├─ Exploring: Random walk, prefer forward, avoid obstacles
├─ Investigating: Approach object of interest
├─ Following: Track person, maintain distance
├─ Avoiding: Escape from blocked paths
└─ Resting: Pause when stuck too many times

PERSONALITIES:
├─ Curious: Investigates everything, asks questions
├─ Cautious: Moves slowly, backs up often
└─ Chaotic: Random spins, unpredictable movements

SAFETY:
├─ Stop if obstacle < 50cm
├─ Max 5 stuck attempts before resting
├─ Emergency stop always available
└─ Hailo real-time monitoring
""")


if __name__ == "__main__":
    print("\n")

    show_architecture()

    print("\nReady to unleash autonomous chaos?")
    user_input = input("\nRun demo? (y/n): ").strip().lower()

    if user_input == 'y':
        demo_autonomous_agent()
    else:
        print("\nDemo cancelled. Run 'python src/demo_autonomous.py' to try later.")
