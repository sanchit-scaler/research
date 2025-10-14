# Sample GPT API Call

A simple Python script to test OpenAI API connectivity and model responses.

## Features

- Automatically loads environment variables from `.env` file
- Supports multiple OpenAI models (GPT-4o-mini, GPT-5, etc.)
- Flexible model selection via command line arguments or environment variables
- Detailed error handling and informative output

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure your API key:**
   Create a `.env` file in the project root:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   OPENAI_MODEL=gpt-4o-mini  # Optional: default model
   ```

## Usage

### Basic Usage
```bash
# Use default model from .env or fallback to gpt-4o-mini
uv run python main.py

# Specify a model via command line
uv run python main.py gpt-5
uv run python main.py gpt-4o-mini
```

### Model Selection Priority
1. **Command line argument** (highest priority)
2. **OPENAI_MODEL environment variable** (from .env file)
3. **Default fallback** (gpt-4o-mini)

### Examples
```bash
# Test with GPT-5
uv run python main.py gpt-5

# Test with GPT-4o-mini
uv run python main.py gpt-4o-mini

# Use model from .env file
uv run python main.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_MODEL` | Default model to use | `gpt-4o-mini` |

## Output

The script will:
- Display the model being used
- Show the AI's response to a creative writing prompt
- Confirm successful API connection
- Provide detailed error messages if something goes wrong

## Troubleshooting

- **"Missing dependency"**: Run `uv sync` to install required packages
- **"OPENAI_API_KEY not set"**: Check your `.env` file exists and contains the API key
- **"Request failed"**: Verify your API key is valid and the model is available in your account
