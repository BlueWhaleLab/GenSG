# STATES
STATES0 = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

STATES1 = ['I', 'K', 'L', 'M', 'N', 'P', 'Q', 'R']
STATES2 = ['S', 'T', 'U', 'V', 'W']
STATES3 = ['X', 'Y', 'Z']

# SPECIAL STATES
BASIC_REPRESENTATION = "O"
SYNTHESIS_REPRESENTATION = "H"
DECOMPOSITION_REPRESENTATION = "J"

# Action map
REVERT_MAP = {'A': 'G', 'B': 'E', 'C': 'F', 'D': 'D', 'E': 'B', 'F': 'C', 'G': 'A'}
FORWARD_MAP = {'A': 'C', 'B': 'D', 'C': 'E', 'D': 'F', 'E': 'G', 'F': 'A', 'G': 'B'}
BACKWARD_MAP = {v: k for k, v in FORWARD_MAP.items()}
RESET_MAP = {c: 'A' for c in STATES0}


class GameObject:
    def __init__(self, name: str, initial_state: str, locked: bool = False):
        self.name = name
        self.state = initial_state
        self.locked = locked
        
        self.target = None
        self.source = None
        
    def __repr__(self) -> str:
        lock_tag = "[LOCKED]" if self.locked else ""
        bind_tag = f"BIND to {self.target.name}" if self.target else ""
        return f"{self.name}: {self.state} {lock_tag}{bind_tag}"
        

GEN_EVAL_PROMPT_TEMPLATE = """
You are playing a state-transformation puzzle game. Your goal is to apply a sequence of logical actions to a set of initial objects to synthesize a specific target object state.

### Objects and States
- **Basic States (`STATES0`)**: `A`, `B`, `C`, `D`, `E`, `F`, `G`.
- **Higher-level States**: (I, K, L, M, N, P, Q, R, S, T, U, V, W, X, Y, Z).
- **Naming Conventions**: 
  - Basic objects given at the start start with `O` (e.g., `O1`, `O2`).
  - Synthesized objects start with `H` (e.g., `H1`, `H2`).
  - Decomposed objects start with `J` (e.g., `J1`, `J2`).
  - Once an object is consumed (via Synthesis or Decomposition), its name and ID are permanently retired. New objects always receive strictly increasing IDs.
- **Lock Status**: Objects can be `[LOCKED]` or unlocked. Locked objects cannot be directly modified by basic actions or as the direct target of a `SYNC` action. 

### Basic Actions
These actions can **only** be applied to objects currently in `STATES0` (A-G). Objects originating from decomposition can be subjected to these actions as long as their new states belong to `STATES0`.
- **`FORWARD(obj)`**: Advances the state 2 steps cyclically. (`A`->`C`, `B`->`D`, `C`->`E`, `D`->`F`, `E`->`G`, `F`->`A`, `G`->`B`).
- **`BACKWARD(obj)`**: Reverses the state 2 steps cyclically. (`C`->`A`, `D`->`B`, etc.)
- **`REVERT(obj)`**: Applies a specific mapping: `A`->`G`, `B`->`E`, `C`->`F`, `D`->`D`, `E`->`B`, `F`->`C`, `G`->`A`.
- **`RESET(obj)`**: Changes the state of the object back to `A`.

### Advanced Actions
These actions connect two objects. There is no restriction on the states of the objects involved, except that the `target` cannot be locked.
- **`SYNC(target, source)`**: Copies the state of the `source` to the `target`.
  - The `target` cannot be locked. 
  - If the `target` has a bound target (via `BIND`), the updated state propagates to that bound object, **ignoring the bound target's lock status**.
- **`BIND(target, source)`**: Binds the `source` to the `target`. 
  - **Propagation**: Any state-changing basic action applied to the `source` will automatically propagate to the `target`.
  - **Unchangeable**: Once bound, the relationship is permanent. 
  - **Exclusivity**: Each object can participate in a maximum of **one** binding relationship (it can be a source OR a target, but not both).
  - **Removal**: An object can be freed from a binding and reused in new bindings **only** if its current binding partner is destroyed via a `SYNTHESIS` action.
  - **Applicability**: Binding relationships can be established between objects in any STATES, but the effects of basic actions will only propagate if the target is in `STATES0`.

### Synthesis and Decomposition Actions
- **`SYNTHESIS(obj1, obj2, ...)`**: Combines multiple objects together. 
  - Any objects can be synthesized together without restriction. The provisional result is determined by concatenating the states of the specified objects in the exact order they are provided.
  - If the concatenated string exists in the **Synthesis Table**, it successfully resolves to the new higher-level state. (Note: A single higher-level state can have multiple valid synthesis paths defined in the table).
  - Source objects are permanently destroyed, severing any of their existing binding relationships.
  - The newly created `H`-prefix object is locked by default.
- **`DECOMPOSITION(obj)`**: Breaks apart an object into multiple smaller parts based on the **Decomposition Table**.
  - Unlike Synthesis, each element in the Decomposition Table has exactly **one** predefined decomposition result.
  - You can **only** apply this action to objects whose states exist as keys in the Decomposition Table. Attempting to decompose any other object will cause an error.
  - The source object is permanently destroyed.
  - Newly generated `J`-prefix objects are unlocked if their resulting state is in `STATES0`, otherwise they are locked.

### Task Specifications
You will be provided with:
1. The **Goal** state.
2. The initial environment configuration (available objects, their names, states, and lock statuses).
3. The **Synthesis Table** and **Decomposition Table**.

Output your sequence of actions step-by-step to achieve the goal state. Use the format `ACTION(arg1, arg2...)` (e.g., `FORWARD(O1)`, `BIND(O2, O1)`, `SYNTHESIS(O1, O2)`). Output them in JSON format with step numbers as keys and action strings as values, like this:
```json
{{
  "1": "FORWARD(O1)",
  "2": "BIND(O2, O1)",
  "3": "SYNTHESIS(O1, O2)"
}}
```

## Note
You should give the action sequence directly without any explanation. Moreover, you should try to find the action sequence with the least number of steps to achieve the goal state.

Now, here is the specific puzzle for you to solve:

Goal: {GOAL},
Initial Objects: \n{OBJECTS},
Synthesis Table: \n{SYNTHESIS_TABLE},
Decomposition Table: \n{DECOMPOSITION_TABLE}

Please provide the step-by-step action sequence to achieve the goal state.
"""

DIS_EVAL_PROMPT_TEMPLATE = """
You are playing a state-transformation puzzle game. The rules of the game are as follows:

### Objects and States
- **Basic States (`STATES0`)**: `A`, `B`, `C`, `D`, `E`, `F`, `G`.
- **Higher-level States**: (I, K, L, M, N, P, Q, R, S, T, U, V, W, X, Y, Z).
- **Naming Conventions**: 
  - Basic objects given at the start start with `O` (e.g., `O1`, `O2`).
  - Synthesized objects start with `H` (e.g., `H1`, `H2`).
  - Decomposed objects start with `J` (e.g., `J1`, `J2`).
  - Once an object is consumed (via Synthesis or Decomposition), its name and ID are permanently retired. New objects always receive strictly increasing IDs.
- **Lock Status**: Objects can be `[LOCKED]` or unlocked. Locked objects cannot be directly modified by basic actions or as the direct target of a `SYNC` action. 

### Basic Actions
These actions can **only** be applied to objects currently in `STATES0` (A-G). Objects originating from decomposition can be subjected to these actions as long as their new states belong to `STATES0`.
- **`FORWARD(obj)`**: Advances the state 2 steps cyclically. (`A`->`C`, `B`->`D`, `C`->`E`, `D`->`F`, `E`->`G`, `F`->`A`, `G`->`B`).
- **`BACKWARD(obj)`**: Reverses the state 2 steps cyclically. (`C`->`A`, `D`->`B`, etc.)
- **`REVERT(obj)`**: Applies a specific mapping: `A`->`G`, `B`->`E`, `C`->`F`, `D`->`D`, `E`->`B`, `F`->`C`, `G`->`A`.
- **`RESET(obj)`**: Changes the state of the object back to `A`.

### Advanced Actions
These actions connect two objects. There is no restriction on the states of the objects involved, except that the `target` cannot be locked.
- **`SYNC(target, source)`**: Copies the state of the `source` to the `target`.
  - The `target` cannot be locked. 
  - If the `target` has a bound target (via `BIND`), the updated state propagates to that bound object, **ignoring the bound target's lock status**.
- **`BIND(target, source)`**: Binds the `source` to the `target`. 
  - **Propagation**: Any state-changing basic action applied to the `source` will automatically propagate to the `target`.
  - **Unchangeable**: Once bound, the relationship is permanent. 
  - **Exclusivity**: Each object can participate in a maximum of **one** binding relationship (it can be a source OR a target, but not both).
  - **Removal**: An object can be freed from a binding and reused in new bindings **only** if its current binding partner is destroyed via a `SYNTHESIS` action.
  - **Applicability**: Binding relationships can be established between objects in any STATES, but the effects of basic actions will only propagate if the target is in `STATES0`.

### Synthesis and Decomposition Actions
- **`SYNTHESIS(obj1, obj2, ...)`**: Combines multiple objects together. 
  - Any objects can be synthesized together without restriction. The provisional result is determined by concatenating the states of the specified objects in the exact order they are provided.
  - If the concatenated string exists in the **Synthesis Table**, it successfully resolves to the new higher-level state. (Note: A single higher-level state can have multiple valid synthesis paths defined in the table).
  - Source objects are permanently destroyed, severing any of their existing binding relationships.
  - The newly created `H`-prefix object is locked by default.
- **`DECOMPOSITION(obj)`**: Breaks apart an object into multiple smaller parts based on the **Decomposition Table**.
  - Unlike Synthesis, each element in the Decomposition Table has exactly **one** predefined decomposition result.
  - You can **only** apply this action to objects whose states exist as keys in the Decomposition Table. Attempting to decompose any other object will cause an error.
  - The source object is permanently destroyed.
  - Newly generated `J`-prefix objects are unlocked if their resulting state is in `STATES0`, otherwise they are locked.

### Task Specifications
You will be provided with:
1. The initial environment configuration (available objects, their names, states, and lock statuses).
2. The **Synthesis Table** and **Decomposition Table**.
3. The **Action** sequence.

Your task is to first understand the rules and then simply execute the actions one by one and then return the result of the final action.

## Note
You should give the result of the final action directly without any explanation. 

Now, here is the specific puzzle for you to solve:

Initial Objects: \n{OBJECTS},
Synthesis Table: \n{SYNTHESIS_TABLE},
Decomposition Table: \n{DECOMPOSITION_TABLE}
Action Sequence: {SOLUTION},

Please provide the result string of the final action.
"""
        
        

