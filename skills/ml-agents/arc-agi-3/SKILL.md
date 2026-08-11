---
name: arc-agi-3
category: ml-agents
tags: [arc-prize, interactive-reasoning, agent-benchmark, game-environments]
version: 1
description: ARC-AGI-3 agent development — understanding game state, FrameData/GameAction types, interactive game loop, and notebook setup.
---

# ARC-AGI-3 Agent Development

ARC-AGI-3 is an **interactive reasoning benchmark** where agents explore novel game environments, acquire goals, build world models, and adapt. Unlike ARC-AGI-1/2 (static input/output grid puzzles), ARC-AGI-3 is turn-based — agents receive observation frames and return actions.

## Key Concepts

### Game Loop

1. Agent receives a `FrameData` observation from the environment
2. Agent calls `is_done(frames, latest_frame) -> bool` — stop on WIN
3. If not done, agent calls `choose_action(frames, latest_frame) -> GameAction`
4. Action is submitted, next `FrameData` is received
5. Repeat until done or `MAX_ACTIONS` limit reached (default 80)

### GameState values

- `NOT_PLAYED` — game just started or was reset; send RESET action
- `NOT_FINISHED` — game in progress
- `WIN` — agent won; stop
- `GAME_OVER` — agent died/lost; send RESET to retry level

### FrameData (the observation)

See `references/game-schema.md` for the full type definition.

Key fields:
- `frame: list[list[list[int]]]` — pixel grid data (64×64, values 0-15)
- `state: GameState` — current game state
- `levels_completed: int` — levels beaten so far
- `win_levels: int` — total levels to beat
- `available_actions: list[int]` — action IDs valid at this state
- `guid: str | None` — session tracking

### Actions (GameAction)

8 possible actions (RESET + ACTION1-7). ACTION6 is complex (takes x,y on 64×64 grid). Check `action.is_complex()` and use `action.set_data({"x": ..., "y": ...})`.

### Environment: 64×64 grid, cell values 0-15

Coordinate system: (0,0) at top-left, (x,y) format. Grid max 64×64.

## Setup

### Install

```bash
pip install arc-agi
# or
uv add arc-agi
```

### API Key

```bash
export ARC_API_KEY="your-key-here"
```

Register at https://three.arcprize.org

### Quick Play (REPL)

```python
import arc_agi
from arcengine import GameAction, GameState

arc = arc_agi.Arcade()
env = arc.make("ls20", render_mode="terminal")
obs = env.step(GameAction.ACTION1)
print(arc.get_scorecard())
```

### Writing an Agent

Subclass `Agent` from `agents.agent`, implement two methods:

```python
class MyAgent(Agent):
    def is_done(self, frames, latest_frame) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(self, frames, latest_frame) -> GameAction:
        # Use latest_frame.frame (pixels), state, available_actions
        # GameAction.ACTION6 needs set_data({"x": ..., "y": ...})
        return GameAction.ACTION1
```

## Pitfalls

- **ARC-AGI-1/2 ≠ ARC-AGI-3**: ARC-AGI-1 and ARC-AGI-2 (static grid puzzles) are solved via **LLM API-based program synthesis**, NOT GPU training. The winning approaches (Berman ~$8.42/task, epang080516 ~$2.56/task) use frontier LLMs to generate Python functions that solve grid transformations — no GPU rental needed. Do not recommend GPU training for ARC-AGI-1/2. See `references/cost-efficient-arc-agi.md` for details.
- **RESET on death**: After `GAME_OVER`, send `GameAction.RESET` — don't stop (unless you want to).
- **Complex action data**: Only ACTION6 needs coordinates; calling `set_data` on simple actions errors silently.
- **frame format**: `FrameData.frame` is `list[list[list[int]]]` — convert to numpy at inference time if needed (the engine internally uses `FrameDataRaw` with `numpy.ndarray`).
- **MAX_ACTIONS**: Default 80; framework enforces it. Hit it and the agent exits regardless of game state.
- **Per-game heuristics**: Check `self.game_id` prefix (e.g. `ls20-9607627b`) to specialize strategies per game.
- **Reasoning field**: Attach to the GameAction instance directly (`action.reasoning = {...}`). Must be JSON-serializable, max 16KB.
- **Kaggle submission**: The starter repo's `scripts/build_notebook.py` splices `my_agent.py` into a Kaggle notebook. Keep agent logic in that single file.

## Reference

- Full docs: https://docs.arcprize.org/
- Game schema: https://docs.arcprize.org/game-schema
- PyPI: `arc-agi`, `arcengine`
- Kaggle starter: https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter
- Agents framework: https://github.com/arcprize/ARC-AGI-3-Agents
- Engine source: https://github.com/arcprize/ARCEngine
