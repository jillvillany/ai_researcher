import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ai_researcher.tools.report_tools import convert_html_to_pdf


def _extract_text_content(content):
    if isinstance(content, str):
        return content

    text_parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text_parts.append(item.get("text", ""))

    return "\n".join(part for part in text_parts if part).strip()


def _extract_html_document(text):
    if "```html" in text:
        return text.split("```html", 1)[1].split("```", 1)[0].strip()

    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()

    return text.strip()


class ReportAgent():
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_REPORT_MODEL", "gpt-5.4-mini"),
            temperature=0,
        )

    def run(self, report_data):
        response = self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You create polished, modern AI research reports. "
                        "Return only a complete HTML document with inline CSS."
                    )
                ),
                HumanMessage(
                    content=(
                        "Use the research data below to generate a simple, modern report. "
                        "Start with <!doctype html> and end with </html>.\n"
                        "The title should just be 'Research Report Dated {toodays date}'"
                        f"Report Data:\n{report_data}"
                    )
                ),
            ]
        )
        report_html = _extract_html_document(_extract_text_content(response.content))
        print("ReportAgent generated HTML report.", flush=True)
        return convert_html_to_pdf.invoke({"report_html": report_html})
