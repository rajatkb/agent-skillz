# ARC-AGI-3 Game State Schema Reference

Exact types from `arcengine/enums.py` (source: https://github.com/arcprize/ARCEngine).

## GameState

```python
class GameState(str, Enum):
    NOT_PLAYED = "NOT_PLAYED"     # Just started or after RESET
    NOT_FINISHED = "NOT_FINISHED" # In progress
    WIN = "WIN"                   # Agent won all levels
    GAME_OVER = "GAME_OVER"       # Died/lost — should RESET and retry
```

## GameAction

```python
class GameAction(Enum):
    RESET  = (0, SimpleAction)
    ACTION1 = (1, SimpleAction)
    ACTION2 = (2, SimpleAction)
    ACTION3 = (3, SimpleAction)
    ACTION4 = (4, SimpleAction)
    ACTION5 = (5, SimpleAction)
    ACTION6 = (6, ComplexAction)   # Requires x,y on 64×64 grid
    ACTION7 = (7, SimpleAction)
```

- `action.is_simple()` / `action.is_complex()`
- `action.set_data({"x": int, "y": int})` for complex actions
- `action.action_data` (the SimpleAction or ComplexAction instance)

## SimpleAction / ComplexAction

```python
class SimpleAction(BaseModel):
    game_id: str = ""

class ComplexAction(BaseModel):
    game_id: str = ""
    x: int = Field(0, ge=0, le=63)
    y: int = Field(0, ge=0, le=63)
```

## FrameData (what your agent receives)

```python
class FrameData(BaseModel):
    game_id: str = ""            # e.g. "ls20-9607627b"
    frame: list[list[list[int]]] = []  # pixel grid [H][W][C], 64×64 max
    state: GameState = GameState.NOT_PLAYED
    levels_completed: int = 0    # levels beaten so far
    win_levels: int = 0          # total levels to beat
    action_input: ActionInput    # the action that produced this frame
    guid: Optional[str] = None   # unique session ID
    full_reset: bool = False     # True after full game reset
    available_actions: list[int] = []  # valid action IDs at this state
```

## FrameDataRaw (internal engine format)

```python
class FrameDataRaw(BaseModel):
    # Same fields as FrameData EXCEPT:
    # frame is PrivateAttr: List[ndarray] — numpy arrays, not serialized
    # Use .frame property to access (returns List[ndarray])
```

When the Agent framework converts `FrameDataRaw` → `FrameData`, it does:
```python
out = FrameData(
    frame=[arr.tolist() for arr in raw.frame],  # numpy → nested lists
    ...  # all other fields copied directly
)
```

## Agent Contract

```python
class Agent(ABC):
    MAX_ACTIONS = 80  # max actions per game; enforced framework-side

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        """Return True when agent should stop playing."""
        ...

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        """Examine latest_frame, decide next action, return it."""
        ...
```

- `frames` — full history of all frames since game started
- `latest_frame` — the current observation (same as `frames[-1]`)
- Key properties on `Agent`: `self.game_id`, `self.name`, `self.state`, `self.levels_completed`

## Environment

- **Grid**: max 64×64, cell values 0-15 (integers representing colors/states)
- **Origin**: (0,0) at top-left, (x,y) format
- **Available games**: Each game has an ID like `ls20`, `ls20-9607627b` (with version hash)
- **Game ID format**: `<game_name>-<version>`
