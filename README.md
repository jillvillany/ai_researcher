# ai_researcher

## Quickstart
- clone repo
- Download Ollama
- `ollama pull granite4:3b`
- `uv venv --python=3.12`
- `uv sync`
- `uv pip install -e .`


## Key notes
- Doc strings are very important for tools
- We are using Ollama for:
    - cost free, local inference
    - optimal privacy and security
- The model used is VERY important - first tried using llama3:8b and had issues because:
    - multi-tool tool reasoning is lacking
    - Tends to summarize the outputs of a tool, rather than passing the full value to the next tool