import re
import json
import random
from typing import Optional

from loguru import logger

from .basics import GameObject, STATES0
from .basics import REVERT_MAP, FORWARD_MAP, BACKWARD_MAP, RESET_MAP, REVERT_MAP
from .basics import SYNTHESIS_REPRESENTATION, DECOMPOSITION_REPRESENTATION


class GameEngine:
    
    def __init__(self, mode: str, data_file: Optional[str] = None) -> None:
        if mode not in ['play', 'validate']:
            raise ValueError(f"Invalid mode: {mode}, mode must be one of ['play', 'validate']")
        
        if mode == 'play':
            if not data_file:
                raise ValueError("Data file must be provided in play mode.")
        
            with open(data_file, "r") as f:
                self.level_list = json.load(f)
        else:
            self.level_list = []
    
    def load_single_level(self, goal: str, synthesis_table: dict, decomposition_table: dict, objects: list) -> None:
        # Update game environment
        self.objects = {}
        
        self.goal = goal
        self.synthesis_table = synthesis_table
        self.decomposition_table = decomposition_table
        
        # Create indexed synthesis table
        self.indexed_synthesis_table = {}
        for k, v in self.synthesis_table.items():
            for item in v:
                self.indexed_synthesis_table[item] = k

        self.synthesised_element_num = 0
        self.decomposed_element_num = 0
        
        for obj in objects:
            self.objects[obj['name']] = GameObject(name=obj['name'], initial_state=obj['initial_state'], locked=obj.get('locked', False))
            
    def get_level_data(self, level_index: Optional[int] = -1) -> dict:
        # Check whether the level data file is loaded
        if self.level_list == []:
            raise ValueError("Level data is empty.")
        
        level_data = {}
        
        if level_index is None or level_index == -1:
            selected_level = random.choice(self.level_list)
        else:
            if 0 <= level_index < len(self.level_list):
                selected_level = self.level_list[level_index]
            else:
                raise ValueError(f"Invalid level index: {level_index}, level index must be between 0 and {len(self.level_list) - 1}, or -1 for random selection.")
        
        level_data['goal'] = selected_level['goal']
        level_data['synthesis_table'] = selected_level['synthesis_table']
        level_data['decomposition_table'] = selected_level['decomposition_table']
        level_data['objects'] = selected_level['objects']
        
        return level_data

    def _update_state(self, current_state: str, action: str) -> str:
        if current_state not in STATES0:
            raise ValueError(f"Invalid current state: {current_state}, state must be one of {STATES0}, the synthesis and decomposition states are not valid current states.")
        
        if action == "FORWARD":
            new_state = FORWARD_MAP[current_state]
        elif action == "BACKWARD":
            new_state = BACKWARD_MAP[current_state]
        elif action == "REVERT":
            new_state = REVERT_MAP[current_state]
        elif action == "RESET":
            new_state = RESET_MAP[current_state]
        else:
            raise ValueError(f"Invalid action: {action}, action must be one of ['FORWARD', 'BACKWARD', 'REVERT', 'RESET']")
        
        return new_state
    
    def _apply_modification(self, obj_name: str, action: str) -> str:
        if obj_name not in self.objects:
            raise ValueError(f"Object {obj_name} does not exist in the current environment.")
        
        obj = self.objects[obj_name]
        if obj.locked:
            raise ValueError(f"Object {obj_name} is locked and cannot be modified.")
        
        new_state = self._update_state(current_state=obj.state, action=action)
        obj.state = new_state
        
        # check binding transmission and what to return 
        if obj.target:
            target_obj = self.objects[obj.target]
            target_new_state = self._update_state(current_state=target_obj.state, action=action)
            target_obj.state = target_new_state
            
        return new_state
    
    def execute_single_action(self, action_str: str) -> bool | str:
        match = re.match(r"([A-Z]+)\((.*)\)", action_str.strip())
        if not match:
            err_msg = f"Invalid command format: {action_str}, command must be in the format ACTION(arg1, arg2, ...)"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        action = match.group(1)
        args_str = match.group(2)
        args = [x.strip() for x in args_str.split(',')] if args_str else []
    
        if action in ['FORWARD', 'BACKWARD', 'REVERT', 'RESET']:
            if len(args) != 1:
                err_msg = f"Action {action} requires exactly one argument, but got {len(args)}: {args}"
                logger.error(err_msg)
                raise ValueError(err_msg)
            self._apply_modification(obj_name=args[0], action=action)
        elif action in ["SYNC", "BIND"]:
            if len(args) != 2:
                err_msg = f"Action {action} requires exactly two arguments, but got {len(args)}: {args}"
                logger.error(err_msg)
                raise ValueError(err_msg)
            target_name, source_name = args
            target = self.objects[target_name]
            source = self.objects[source_name]
            
            if action == "SYNC":
                if target.locked:
                    err_msg = f"Target object {target_name} is locked and cannot be modified."
                    logger.error(err_msg)
                    raise ValueError(err_msg)
                
                if target.target:  # Binding relationship ignores lock status, so we don't need to chekc the lock status of the target's target.
                    target.target.state = source.state
                
                target.state = source.state
            else:
                if target.state not in STATES0 or source.state not in STATES0:
                    err_msg = f"Both source and target objects must be in STATES0 ({STATES0}) to form a binding relationship, but got {source_name} in state {source.state} and {target_name} in state {target.state}."
                    logger.error(err_msg)
                    raise ValueError(err_msg)
                elif target.source or target.target:
                    err_msg = f"Target object {target_name} is already involved in another binding relationship and cannot be bound again. Current binding relationship: source={target.source}, target={target.target}"
                    logger.error(err_msg)
                    raise ValueError(err_msg)
                elif source.source or source.target:
                    err_msg = f"Source object {source_name} is already involved in another binding relationship and cannot be bound again. Current binding relationship: source={source.source}, target={source.target}"
                    logger.error(err_msg)
                    raise ValueError(err_msg)
                elif target_name == source_name:
                    err_msg = f"An object cannot be bound to itself: {source_name}"
                    logger.error(err_msg)
                    raise ValueError(err_msg)
                else:    
                    source.target = target
                    target.source = source
                    
        elif action == "SYNTHESIS":
            if len(args) == 1:
                err_msg = f"SYNTHESIS action requires at least two arguments: , but got only {len(args)} argument: {args[0]}"
                logger.error(err_msg)
                raise ValueError(err_msg)

            result_string = "".join([self.objects[name].state for name in args])
            
            # Clear the binding relationships of the source objects before deletion
            for name in args:
                if self.objects[name].source:
                    self.objects[name].source.target = None
                if self.objects[name].target:
                    self.objects[name].target.source = None
                    
                del self.objects[name]
            
            # Check whether the result string can be synthesized into a new object
            if result_string in self.indexed_synthesis_table:
                result_string = self.indexed_synthesis_table[result_string]
            
            # Add synthesized object to the environment
            synthesised_element_id = f"{SYNTHESIS_REPRESENTATION}{self.synthesised_element_num + 1}"
            self.objects[synthesised_element_id] = GameObject(name=synthesised_element_id, initial_state=result_string, locked=True)  # The synthesized object is locked by default, as it cannot be modified by basic actions, but it can be used for further synthesis and decomposition.
            self.synthesised_element_num += 1
            
            return result_string  # For verification
        elif action == "DECOMPOSITION":
            if len(args) != 1:
                err_msg = f"DECOMPOSITION action requires exactly one argument: the object to be decomposed, but got {len(args)} arguments: {args}"
                logger.error(err_msg)
                raise ValueError(err_msg)
            
            if self.objects[args[0]].state not in self.decomposition_table:
                err_msg = f"Object {args[0]} in state {self.objects[args[0]].state} cannot be decomposed as it is not in the decomposition table. Decomposition table keys: {list(self.decomposition_table.keys())}"
                logger.error(err_msg)
                raise ValueError(err_msg)
            
            result = self.decomposition_table[self.objects[args[0]].state]
            
            # Add decomposed objects to the environment
            for obj in result:
                obj_name = f"{DECOMPOSITION_REPRESENTATION}{self.decomposed_element_num + 1}"
                self.objects[obj_name] = GameObject(name=obj_name, initial_state=obj, locked=False if obj in STATES0 else True)
                self.decomposed_element_num += 1
                
            # Delete the decomposed object from the environment
            del self.objects[args[0]]
        else:
            err_msg = f"Unknown action: {action}, action must be one of ['FORWARD', 'BACKWARD', 'REVERT', 'RESET', 'SYNC', 'BIND', 'SYNTHESIS', 'DECOMPOSITION']"
            logger.error(err_msg)
            raise ValueError(err_msg)
        
        # Return execution status for verification
        return True
        
    def verify_solution(self, solution_list: list) -> str:
        try:
            for action in solution_list:
                res = self.execute_single_action(action)
                
                if res == self.goal:
                    return "SUCCESS"
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return "Command Execution Error"
        
        return "Failed to obtain goal"

    def print_status(self):
        print("\n--- Current Status ---")
        for name, obj in self.objects.items():
            print(obj)
        print("\n--- Environment ---")
        print(f"Goal: {self.goal}\nSynthesis table: {self.synthesis_table}\nDecomposition table: {self.decomposition_table}")
        print("----------------------")
            
    def play_in_terminal_mode(self) -> None:
        print("Welcome to the Game! Please select a level to start playing.")
        selected_level = int(input(f"Please enter a level index between 0 and {len(self.level_list) - 1}, or enter -1 to select a random level: "))
        
        level_data = self.get_level_data(level_index=selected_level)
        self.load_single_level(goal=level_data['goal'], synthesis_table=level_data['synthesis_table'], decomposition_table=level_data['decomposition_table'], objects=level_data['objects'])
        self.print_status()
        
        while True:
            try:
                cmd = input("\n> ")
                if cmd.lower() in ['exit', 'quit']:
                    break
                result = self.execute_single_action(cmd)
                self.print_status()
                if result and result == self.goal:
                    print("🎉 YOU WIN! 🎉")
                    print("🎉 YOU WIN! 🎉")
                    print("🎉 YOU WIN! 🎉")
                    
                    print("Do you want to play again? (y/n)")
                    play_again = input("> ")
                    if play_again.lower() == 'y':
                        selected_level = int(input(f"Please enter a level index between 0 and {len(self.level_list) - 1}, or enter -1 to select a random level: "))
                        
                        level_data = self.get_level_data(level_index=selected_level)
                        self.load_single_level(goal=level_data['goal'], synthesis_table=level_data['synthesis_table'], decomposition_table=level_data['decomposition_table'], objects=level_data['objects'])
        
                        self.print_status()
                    else:
                        break
            except Exception as e:
                print(f"Error: {e}")
       
    def get_level_len(self) -> int:
        return len(self.level_list)
                

# if __name__ == "__main__":
#     engine = GameEngine(mode="play", data_file="level_data.json")
#     engine.play_in_terminal_mode()

            
            
            