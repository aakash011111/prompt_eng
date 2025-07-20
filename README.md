🧠 AML Matching Evaluator (Groq LLM-Based)
This Python project evaluates the performance of a Large Language Model (LLM) for Anti-Money Laundering (AML) entity matching. It uses the Groq API and a custom-built prompt to test whether transaction entries match high-risk entities with forensic precision.

📌 Overview
The script loads a CSV file containing test cases (transactions and watchlist entries) and submits each to Groq’s llama3-70b-8192 model using a highly structured prompt. It parses and evaluates the model's JSON output, compares the prediction to the expected result, and logs mismatches for review.

🔁 Evaluation Logic
True Match → Block & Review

False Match → Allow & Log

For each case, the script:

Sends structured inputs to Groq LLM.

Applies a deterministic AML prompt with strict rules on name normalization, entity validation, cultural logic, etc.

Compares the model's prediction (True Match or False Match) against the expected value in the CSV.

Prints result and logs any mismatches to mismatches.jsonl.

