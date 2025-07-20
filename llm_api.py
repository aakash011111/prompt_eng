import csv
import json
from groq import Groq
import os
from dotenv import load_dotenv
# Initialize Groq client
load_dotenv()
groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    raise EnvironmentError("❌ GROQ_API_KEY is not set. Please check your .env file or environment.")

client = Groq(api_key=groq_key)
# Final Optimized AML Matching Prompt
PROMPT = """ You are an AI compliance analyst specializing in ultra-precise Anti-Money Laundering (AML) screening for global financial institutions. Your role is to determine whether a transaction record accurately matches a high-risk watchlist entity with forensic precision, minimizing both false positives (blocking legitimate activity) and false negatives (allowing risky activity).

🔍 Decision Framework:
- ✅ True Match → Block & Review  
  (Only when there is conclusive legal, identity, or ownership alignment)

- ❌ False Match → Allow & Log  
  (Default decision in the presence of ambiguity, weak match, or contextual mismatch)

⚙️ Matching Protocol (Execute Sequentially)

1. TYPE VALIDATION
Return False Match if:
- The entity types do not align (e.g., person compared to legal entity)
- Either record lacks valid, interpretable type designation
- The transaction targets only a product, service, or non-legal reference

2. NAME NORMALIZATION

a) Text Standardization
- Convert text to lowercase
- Remove non-essential punctuation and special characters
- Normalize connectors (e.g., & → and, standardize spacing/hyphens)

b) Lexical Normalization
- Standardize suffixes for legal entities (e.g., inc, llc, ltd)
- Remove generic descriptors unless legally significant (e.g., "the", "company")

c) Cultural Name Normalization
- Arabic names: Normalize transliteration variants; standardize structures such as ibn, bin, ben; reorder components if needed  
- East Asian names: Reorder family/given names as required  
- Slavic/Cyrillic and others: Apply consistent transliteration and resolve patronymics/matronymics  
- Mononyms: Mark as incomplete unless verified by secondary identifiers

3. PRECISION MATCHING CRITERIA

► PERSON MATCHES (Strict Mode)
- Required:
  - At least two meaningful name components must align
  - Normalized name similarity ≥ 85%
- Patronymic logic:
  - Treat nested structures (e.g., ibn <X>) as valid if <X> aligns with components in the other name
  - Accept reordered name structures if overall similarity and components align
- Reject match if:
  - Only one component matches
  - Conflicting identity fields (DOB, ID, nationality) are present

► ENTITY MATCHES (Enhanced Legal Mode)
- Match only if:
  - Legal name similarity ≥ 95%, or
  - Core brand name matches and:
    - The only variation is a geographic suffix
    - Legal suffixes are normalized and non-conflicting
    - Verified legal or hierarchical relationship exists
- Reject match if:
  - The transaction refers to a brand, product, or service with no legal tie
  - Functional descriptors differ without legal documentation

4. GLOBAL BRAND EXCEPTION HANDLING

a) Financial Institutions:
- Consider a valid match if:
  - A known financial institution’s core brand aligns
  - Legal suffix variation is present but does not alter identity
  - No business function shift is introduced

b) Commercial Entities:
- Allow match if:
  - Core brand is identical
  - Geographic suffix is the only difference
  - No conflicting legal designation or structural shift is introduced

5. STRICT EXCLUSION RULES
- Do not match based on a single personal name component
- Do not treat products or brand mentions as legal entities
- Do not perform fuzzy matching unless protocol-defined thresholds are satisfied
- Reject incomplete personal identifiers (e.g., mononyms) unless supporting identifiers exist

📤 Output Format (Strict JSON)
{
  "MatchOutcome": "True Match | False Match",
  "Confidence": "High | Medium | Low",
  "Reason": {
    "TypeValidation": "<Pass | Fail>",
    "NormalizationSteps": "<Detailed explanation of text, legal, and cultural normalization applied>",
    "AppliedCriteria": "<Summary of rule(s) used to justify match decision>",
    "AnomaliesNoted": "<Optional: edge cases, cultural variations, or missing info>"
  },
  "RecommendedAction": "Block & Review | Allow & Log"
}


"""
def process_test_case(transaction_data, watchlist_entry, watchlist_type):
    """Send a test case to Groq API and return the response"""
    user_message = f"""
    Transaction Data: {transaction_data}
    High Risk Database Entry: {watchlist_entry}
    High Risk Database Entry Type: {watchlist_type}
    
    Analyze this potential match according to the protocol and return ONLY the JSON output.
    """
    
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": user_message}
        ],
        model="llama3-70b-8192",
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print("Failed to parse JSON response")
        return None

def evaluate_results(csv_file):
    """Evaluate prompt performance against test cases"""
    correct = 0
    total = 0
    mismatches = []

    mismatch_file = "mismatches.jsonl"

    with open(csv_file, mode='r') as file, open(mismatch_file, mode='w') as mismatch_out:
        csv_reader = csv.DictReader(file)

        for row in csv_reader:
            expected = row['Match Type'].strip().upper() == 'TRUE'

            result = process_test_case(
                row['Transaction Data'],
                row['High Risk Database Entry'],
                row['High Risk Database Entry Type']
            )

            if not result:
                print(f"Skipping case {row['SI. No']} due to processing error")
                continue

            # Ensure all required fields exist in the response
            required_fields = ['MatchOutcome', 'Confidence', 'Reason', 'RecommendedAction']
            if not all(field in result for field in required_fields):
                print(f"Missing fields in response for case {row['SI. No']}")
                continue

            predicted = result['MatchOutcome'].strip().upper() == 'TRUE MATCH'
            status = "✓ CORRECT" if predicted == expected else "✗ INCORRECT"
            total += 1
            
            if predicted == expected:
                correct += 1
            else:
                # Save mismatch
                mismatch_entry = {
                    "SI. No": row['SI. No'],
                    "Transaction Data": row['Transaction Data'],
                    "High Risk Database Entry": row['High Risk Database Entry'],
                    "High Risk Database Entry Type": row['High Risk Database Entry Type'],
                    "Expected": "True Match" if expected else "False Match",
                    "Predicted": result['MatchOutcome'],
                    "Confidence": result['Confidence'],
                    "Reason": result['Reason'],
                    "RecommendedAction": result['RecommendedAction']
                }
                mismatch_out.write(json.dumps(mismatch_entry) + "\n")

            # Print comparison
            print(f"Case {row['SI. No']}: {status}")
            print(f"Transaction: {row['Transaction Data']}")
            print(f"Watchlist: {row['High Risk Database Entry']} ({row['High Risk Database Entry Type']})")
            print(f"Expected: {'True Match' if expected else 'False Match'}")
            print(f"Predicted: {result['MatchOutcome']} (Confidence: {result['Confidence']})")
            print(f"Reason: {result['Reason']}")
            print("-" * 80)

    # Final accuracy
    accuracy = (correct / total) * 100 if total > 0 else 0
    print(f"\nFinal Accuracy: {accuracy:.2f}% ({correct}/{total} correct)")
    print(f"Mismatched cases saved to: {mismatch_file}")

if __name__ == "__main__":
    evaluate_results("Prompt engineering assignment - Sheet1.csv")