"""
For Generative Evaluation of SG
"""

import json
from utils.validator import Validator

gen_filename = "result/Result_grok-4.20_0_100.json"
validator = Validator(gen_filename)
result_summary = validator.validate()

# calculate average output length in tokens
with open(gen_filename, 'r') as f:
    gen_data = json.load(f)

total_tokens = 0
token_cnt = 0
for item in gen_data:
    if 'usage' in item and 'completion_tokens' in item['usage']:
        total_tokens += item['usage']['completion_tokens']
        token_cnt += 1

print(result_summary)
print(f"Average output length (in tokens): {total_tokens / token_cnt:.2f}")



# """
# For Discriminative Evaluation of SG
# """
# import json

# with open("Discriminative_Results_minimax-m2.7_0_100.json", 'r') as f:
#     result = json.load(f)
    
# correct = 0
# parse_error = 0
# wrong = 0
# total_tokens = 0
# for item in result:
#     if 'completion_tokens' in item['usage']:
#         total_tokens += item['usage']['completion_tokens']
        
#     if item['model_predicted_goal'] == item['goal']:
#         correct += 1
#     elif item['model_predicted_goal'] is None or len(item['model_predicted_goal']) >= 20 or item['model_predicted_goal'] == "":
#         parse_error += 1
#     else:
#         wrong += 1

# print(f"Total instances: {len(result)}, Correct:{correct}, Parse Errors: {parse_error}, Wrong: {wrong},Accuracy: {correct / len(result):.2%}")
# print(f"Average output length (in tokens): {total_tokens / len(result):.2f}")