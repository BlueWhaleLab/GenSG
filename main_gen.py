import os
import json
import time
import copy
import argparse
from concurrent.futures import ThreadPoolExecutor

import requests
from tqdm.auto import tqdm

from utils.basics import GEN_EVAL_PROMPT_TEMPLATE
from utils.validator import Validator


class Evaluator:
    
    def __init__(self, args) -> None:
        self.args = args
        self.model_name = args.model_name
        self.concurrency = args.concurrency
        
        self.headers = {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}"}
        self.data = self.load_data(args.test_data)
        
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
        question = GEN_EVAL_PROMPT_TEMPLATE.format(
            GOAL=level["goal"],
            OBJECTS=objects_str,
            SYNTHESIS_TABLE=synthesis_table_str,
            DECOMPOSITION_TABLE=decomposition_table_str
        )
        messages = [
            {"role": "user", "content": question}
        ]
        
        original_answer, reasoning_content, action_sequence_list, usage = self.send_requests(messages)
        
        answers["original_answer"] = original_answer
        answers["reasoning_content"] = reasoning_content
        answers["action_sequence_list"] = action_sequence_list
        answers["usage"] = usage
        
        return answers

    def evaluate(self):
        test_data = self.data[self.args.start:self.args.end]
        
        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            results = list(tqdm(
                executor.map(self.process_single_instance, test_data),
                total=len(test_data),
                desc=f"Evaluating data (Concurrency: {self.concurrency})"
            ))
            
        return results

    def _call_api(self, messages: list) -> requests.Response:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "reasoning": {"effort": "high"},
            # "quantizations": ["fp8"]
        }
    
        if self.args.provider:
            payload["provider"] = {"only": [self.args.provider]}
    
        return requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=(30, 600),
        )
        
    def _parse_actions(self, raw: str) -> list:
        try:
            clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
            actions = json.loads(clean)
            return [actions[k] for k in sorted(actions, key=lambda x: int(x))]
        except:
            return []
    
    def send_requests(self, messages: list) -> tuple[str, str, list, dict]:
        for attempt in range(self.args.max_retries):
            try:
                response = self._call_api(messages)
                response.raise_for_status()

                data = response.json()
                
                prompt_token = data['usage']['prompt_tokens']
                completion_tokens = data['usage']['completion_tokens']
                total_tokens = data['usage']['total_tokens']
                    
                usage = {
                    "prompt_tokens": prompt_token,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                }
                    
                message = data["choices"][0]["message"]

                original_answer = message["content"]
                reasoning_content = message.get("reasoning", "")
                
                if data["choices"][0]["finish_reason"] == "length":
                    return original_answer, reasoning_content, [], usage
                    
                action_sequence_list = self._parse_actions(original_answer)

                return original_answer, reasoning_content, action_sequence_list, usage
            
            except requests.exceptions.Timeout:
                print(f"[Attempt {attempt + 1}] Request timed out. Retrying...")
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code
                if status == 429:
                    wait = min(30 * (attempt + 1), 120)
                    print(f"[Attempt {attempt + 1}] Rate limited. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"[Attempt {attempt + 1}] HTTP {status}. Retrying...")
            except Exception as e:
                print(f"[Attempt {attempt + 1}] Error: {e}. Retrying...")

            time.sleep(10)

        return "Failed to get a valid response after multiple attempts.", "", [], {}
    
    @staticmethod
    def load_data(filepath: str) -> list:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Evaluation parameters
    parser.add_argument("--test_data", type=str, default="data/test.json")
    parser.add_argument("--model_name", type=str, default="deepseek/deepseek-v3.2", help="The name of the model to evaluate.")
    parser.add_argument("--provider", type=str, default="", help="The provider of the model (e.g., openai, azure). Leave empty to allow all providers.")
    parser.add_argument("--start", type=int, default=0, help="The starting index of the levels to evaluate.")
    parser.add_argument("--end", type=int, default=100, help="The ending index of the levels to evaluate.")
    
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent API requests.")
    parser.add_argument("--max_retries", type=int, default=3, help="Maximum number of retries for API calls.")
    
    
    args = parser.parse_args()
    
    evaluator = Evaluator(args)
    result = evaluator.evaluate()
    
    # Save results
    model_name = args.model_name.split("/")[-1]
    output_filename = f"Result_{model_name}_{args.start}_{args.end}.json"
    with open(output_filename, 'w') as f:
        json.dump(result, f, indent=2)
        
    # Calculate metrics
    time.sleep(2)
    validator = Validator(output_filename)
    result_summary = validator.validate()
    
    print(result_summary)
    
    
