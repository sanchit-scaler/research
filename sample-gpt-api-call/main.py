#!/usr/bin/env python3
"""
Quick check that your OpenAI API key works by sending a simple
"Hi" prompt and printing the model's reply.

Usage:
  - Place your API key in a .env file: OPENAI_API_KEY=your_key_here
  - Optional: choose model via OPENAI_MODEL or first CLI arg
  - Run: python3 main.py [model]

Notes:
  - Automatically loads environment variables from .env file
  - Defaults to a widely available, low-cost model if none provided.
  - If you try an unavailable model (e.g., "gpt-5"), you'll likely
    get a model-not-found error even if your key is valid.
"""

import os
import sys

try:
    from openai import OpenAI
    from dotenv import load_dotenv
except Exception as e:
    print(
        f"Missing dependency: {e}",
        file=sys.stderr,
    )
    sys.exit(1)

# Load environment variables from .env file
load_dotenv()


def main() -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        return 1

    # Model selection priority:
    # 1. Command line argument (if provided and valid)
    # 2. OPENAI_MODEL environment variable (from .env file)
    # 3. Default fallback (gpt-4o-mini)
    model = None
    
    # Check command line argument first
    if len(sys.argv) > 1:
        model = sys.argv[1].strip()
        if not model:
            print("WARNING: Empty model argument provided, falling back to environment variable.", file=sys.stderr)
            model = None
    
    # Fall back to environment variable if no CLI arg or invalid CLI arg
    if not model:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    print(f"Using model: {model}")

    client = OpenAI(api_key=api_key)

    prompt = "Write a short creative story about a robot learning to paint. Include specific details about colors and techniques."
    try:
        resp = client.responses.create(model=model, input=prompt)
        # New SDKs expose a convenient .output_text; fall back if unavailable.
        text = getattr(resp, "output_text", None)
        if not text:
            # Basic extraction fallback for older SDK responses
            try:
                text = resp.output[0].content[0].text
            except Exception:
                text = str(resp)

        print(f"Model: {model}")
        print("Reply:")
        print(text.strip())
        print("\nSuccess: API key is valid and request succeeded.")
        return 0
    except Exception as e:
        print(f"Request failed for model '{model}'.", file=sys.stderr)
        print(str(e), file=sys.stderr)
        # Common causes:
        #  - Invalid/absent API key (Authentication error)
        #  - Model not found or unavailable in your account/region
        #  - Network/connectivity issues
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
