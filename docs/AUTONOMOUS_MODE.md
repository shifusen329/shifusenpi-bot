# Autonomous Mode - AI-Powered Semi-Autonomous Operation

## Overview

Your hexapod robot can now operate autonomously like a Roomba, but with:
- **Vision** (Hailo 26 TOPS + VLM)
- **Personality** (LLM-driven dialogue)
- **Intelligence** (Goal-oriented behavior)
- **Chaos** (Questionable decision-making guaranteed)

## Quick Start

```bash
# Run autonomous demo
python src/demo_autonomous.py

# Choose personality:
# 1. Curious - Investigates everything
# 2. Cautious - Careful and slow
# 3. Chaotic - Completely unpredictable

# Watch it wander around for 60 seconds
```

## Architecture

```
┌──────────────────────────────────────────────┐
│          AUTONOMOUS AGENT                    │
│  (Decision-making loop - 2 Hz)               │
└──────────────────┬───────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
┌──────────┐  ┌────────┐  ┌──────────┐
│  Vision  │  │  LLM   │  │Movement  │
│  System  │  │Dialogue│  │ Control  │
│          │  │        │  │          │
│ Hailo    │  │Persona-│  │ Servos   │
│ + VLM    │  │lity    │  │ + IMU    │
└──────────┘  └────────┘  └──────────┘
```

## Operational Modes

### 1. Exploring (Default)
**What it does:**
- Wanders randomly
- Prefers moving forward
- Avoids obstacles
- Occasionally changes direction

**Behavior by personality:**
- **Curious**: 30% chance to investigate interesting objects
- **Cautious**: Moves slowly, stops if too many obstacles
- **Chaotic**: 10% chance to randomly spin

```python
# Example exploration decision
if safe_to_move_forward:
    move_forward(duration=2.0)
elif can_turn_left:
    turn_left(angle=45)
else:
    backup()
```

### 2. Investigating
**What it does:**
- Approaches object of interest
- Turns to face it
- Moves closer until "near"
- Asks LLM about it
- Returns to exploring

**Triggers:**
- Curious personality sees something new
- User command: "investigate the cup"
- Random chance while exploring

```python
agent.set_goal("investigate", target="cup")
# Robot will approach the cup and examine it
```

### 3. Following
**What it does:**
- Tracks detected person
- Maintains safe distance
- Turns to keep person in view
- Stops if person too close

**Triggers:**
- User command: "follow me"
- Person detected repeatedly
- LLM suggests following

```python
agent.set_goal("follow")
# Robot follows nearest person
```

### 4. Stuck/Resting
**What it does:**
- Stops moving
- Waits 5 seconds
- Resets stuck counter
- Resumes exploring

**Triggers:**
- Blocked 5+ times in a row
- No safe directions available
- User command: "rest"

## Personalities

### Curious
**Traits:**
- Investigates new objects (30% chance)
- Asks LLM questions about things
- Prefers exploring unknown areas
- Rarely rests

**Example behavior:**
```
[Agent] 🤔 Curious about chair...
[Agent] 🔍 Investigating chair (center)...
[Agent] ✅ Reached chair! Marking as investigated.
[Agent] 💭 "This chair looks comfortable! Should I try to climb it?"
```

### Cautious
**Traits:**
- Moves slowly
- Backs up frequently
- Rests if too many obstacles
- Avoids risky paths

**Example behavior:**
```
[Agent] ⚠️ Obstacle detected: ['chair', 'table']
[Agent] 😰 Too many obstacles, resting...
[Agent] Movement: STOP {'action': 'STOP', 'duration': 3.0}
```

### Chaotic
**Traits:**
- Random spins (10% chance)
- Unpredictable movements
- Ignores conventional paths
- Maximum entertainment value

**Example behavior:**
```
[Agent] 🌀 Feeling spicy, spinning!
[Agent] Movement: SPIN {'action': 'SPIN', 'duration': 1.8}
[Agent] 🚶 Exploring BACKWARD...
```

## Safety Features

### Real-Time Obstacle Avoidance
```python
# Hailo detects obstacle < 50cm
→ Immediate STOP
→ Find safe direction
→ Turn or backup
→ Resume movement
```

### Stuck Detection
```python
stuck_counter = 0
while moving:
    if blocked:
        stuck_counter += 1
    if stuck_counter >= 5:
        mode = RESTING
        wait(5.0)
```

### Emergency Stop
```python
# Always available:
agent.stop()  # Stops all movement immediately
```

## Decision-Making Flow

```
Every 2 seconds:
├─ Get latest scene from VLM (cached)
├─ Check Hailo for obstacles
├─ Check current goal
└─ Decide action
    ├─ Safety: Obstacle ahead? → Avoid
    ├─ Goal: Investigating? → Approach target
    ├─ Goal: Following? → Track person
    └─ Default: Explore randomly
```

## Integration with Robot Control

### Setup
```python
from async_brain import AsyncRobotBrain
from autonomous_agent import AutonomousAgent

# Initialize brain
brain = AsyncRobotBrain(
    vlm_url=os.getenv('LITELLM_BASE_URL'),
    vlm_model=os.getenv('VISION_MODEL'),
    llm_url=os.getenv('LITELLM_BASE_URL'),
    llm_model=os.getenv('PERSONALITY_MODEL'),
    api_key=os.getenv('LITELLM_API_KEY'),
    vlm_interval=5.0
)

brain.start()

# Create agent
agent = AutonomousAgent(
    brain=brain,
    movement_callback=robot_control.execute_command,
    personality="curious"
)

agent.start()
```

### Movement Callback
```python
def movement_callback(command: dict):
    """Execute movement command from agent."""
    action = command.get('action')

    if action == 'FORWARD':
        robot.move_forward(duration=command.get('duration', 1.0))
    elif action == 'TURN_LEFT':
        robot.turn_left(angle=command.get('angle', 45))
    elif action == 'TURN_RIGHT':
        robot.turn_right(angle=command.get('angle', 45))
    elif action == 'BACKWARD':
        robot.move_backward(duration=command.get('duration', 1.0))
    elif action == 'STOP':
        robot.stop()
```

## Monitoring & Stats

### Real-Time Status
```python
status = agent.get_status()

# Returns:
{
    "mode": "exploring",
    "running": True,
    "personality": "curious",
    "current_goal": "investigate",
    "decisions_made": 145,
    "objects_investigated": 8,
    "close_calls": 3,
    "stuck_counter": 0,
    "uptime": 120.5,
    "last_movement": "TURN_LEFT"
}
```

### Logging
```
[Agent] 🚶 Exploring FORWARD...
  🤖 Movement: FORWARD {'action': 'FORWARD', 'duration': 2.3}
[Agent] 🤔 Curious about cup...
[Agent] 🔍 Investigating cup (left)...
  🤖 Movement: TURN_LEFT {'action': 'TURN_LEFT', 'angle': 20}
[Agent] ✅ Reached cup! Marking as investigated.
[Agent] 💭 "This cup looks empty. Should I find something to fill it?"
```

## Common Scenarios

### Scenario 1: Exploring a Room
```
1. Agent starts in EXPLORING mode
2. Moves forward for 2 seconds
3. VLM sees: chair, table, person
4. Curious personality → investigate chair
5. Turns toward chair
6. Approaches chair
7. LLM responds: "This looks like a comfy place to rest!"
8. Resumes exploring
```

### Scenario 2: Getting Stuck
```
1. Moves forward
2. Hailo detects obstacle
3. Tries to turn left → blocked
4. Tries to turn right → blocked
5. Backs up
6. Still blocked
7. stuck_counter = 5
8. Enters RESTING mode for 5 seconds
9. Resumes with cleared stuck_counter
```

### Scenario 3: Person Following
```
1. User: "follow me"
2. Agent sets goal: FOLLOWING
3. VLM detects person (right side)
4. Turns right to face person
5. Moves forward
6. Person moves left
7. Tracks and turns left
8. Maintains distance
9. Person stops → Agent stops
```

## Configuration Options

### Agent Parameters
```python
agent = AutonomousAgent(
    brain=brain,
    movement_callback=callback,
    personality="curious"  # curious, cautious, chaotic
)

# Adjust decision frequency
agent.decision_interval = 2.0  # seconds

# Adjust safety threshold
agent.safe_distance_threshold = 50.0  # cm

# Adjust stuck tolerance
agent.max_stuck_count = 5
```

### Goal Management
```python
# Set custom goal
agent.set_goal(
    goal_type="investigate",
    target="cup",
    priority=8  # 0-10
)

# Clear goal (return to exploring)
agent.set_goal("explore")
```

## Troubleshooting

### Robot Just Spins
**Cause**: Chaotic personality or stuck loop
**Solution**:
```python
# Check personality
status = agent.get_status()
print(status['personality'])  # If "chaotic", that's expected!

# Switch to cautious
agent.stop()
agent = AutonomousAgent(brain, callback, personality="cautious")
agent.start()
```

### Robot Won't Move
**Cause**: Scene data shows all directions blocked
**Solution**:
```python
# Check scene
scene = brain.get_latest_scene()
print(scene.safe_directions)  # Should have at least one direction

# If empty, VLM might be too conservative
# Manually set safe directions or adjust prompt
```

### Too Many Close Calls
**Cause**: Moving too fast or safety threshold too low
**Solution**:
```python
# Increase safety distance
agent.safe_distance_threshold = 100.0  # cm (was 50)

# Reduce movement duration
# Edit _explore_behavior() to use shorter durations
```

## Future Enhancements

### Planned Features
- [ ] **Memory**: Remember visited locations, create map
- [ ] **Learning**: Improve decisions based on past actions
- [ ] **Social**: Recognize and interact with specific people
- [ ] **Tasks**: Complete multi-step goals ("fetch the cup")
- [ ] **Collaboration**: Multiple robots coordinating

### Advanced Behaviors
- [ ] **Patrolling**: Follow predefined routes
- [ ] **Guarding**: Stay in area, alert on intrusions
- [ ] **Fetching**: Find object and return it
- [ ] **Cleaning**: Actually work like a Roomba
- [ ] **Entertainment**: Play games, perform tricks

## Best Practices

1. **Start with Curious** personality for testing
2. **Monitor logs** to understand decision-making
3. **Use simulation mode** before hardware deployment
4. **Set up** emergency stop button/command
5. **Test in** open area first (not near stairs!)
6. **Gradually increase** autonomy time
7. **Review stats** to tune parameters

## Conclusion

You now have a semi-autonomous robot that can:
- ✅ See (Hailo 26 TOPS + VLM)
- ✅ Hear (WM8960 + STT)
- ✅ Speak (WM8960 + TTS)
- ✅ Think (LLM personality)
- ✅ Act (Autonomous movement)
- ✅ Learn (Memory of objects/locations)

**It's like a Roomba**, except it has opinions, asks questions, and might investigate your shoes instead of vacuuming them.

Enjoy the chaos! 🤖🔥

---

**Next**: Fine-tune personality, add custom goals, train on your environment
**See**: `src/demo_autonomous.py` for examples
