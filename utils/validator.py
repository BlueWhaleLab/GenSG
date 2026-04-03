import json

from tqdm.auto import tqdm

from .engine import GameEngine


class Validator:
    def __init__(self, result_file) -> None:
        self.data = self.load_data(result_file)
        self.engine = GameEngine(mode="validate", data_file=result_file)
        
    def validate(self) -> str:
        data_len = len(self.data)
        print(f"Total instances in the dataset: {data_len}")
        
        correct = 0
        command_error = 0
        failed = 0
        for idx in tqdm(range(data_len), desc="Validating Answers"):
            ins = self.data[idx]
            self.engine.load_single_level(goal=ins['goal'], synthesis_table=ins['synthesis_table'], decomposition_table=ins['decomposition_table'], objects=ins['objects'])
            
            result = self.engine.verify_solution(ins.get('action_sequence_list', []))
            if result == "SUCCESS":
                correct += 1
                print(f"correct action sequence length: {len(ins.get('action_sequence_list', []))}, solution length: {len(ins.get('solution', []))}")
            elif result == "Command Execution Error":
                command_error += 1
            else:
                failed += 1
        
        result_summary = f"Validation completed. Correct: {correct}, Command Execution Errors: {command_error}, Failed: {failed}, Accuracy: {correct / data_len:.2%}"
        
        return result_summary
            
        
    @staticmethod
    def load_data(filepath: str) -> list:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    
    

# if __name__ == "__main__":
#     import argparse
    
#     parser = argparse.ArgumentParser(description="Validate the generated levels.")
#     parser.add_argument('--level_data', type=str, default="nosys_evaluation_results_gemini-3.1-pro-preview_0_5.json", help="Path to the level data JSON file.")
    
#     args = parser.parse_args()
    
#     validator = Validator(args)
#     validator.validate()
    