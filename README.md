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
    - NOTE: If you get the error "No module named 'ai_researcher'", rerun `uv pip install -e .`
- Run the app
    - `python ai_researcher/app.py`


## Notes
- First started with gtp-5.4-mini but that struggled to create a report in a cohesive way, so needed to switch to gpt-5.4. However, this is still having difficulty with an orchestrator agent workflow.