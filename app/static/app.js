const askForm = document.getElementById("askForm");
const questionInput = document.getElementById("questionInput");
const includeRowsInput = document.getElementById("includeRowsInput");
const modelInput = document.getElementById("modelInput");
const submitButton = document.getElementById("submitButton");
const sampleButton = document.getElementById("sampleButton");
const answerBox = document.getElementById("answerBox");
const cypherBox = document.getElementById("cypherBox");
const traceList = document.getElementById("traceList");
const rowsBox = document.getElementById("rowsBox");
const rowCount = document.getElementById("rowCount");
const statusText = document.getElementById("statusText");
const healthBadge = document.getElementById("healthBadge");

const SAMPLE_QUESTIONS = [
  "Which delivery points have the most failed or delayed delivery requests?",
  "What titles have 4K or 8K versions with no delivery requests created yet?",
  "Which languages have the most completed localization jobs, and what are their average quality scores?",
  "Which studios have the most titles with active exclusive rights grants?",
  "Show all high-priority delivery requests that missed their deadline, and which clients submitted them.",
  "Which vendors completed the most localization jobs, and what is their average quality score?",
  "Which Tier 1 clients have active rights for localized versions with delayed delivery requests?",
  "Which active rights are expiring in the next 90 days, and which clients and regions are affected?",
];

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.classList.toggle("error", isError);
}

function setAnswer(text, isError = false) {
  answerBox.textContent = text;
  answerBox.classList.toggle("empty", false);
  answerBox.classList.toggle("error", isError);
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Working..." : "Ask the graph";
}

function setTraceLink(traceId) {
  const el = document.getElementById("jaegerLink");
  if (!el) return;
  if (!traceId) {
    el.hidden = true;
    el.innerHTML = "";
    return;
  }
  el.hidden = false;
  el.innerHTML =
    `<span class="jaeger-link-label">Trace:</span>` +
    `<a href="http://localhost:16686/trace/${traceId}" target="_blank" rel="noopener noreferrer">${traceId}</a>`;
}

function renderTrace(trace = []) {
  traceList.innerHTML = "";
  traceList.classList.toggle("empty", trace.length === 0);

  if (trace.length === 0) {
    const item = document.createElement("li");
    item.textContent = "No trace yet.";
    traceList.appendChild(item);
    return;
  }

  trace.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = step;
    traceList.appendChild(item);
  });
}

function renderRows(rows = []) {
  rowCount.textContent = `${rows.length} row${rows.length === 1 ? "" : "s"}`;
  rowsBox.classList.toggle("empty", rows.length === 0);

  if (rows.length === 0) {
    rowsBox.textContent = "No rows returned.";
    return;
  }

  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify(rows, null, 2);
  rowsBox.replaceChildren(pre);
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) {
      throw new Error(`Health check failed with status ${response.status}`);
    }

    const data = await response.json();
    healthBadge.textContent = `Neo4j + Ollama ready (${data.model})`;
    healthBadge.classList.remove("pending", "error");
  } catch (error) {
    healthBadge.textContent = "Service unavailable";
    healthBadge.classList.remove("pending");
    healthBadge.classList.add("error");
  }
}

const sampleDropdown = document.getElementById("sampleDropdown");
const sampleList = document.getElementById("sampleList");

// Move list to <body> so it escapes the backdrop-filter stacking context on .panel,
// which would otherwise make position:fixed unreliable and clip z-index layering.
document.body.appendChild(sampleList);

SAMPLE_QUESTIONS.forEach((q, i) => {
  const li = document.createElement("li");
  li.textContent = q;
  li.setAttribute("role", "option");
  li.addEventListener("click", () => {
    questionInput.value = q;
    sampleButton.textContent = `Sample question (${i + 1}/${SAMPLE_QUESTIONS.length}) ▾`;
    closeSampleDropdown();
    questionInput.focus();
  });
  sampleList.appendChild(li);
});

function closeSampleDropdown() {
  sampleList.classList.remove("open");
  sampleButton.setAttribute("aria-expanded", "false");
}

sampleButton.addEventListener("click", (e) => {
  e.stopPropagation();
  if (sampleList.classList.contains("open")) {
    closeSampleDropdown();
    return;
  }
  // Reveal first so offsetHeight is measurable, then position relative to button.
  sampleList.classList.add("open");
  sampleButton.setAttribute("aria-expanded", "true");

  const rect = sampleButton.getBoundingClientRect();
  const listW = sampleList.offsetWidth;
  const listH = sampleList.offsetHeight;
  const left = Math.max(8, rect.right - listW);
  const topAbove = rect.top - listH - 8;
  const top = topAbove >= 8 ? topAbove : rect.bottom + 8;

  sampleList.style.left = `${left}px`;
  sampleList.style.top = `${top}px`;
});

document.addEventListener("click", (e) => {
  if (!sampleDropdown.contains(e.target) && !sampleList.contains(e.target)) {
    closeSampleDropdown();
  }
});

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();
  if (!question) {
    setStatus("Enter a question first.", true);
    questionInput.focus();
    return;
  }

  setLoading(true);
  setTraceLink(null);
  setStatus("Planning query and asking the graph...");
  setAnswer("Working on your question...");
  cypherBox.textContent = "Waiting for generated Cypher...";
  cypherBox.classList.add("empty");
  renderTrace([]);
  renderRows([]);

  const payload = {
    question,
    include_rows: includeRowsInput.checked,
  };

  const model = modelInput.value.trim();
  if (model) {
    payload.model = model;
  }

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      const traceId = response.headers.get("X-Trace-Id");
      setTraceLink(traceId);
      const detail = typeof data.detail === "string" ? data.detail : "Request failed.";
      throw new Error(detail);
    }

    setTraceLink(null);
    setStatus("Answer ready");
    setAnswer(data.answer || "No answer returned.");
    cypherBox.textContent = data.cypher || "No Cypher returned.";
    cypherBox.classList.remove("empty");
    renderTrace(data.agent_trace || []);
    renderRows(data.rows || []);
  } catch (error) {
    setStatus("Request failed", true);
    setAnswer(error.message || "Unknown error.", true);
    cypherBox.textContent = "No Cypher available because the request failed.";
    cypherBox.classList.add("empty");
    renderTrace([]);
    renderRows([]);
  } finally {
    setLoading(false);
  }
});

checkHealth();
checkServices();

async function checkServices() {
  try {
    const response = await fetch("/api/v1/services");
    if (!response.ok) return;
    const services = await response.json();

    const healthyCount = services.filter((s) => s.healthy === true).length;
    const total = services.length;
    const summary = document.getElementById("servicesSummary");
    if (summary) {
      summary.textContent = `${healthyCount} / ${total} healthy`;
    }

    services.forEach((svc) => {
      const dot = document.getElementById(`dot-${svc.id}`);
      if (!dot) return;
      dot.classList.remove("healthy", "unhealthy");
      if (svc.healthy === true) {
        dot.classList.add("healthy");
        dot.title = "Healthy";
      } else if (svc.healthy === false) {
        dot.classList.add("unhealthy");
        dot.title = "Unreachable";
      } else {
        dot.title = "Unknown";
      }
    });
  } catch (_) {
    const summary = document.getElementById("servicesSummary");
    if (summary) summary.textContent = "Status unavailable";
  }
}