# ai_researcher

## Quickstart
- Fork the following repo: https://github.com/jillvillany/ai_researcher
- Clone the forked repo
- Download Ollama: https://ollama.com/download
- `ollama pull granite4:3b`
- `uv venv --python=3.12`
- `uv sync`
- `playwright install`
- `python ai_researcher/app.py`


## Key notes
- Doc strings are very important for tools
- We are using Ollama for:
    - cost free, local inference
    - optimal privacy and security
- The model used is VERY important - first tried using llama3:8b and had issues because:
    - multi-tool tool reasoning is lacking
    - Tends to summarize the outputs of a tool, rather than passing the full value to the next tool