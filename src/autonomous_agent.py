"""Autonomous Agent - Semi-autonomous Roomba-style wandering AI.

Like a Roomba, but with vision, personality, and questionable decision-making.
"""

import time
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import threading

import numpy as np

from async_brain import AsyncRobotBrain, SceneUnderstanding
from hailo_vision import NavigationData


class AgentMode(Enum):
    """Autonomous agent operational modes."""
    EXPLORING = "exploring"      # Random wandering
    INVESTIGATING = "investigating"  # Found something interesting
    STUCK = "stuck"              # Can't find path
    RESTING = "resting"          # Taking a break
    FOLLOWING = "following"      # Following a person
    FLEEING = "fleeing"          # Avoiding danger


@dataclass
class AgentGoal:
    """Current goal for autonomous agent."""
    type: str  # "explore", "investigate", "follow", "rest"
    target: Optional[str] = None  # Object or person to interact with
    priority: int = 0  # 0-10
    created_at: float = 0.0


class AutonomousAgent:
    """Semi-autonomous wandering agent with AI decision-making."""

    def __init__(
        self,
        brain: AsyncRobotBrain,
        movement_callback,
        personality: str = "curious"
    ):
        """
        Initialize autonomous agent.

        Args:
            brain: Robot brain instance
            movement_callback: Function to send movement commands
            personality: Agent personality (curious, cautious, chaotic)
        """
        self.brain = brain
        self.movement_callback = movement_callback
        self.personality = personality

        # State
        self.mode = AgentMode.EXPLORING
        self.current_goal: Optional[AgentGoal] = None
        self.running = False

        # Memory
        self.visited_locations = []  # Track where we've been
        self.interesting_objects = set()  # Objects we've seen
        self.stuck_counter = 0  # Times we've been stuck
        self.last_movement = None
        self.exploration_bias = "random"  # "left", "right", "random"

        # Timing
        self.last_decision_time = 0.0
        self.decision_interval = 2.0  # Make decisions every 2 seconds
        self.action_start_time = 0.0
        self.action_duration = 0.0

        # Safety
        self.safe_distance_threshold = 50.0  # cm
        self.max_stuck_count = 5

        # Stats
        self.decisions_made = 0
        self.objects_investigated = 0
        self.close_calls = 0
        self.start_time = time.time()

        # Threading
        self.agent_thread: Optional[threading.Thread] = None

    def start(self):
        """Start autonomous operation."""
        if self.running:
            print("[Agent] Already running")
            return

        self.running = True

        # Set initial goal
        self.current_goal = AgentGoal(
            type="explore",
            priority=5,
            created_at=time.time()
        )

        # Start agent loop
        self.agent_thread = threading.Thread(target=self._agent_loop, daemon=True)
        self.agent_thread.start()

        print(f"[Agent] Autonomous agent started ({self.personality} personality)")

    def stop(self):
        """Stop autonomous operation."""
        if not self.running:
            return

        self.running = False

        # Stop movement
        self._execute_movement("STOP")

        if self.agent_thread:
            self.agent_thread.join(timeout=3.0)

        print("[Agent] Autonomous agent stopped")

    def _agent_loop(self):
        """Main autonomous decision-making loop."""
        print("[Agent] Agent loop started")

        while self.running:
            try:
                current_time = time.time()

                # Check if it's time for a new decision
                if current_time - self.last_decision_time >= self.decision_interval:
                    self._make_decision()
                    self.last_decision_time = current_time

                # Check if current action is complete
                if (self.action_duration > 0 and
                    current_time - self.action_start_time >= self.action_duration):
                    self._execute_movement("STOP")
                    self.action_duration = 0

                time.sleep(0.1)

            except Exception as e:
                print(f"[Agent] Error in agent loop: {e}")
                time.sleep(1.0)

        print("[Agent] Agent loop ended")

    def _make_decision(self):
        """Make an autonomous decision based on current state."""
        # Get current sensor data
        scene = self.brain.get_latest_scene()
        # nav_data would come from Hailo (if integrated)

        # Decide what to do
        action = self._decide_action(scene)

        # Execute action
        if action:
            self._execute_action(action)
            self.decisions_made += 1

    def _decide_action(self, scene: Optional[SceneUnderstanding]) -> Optional[Dict]:
        """
        Decide what action to take based on scene.

        Args:
            scene: Current scene understanding

        Returns:
            Action dict or None
        """
        # Safety first: Check for obstacles
        if scene and scene.obstacles:
            if self._is_path_blocked(scene):
                return self._avoid_obstacle(scene)

        # Check current goal
        if self.current_goal:
            if self.current_goal.type == "explore":
                return self._explore_behavior(scene)

            elif self.current_goal.type == "investigate":
                return self._investigate_behavior(scene)

            elif self.current_goal.type == "follow":
                return self._follow_behavior(scene)

        # Default: explore
        return self._explore_behavior(scene)

    def _explore_behavior(self, scene: Optional[SceneUnderstanding]) -> Dict:
        """
        Exploration behavior - wander around randomly.

        Args:
            scene: Current scene

        Returns:
            Movement action
        """
        if self.personality == "curious":
            # Curious: Look for interesting things
            if scene and scene.objects and random.random() < 0.3:
                # 30% chance to investigate something
                obj = random.choice(scene.objects)
                print(f"[Agent] 🤔 Curious about {obj['name']}...")
                self.current_goal = AgentGoal(
                    type="investigate",
                    target=obj['name'],
                    priority=6,
                    created_at=time.time()
                )
                return self._investigate_behavior(scene)

        elif self.personality == "cautious":
            # Cautious: Move slowly, prefer known paths
            if self.stuck_counter > 2:
                print("[Agent] 😰 Too many obstacles, resting...")
                return {"command": "STOP", "duration": 3.0}

        elif self.personality == "chaotic":
            # Chaotic: Random, unpredictable movements
            if random.random() < 0.1:  # 10% chance
                spin_duration = random.uniform(0.5, 2.0)
                print("[Agent] 🌀 Feeling spicy, spinning!")
                return {"command": "SPIN", "duration": spin_duration}

        # Default exploration: Random walk
        direction = self._choose_exploration_direction(scene)

        print(f"[Agent] 🚶 Exploring {direction}...")

        if direction == "FORWARD":
            return {"command": "FORWARD", "duration": random.uniform(1.0, 3.0)}
        elif direction == "LEFT":
            return {"command": "TURN_LEFT", "angle": random.uniform(30, 90)}
        elif direction == "RIGHT":
            return {"command": "TURN_RIGHT", "angle": random.uniform(30, 90)}
        elif direction == "BACKWARD":
            return {"command": "BACKWARD", "duration": random.uniform(0.5, 1.5)}

    def _investigate_behavior(self, scene: Optional[SceneUnderstanding]) -> Dict:
        """
        Investigation behavior - approach object of interest.

        Args:
            scene: Current scene

        Returns:
            Movement action
        """
        if not scene or not self.current_goal:
            return self._explore_behavior(scene)

        target = self.current_goal.target

        # Find target object in scene
        target_obj = None
        for obj in scene.objects:
            if obj['name'] == target:
                target_obj = obj
                break

        if not target_obj:
            print(f"[Agent] 🤷 Lost sight of {target}, back to exploring")
            self.current_goal = AgentGoal(type="explore", priority=5, created_at=time.time())
            return self._explore_behavior(scene)

        # Move toward object based on position
        position = target_obj.get('position', 'center')

        print(f"[Agent] 🔍 Investigating {target} ({position})...")

        if position == 'left':
            return {"command": "TURN_LEFT", "angle": 20}
        elif position == 'right':
            return {"command": "TURN_RIGHT", "angle": 20}
        elif position == 'center':
            # Close enough?
            if target_obj.get('distance') == 'near':
                print(f"[Agent] ✅ Reached {target}! Marking as investigated.")
                self.interesting_objects.add(target)
                self.objects_investigated += 1

                # Ask brain about it
                response = self.brain.get_personality_response(
                    f"I found a {target}. What should I do with it?",
                    scene_context=scene
                )
                print(f"[Agent] 💭 {response.text}")

                # Back to exploring
                self.current_goal = AgentGoal(type="explore", priority=5, created_at=time.time())
                return {"command": "STOP", "duration": 2.0}
            else:
                return {"command": "FORWARD", "duration": 1.0}

    def _follow_behavior(self, scene: Optional[SceneUnderstanding]) -> Dict:
        """
        Following behavior - track a person.

        Args:
            scene: Current scene

        Returns:
            Movement action
        """
        if not scene or scene.people_count == 0:
            print("[Agent] 😢 Lost the person, back to exploring")
            self.current_goal = AgentGoal(type="explore", priority=5, created_at=time.time())
            return self._explore_behavior(scene)

        # Find person in objects
        person = None
        for obj in scene.objects:
            if obj['name'] == 'person':
                person = obj
                break

        if not person:
            return self._explore_behavior(scene)

        # Follow person
        position = person.get('position', 'center')
        distance = person.get('distance', 'far')

        if distance == 'near':
            # Too close, stop
            return {"command": "STOP", "duration": 1.0}
        elif position == 'left':
            return {"command": "TURN_LEFT", "angle": 15}
        elif position == 'right':
            return {"command": "TURN_RIGHT", "angle": 15}
        else:
            return {"command": "FORWARD", "duration": 1.0}

    def _choose_exploration_direction(
        self,
        scene: Optional[SceneUnderstanding]
    ) -> str:
        """Choose direction for exploration."""
        # Use scene safe directions if available
        if scene and scene.safe_directions:
            safe_dirs = scene.safe_directions

            # Prefer forward if safe
            if "forward" in safe_dirs and random.random() < 0.6:
                return "FORWARD"

            # Otherwise pick random safe direction
            if safe_dirs:
                choice = random.choice(safe_dirs)
                if choice == "left":
                    return "LEFT"
                elif choice == "right":
                    return "RIGHT"
                elif choice == "forward":
                    return "FORWARD"

        # Fallback: Random with bias
        if self.exploration_bias == "left":
            choices = ["FORWARD", "LEFT", "LEFT", "RIGHT"]
        elif self.exploration_bias == "right":
            choices = ["FORWARD", "RIGHT", "RIGHT", "LEFT"]
        else:
            choices = ["FORWARD", "FORWARD", "LEFT", "RIGHT", "BACKWARD"]

        return random.choice(choices)

    def _is_path_blocked(self, scene: SceneUnderstanding) -> bool:
        """Check if path is blocked."""
        # Check for obstacles in center
        for obj in scene.objects:
            if obj.get('position') == 'center' and obj.get('distance') == 'near':
                if obj['name'] in ['chair', 'table', 'wall', 'person']:
                    return True
        return len(scene.obstacles) > 2

    def _avoid_obstacle(self, scene: SceneUnderstanding) -> Dict:
        """Avoid detected obstacle."""
        print(f"[Agent] ⚠️ Obstacle detected: {scene.obstacles}")

        self.stuck_counter += 1
        self.close_calls += 1

        # If stuck too many times, give up and rest
        if self.stuck_counter >= self.max_stuck_count:
            print("[Agent] 😵 Too many obstacles! Taking a break...")
            self.mode = AgentMode.STUCK
            self.stuck_counter = 0
            return {"command": "STOP", "duration": 5.0}

        # Choose escape direction
        if "left" in scene.safe_directions:
            return {"command": "TURN_LEFT", "angle": 45}
        elif "right" in scene.safe_directions:
            return {"command": "TURN_RIGHT", "angle": 45}
        else:
            # No safe direction, back up
            return {"command": "BACKWARD", "duration": 1.0}

    def _execute_action(self, action: Dict):
        """Execute movement action."""
        command = action.get("command", "STOP")
        duration = action.get("duration", 0.0)
        angle = action.get("angle", 0)

        self._execute_movement(command, angle=angle)

        self.action_start_time = time.time()
        self.action_duration = duration
        self.last_movement = command

    def _execute_movement(self, command: str, angle: int = 0):
        """
        Send movement command to robot.

        Args:
            command: Movement command
            angle: Angle for turns
        """
        if self.movement_callback:
            cmd_dict = {"action": command}

            if angle:
                cmd_dict["angle"] = angle

            self.movement_callback(cmd_dict)

    def set_goal(self, goal_type: str, target: Optional[str] = None, priority: int = 5):
        """
        Set a new goal for the agent.

        Args:
            goal_type: Goal type (explore, investigate, follow, rest)
            target: Target object or person
            priority: Goal priority
        """
        self.current_goal = AgentGoal(
            type=goal_type,
            target=target,
            priority=priority,
            created_at=time.time()
        )

        print(f"[Agent] 🎯 New goal: {goal_type} {target if target else ''}")

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "mode": self.mode.value,
            "running": self.running,
            "personality": self.personality,
            "current_goal": self.current_goal.type if self.current_goal else None,
            "decisions_made": self.decisions_made,
            "objects_investigated": self.objects_investigated,
            "close_calls": self.close_calls,
            "stuck_counter": self.stuck_counter,
            "uptime": round(time.time() - self.start_time, 1),
            "last_movement": self.last_movement
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
