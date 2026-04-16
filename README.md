# ai_researcher

## Quickstart
- Fork the following repo: https://github.com/jillvillany/ai_researcher
- Clone the forked repo: `git clone ...`
- Create an OpenAI API Key
    - Log into OpenAI API Platform
    - Click "Create API Keys"
- Create a `.env` file that looks like the below
    ```
    OPENAI_API_KEY={insert key here}
    ```
- Create Python env 
    - `uv venv --python=3.12`
- Install requirements
    - `uv sync`
    - `playwright install`
    - `uv pip install -e .`
- Run the app
- `python ai_researcher/app.py`
