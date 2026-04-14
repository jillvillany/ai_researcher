# ai_researcher

## Quickstart
- clone repo
- Download Ollama
- `ollama run llama3`
- `uv venv --python=3.12`
- `uv sync`
- `uv pip install -e .`


## Key notes
- Doc strings are very important for tools
- We are using Ollama for:
    - cost free, local inference
    - optimal privacy and security
- BUT that also means:
    - multi-tool tool reasoning is lacking - pipeline should be deterministic for agent tool calling
        - Tends to summarize the outputs of a tool, rather than passing the full value to the next tool