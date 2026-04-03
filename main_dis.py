import os
import json
import time
import copy
import argparse
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm.auto import tqdm

from utils.basics import DIS_EVAL_PROMPT_TEMPLATE


class Evaluator:
    
    def __init__(self, args) -> None:
        self.args = args
        self.model_name = args.model_name
        self.concurrency = args.concurrency
        
        self.headers = {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}"}
        self.data = self.load_data(args.level_data)
        
    def process_single_instance(self, level):
        """Handle single instance"""
        answers = copy.deepcopy(level)
        
        # Get synthesis table and decomposition table
        synthesis_table = level.get("synthesis_table", {})
        synthesis_table_str = "\n".join([f"{key}: {synthesis_table[key]}" for key in sorted(synthesis_table.keys())])
            
        decomposition_table = level.get("decomposition_table", {})
        decomposition_table_str = "\n".join([f"{key}: {decomposition_table[key]}" for key in sorted(decomposition_table.keys())])
            
        # Get objects str
        objects_list = level.get("objects", [])
        objects_str = "\n".join([str(obj) for obj in objects_list])
            
        # Get prompt
        question = DIS_EVAL_PROMPT_TEMPLATE.format(
            OBJECTS=objects_str,
            SYNTHESIS_TABLE=synthesis_table_str,
            DECOMPOSITION_TABLE=decomposition_table_str,
            SOLUTION=level["solution"],
        )
        
        messages = [
            {"role": "user", "content": question}
        ]
        
        original_answer, reasoning_content, usage = self.send_requests(messages)
            
        answers["model_predicted_goal"] = original_answer
        answers["reasoning_content"] = reasoning_content
        answers["usage"] = usage
            
        return answers
        
    def _call_api(self, messages: list) -> requests.Response:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "reasoning": {"effort": "high"},
        }
    
        if self.args.provider:
            payload["provider"] = {"only": [self.args.provider]}
    
        return requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=self.headers,
            json=payload,
        )
        
    def send_requests(self, messages: list) -> tuple[str, str, dict]:
        for attempt in range(self.args.max_retries):
            try:
                response = self._call_api(messages)
                response.raise_for_status()
                
                response_json = response.json()
                    
                original_answer = response_json["choices"][0]["message"]["content"]
                    
                prompt_token = response_json['usage']['prompt_tokens']
                completion_tokens = response_json['usage']['completion_tokens']
                total_tokens = response_json['usage']['total_tokens']
                    
                usage = {
                    "prompt_tokens": prompt_token,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
                    
                reasoning_content = response_json["choices"][0]["message"]['reasoning']
                    
                return original_answer, reasoning_content, usage

            except requests.exceptions.HTTPError as e:
                print(f"[Attempt {attempt + 1}] HTTP {e.response.status_code}. Retrying...")
            except Exception as e:
                print(f"[Attempt {attempt + 1}] Error: {e}. Retrying...")

            time.sleep(10)
        
        return "Failed to get a valid response after multiple attempts.", "", {}
    
    def evaluate(self):
        test_data = self.data[self.args.start:self.args.end]
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            results = list(tqdm(
                executor.map(self.process_single_instance, test_data),
                total=len(test_data),
                desc=f"Evaluating data (Concurrency: {self.concurrency})"
            ))
            
        return results
    
    @staticmethod
    def load_data(filepath: str) -> list:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Evaluation parameters
    parser.add_argument("--level_data", type=str, default="data/test.json")
    parser.add_argument("--model_name", type=str, default="openai/gpt-5.4", help="The name of the model to evaluate.")
    parser.add_argument("--provider", type=str, default="", help="The provider of the model (e.g., openai, azure).")
    parser.add_argument("--start", type=int, default=0, help="The starting index of the levels to evaluate.")
    parser.add_argument("--end", type=int, default=100, help="The ending index of the levels to evaluate.")
    
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent API requests.")
    parser.add_argument("--max_retries", type=int, default=3, help="Maximum number of retries for API calls.")
    
    args = parser.parse_args()
    
    evaluator = Evaluator(args)
    result = evaluator.evaluate()
    
    # Save results
    model_name = args.model_name.split("/")[-1]
    output_filename = f"Discriminative_Results_{model_name}_{args.start}_{args.end}.json"
    with open(output_filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Calculate metrics
    correct = 0
    parse_error = 0
    wrong = 0
    for item in result:
        if item['model_predicted_goal'] == item['goal']:
            correct += 1
        elif len(item['model_predicted_goal']) >= 20 or item['model_predicted_goal'] == "":
            parse_error += 1
        else:
            wrong += 1
    
    print(f"Total instances: {len(result)}, Correct: {correct}, Parse Errors: {parse_error}, Wrong: {wrong}, Accuracy: {correct / len(result):.2%}")

        
    
    
    
    
    
