import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def query_llm(text):
    if text == "":
        return ""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    prompt = generatePrompt(text)
    try:
        completion = client.chat.completions.create(
            model=os.getenv("LLM_MODEL"),
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"LLM request failed: {e}")
        return ""


def generatePrompt(text):
    prompt = f"""
Read the following text and extract all trading signals, regardless of the exact wording or format. 
For each signal, output a single line containing the ticker symbol, the price, and the action (LONG or SHORT), in the format:

<number>) $<TICKER> - $<PRICE> <LONG/SHORT>

- Only output a line if all three elements (ticker, price, and direction) are clearly present and understandable.
- If the text is ambiguous, incomplete, or does not contain a valid trading signal, do not output anything for that line.
- Ignore notes, commentary, stop loss, BE alarm, and portfolio summary lines.
- Do not include any explanations or extra text, just one signal per line.
- Fully Capitalize the ticker and action in output

Example output:
1) $GOOG - $100.15 SHORT
2) $AAPL - $150.15 LONG

Text to parse:
{text}
"""
    return prompt