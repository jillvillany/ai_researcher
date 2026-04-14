# ai_researcher

## Quickstart
- clone repo
- Create an OpenAI API Key
    - Log into OpenAI API Platform
    - Click "Create API Keys"
- Create a `.env` file that looks like the below
```
OPENAI_API_KEY={insert key here}
```
- `ollama run llama3`
- `uv venv --python=3.12`
- `uv sync`
- `uv pip install -e .`


## Key notes
- Doc strings are very important for tools