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

const SAMPLE_QUESTION =
  "Which Tier 1 clients have active rights for localized versions with delayed delivery requests?";

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

sampleButton.addEventListener("click", () => {
  questionInput.value = SAMPLE_QUESTION;
  questionInput.focus();
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
      const detail = typeof data.detail === "string" ? data.detail : "Request failed.";
      throw new Error(detail);
    }

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