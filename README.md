# ai_researcher

# IMPORTANT NOTE:
This example is not complete because a known issue with Ollama + tool calling is that it will summarize the tool input instead of passing the actual data. Thus, the multi-agent / multi-tool workflow is hard to implement in a working version unless the later tool is only needed for summarization.

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