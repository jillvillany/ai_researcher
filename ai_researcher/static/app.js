const form = document.getElementById("search-form");
const queryInput = document.getElementById("query-input");
const submitButton = document.getElementById("submit-button");
const statusMessage = document.getElementById("status-message");
const logSection = document.getElementById("log-section");
const logOutput = document.getElementById("agent-stdout");
const resultsSection = document.getElementById("results");
const reportPreview = document.getElementById("report-preview");
const reportEmpty = document.getElementById("report-empty");
const reportLink = document.getElementById("report-link");
const POLL_INTERVAL_MS = 1000;

function updateLogs(logText) {
  logOutput.value = logText || "";
  logOutput.scrollTop = logOutput.scrollHeight;
}

function resetResults() {
  resultsSection.classList.add("hidden");
  reportPreview.src = "";
  reportPreview.classList.add("hidden");
  reportEmpty.classList.remove("hidden");
  reportLink.classList.add("hidden");
  reportLink.removeAttribute("href");
}

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  queryInput.disabled = isLoading;
  submitButton.textContent = isLoading ? "Working..." : "Generate Report";
}

async function pollJob(jobId) {
  while (true) {
    const response = await fetch(`/api/search/${jobId}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Unable to load job status.");
    }

    updateLogs(payload.logs || "");

    if (payload.status === "completed") {
      if (payload.report_pdf_url) {
        reportPreview.src = payload.report_pdf_url;
        reportPreview.classList.remove("hidden");
        reportEmpty.classList.add("hidden");
        reportLink.href = payload.report_pdf_url;
        reportLink.classList.remove("hidden");
      }

      resultsSection.classList.remove("hidden");
      setStatus("Finished. Results are ready below.");
      return;
    }

    if (payload.status === "failed") {
      throw new Error(payload.error || "The research workflow failed.");
    }

    await new Promise((resolve) => {
      window.setTimeout(resolve, POLL_INTERVAL_MS);
    });
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  setLoading(true);
  setStatus("Searching Google News and generating report...");
  logSection.classList.remove("hidden");
  updateLogs("$ starting workflow\n");
  resetResults();

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query: queryInput.value.trim() }),
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.details || payload.error || "Request failed.");
    }

    await pollJob(payload.job_id);
  } catch (error) {
    updateLogs(`${logOutput.value}\n${error.message || "Something went wrong."}`.trim());
    setStatus(error.message || "Something went wrong.", true);
  } finally {
    setLoading(false);
  }
});
