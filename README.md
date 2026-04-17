# ai_researcher

## Quickstart
- Fork the following repo: https://github.com/jillvillany/ai_researcher
- Clone the forked repo: `git clone git@github.com:jillvillany/ai_researcher.git`
- Create a `.env` file that looks like the below
    ```
    OPENAI_API_KEY={insert key here}
    SERPAPI_KEY={insert key here}
    ```
- Create an OpenAI API Key
    - Log into OpenAI API Platform
    - Click "Create API Keys"
- Create a SerpAPI API key
- Create Python env 
    - `uv venv --python=3.12`
- Install requirements
    - `uv sync`
    - `playwright install`
- Run the app
    - `python ai_researcher/app.py`


## Notes
- gtp-5.4-mini and gtp-5.4 were too judgemental of what Arxiv returned and would not just summarize the articles returned by the search
- gtp-5.4-mini did much better with a general internet search but was variable in performance even with temperature set to 0