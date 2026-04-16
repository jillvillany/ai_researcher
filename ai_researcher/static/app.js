const form = document.getElementById("search-form");
const submitButton = document.getElementById("submit-button");
const statusMessage = document.getElementById("status-message");
const resultsSection = document.getElementById("results");
const reportPreview = document.getElementById("report-preview");
const reportEmpty = document.getElementById("report-empty");
const reportLink = document.getElementById("report-link");
const DEFAULT_QUERY = "AI";

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Working..." : "Search and Generate Report";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  setLoading(true);
  setStatus("Searching arXiv and generating report...");
  resultsSection.classList.add("hidden");
  reportPreview.src = "";
  reportPreview.classList.add("hidden");
  reportEmpty.classList.remove("hidden");
  reportLink.classList.add("hidden");
  reportLink.removeAttribute("href");

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: DEFAULT_QUERY }),
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.details || payload.error || "Request failed.");
    }

    if (payload.report_pdf_url) {
      reportPreview.src = payload.report_pdf_url;
      reportPreview.classList.remove("hidden");
      reportEmpty.classList.add("hidden");
      reportLink.href = payload.report_pdf_url;
      reportLink.classList.remove("hidden");
    }
    resultsSection.classList.remove("hidden");
    setStatus("Finished. Results are ready below.");
  } catch (error) {
    setStatus(error.message || "Something went wrong.", true);
  } finally {
    setLoading(false);
  }
});
