from langchain_core.tools import tool
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from datetime import datetime
import os


@tool(return_direct=True)
def generate_pdf_report(report_text: str) -> str:
    """
    Generate a formatted PDF report from research summary text.
    Returns the file path of the generated PDF.
    """

    filename = f"ai_research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    output_path = os.path.join(os.getcwd(), filename)

    doc = SimpleDocTemplate(output_path)

    styles = getSampleStyleSheet()

    elements = []

    # Title
    elements.append(
        Paragraph("AI Research Report", styles["Title"])
    )

    elements.append(Spacer(1, 20))

    # Split content into paragraphs
    for section in report_text.split("\n\n\n"):

        if section.strip():
            elements.append(
                Paragraph(section.strip(), styles["BodyText"])
            )
            elements.append(Spacer(1, 10))

    doc.build(elements)
