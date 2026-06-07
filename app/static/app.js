const askForm = document.getElementById("askForm");
const questionInput = document.getElementById("questionInput");
const questionLabel = document.getElementById("questionLabel");
const includeRowsInput = document.getElementById("includeRowsInput");
const vectorLimitInput = document.getElementById("vectorLimitInput");
const modelInput = document.getElementById("modelInput");
const submitButton = document.getElementById("submitButton");
const sampleButton = document.getElementById("sampleButton");
const answerBox = document.getElementById("answerBox");
const cypherBox = document.getElementById("cypherBox");
const traceList = document.getElementById("traceList");
const rowsBox = document.getElementById("rowsBox");
const rowCount = document.getElementById("rowCount");
const hitsBox = document.getElementById("hitsBox");
const hitCount = document.getElementById("hitCount");
const statusText = document.getElementById("statusText");
const healthBadge = document.getElementById("healthBadge");
const mainLayout = document.getElementById("mainLayout");
const modeGraphBtn = document.getElementById("modeGraphBtn");
const modeVectorBtn = document.getElementById("modeVectorBtn");
const modeDescription = document.getElementById("modeDescription");

// ── Mode management ──────────────────────────────────────────────────

const MODE_DESCRIPTIONS = {
  graph: "Graph RAG: the LLM generates a Cypher query, executes it against Neo4j, then synthesises a grounded answer from the returned rows.",
  vector: "Vector RAG: your question is embedded and used to find semantically similar content synopses in Weaviate, then the LLM synthesises an answer from those documents.",
};

const GRAPH_SAMPLE_QUESTIONS = [
  "Which delivery points have the most failed or delayed delivery requests?",
  "What titles have 4K or 8K versions with no delivery requests created yet?",
  "Which languages have the most completed localization jobs, and what are their average quality scores?",
  "Which studios have the most titles with active exclusive rights grants?",
  "Show all high-priority delivery requests that missed their deadline, and which clients submitted them.",
  "Which vendors completed the most localization jobs, and what is their average quality score?",
  "Which Tier 1 clients have active rights for localized versions with delayed delivery requests?",
  "Which active rights are expiring in the next 90 days, and which clients and regions are affected?",
];

const VECTOR_SAMPLE_QUESTIONS = [
  "Show me science fiction titles about space exploration and colonization.",
  "Find dramatic films dealing with grief, loss, and family reconciliation.",
  "What action thrillers involve government conspiracies or corruption?",
  "Show me psychological thrillers with twists and hidden identities.",
  "Find animated titles about friendship, belonging, and found family.",
  "What horror content deals with isolation and being hunted?",
  "Show me romantic dramas about star-crossed or long-distance love.",
  "Find documentaries investigating environmental or social issues.",
];

let currentMode = "graph";

function setMode(mode) {
  currentMode = mode;
  mainLayout.dataset.mode = mode;

  // Toggle button states
  modeGraphBtn.classList.toggle("active", mode === "graph");
  modeVectorBtn.classList.toggle("active", mode === "vector");

  // Show/hide mode-specific elements
  document.querySelectorAll(".graph-only").forEach(el => {
    el.style.display = mode === "graph" ? "" : "none";
  });
  document.querySelectorAll(".vector-only").forEach(el => {
    el.style.display = mode === "vector" ? "" : "none";
  });

  // Update labels and descriptions
  modeDescription.textContent = MODE_DESCRIPTIONS[mode];
  if (mode === "graph") {
    questionLabel.textContent = "Ask about rights, localization, delivery risk, or clients";
    questionInput.placeholder = "Which Tier 1 clients have active rights for localized versions with delayed deliveries?";
    submitButton.textContent = "Ask the graph";
  } else {
    questionLabel.textContent = "Describe the kind of content you're looking for";
    questionInput.placeholder = "Show me science fiction titles about artificial intelligence and the future of humanity.";
    submitButton.textContent = "Search by meaning";
  }

  // Rebuild sample list for the active mode
  rebuildSampleList(mode === "graph" ? GRAPH_SAMPLE_QUESTIONS : VECTOR_SAMPLE_QUESTIONS);

  // Reset output areas
  setStatus("Ready");
  setAnswer("No answer yet.");
  answerBox.classList.add("empty");
  answerBox.classList.remove("error");
  setTraceLink(null);
  renderTrace([]);

  if (mode === "graph") {
    cypherBox.textContent = "No query yet.";
    cypherBox.classList.add("empty");
    renderRows([]);
  } else {
    renderHits([]);
  }
}

modeGraphBtn.addEventListener("click", () => setMode("graph"));
modeVectorBtn.addEventListener("click", () => setMode("vector"));

// ── Helpers ──────────────────────────────────────────────────────────

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
  if (isLoading) {
    submitButton.textContent = "Working...";
  } else {
    submitButton.textContent = currentMode === "graph" ? "Ask the graph" : "Search by meaning";
  }
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
  if (!rowCount || !rowsBox) return;
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

function renderHits(hits = []) {
  if (!hitCount || !hitsBox) return;
  hitCount.textContent = `${hits.length} hit${hits.length === 1 ? "" : "s"}`;
  hitsBox.classList.toggle("empty", hits.length === 0);

  if (hits.length === 0) {
    hitsBox.textContent = "No results returned.";
    return;
  }

  const table = document.createElement("table");
  table.className = "hits-table";

  const thead = table.createTHead();
  const hr = thead.insertRow();
  ["#", "Title", "Type", "Genre", "Year", "Synopsis", "Certainty"].forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    hr.appendChild(th);
  });

  const tbody = table.createTBody();
  hits.forEach((hit, i) => {
    const tr = tbody.insertRow();

    const tdNum = tr.insertCell();
    tdNum.textContent = i + 1;

    const tdName = tr.insertCell();
    tdName.textContent = hit.title_name || "—";

    const tdType = tr.insertCell();
    tdType.textContent = hit.title_type || "—";

    const tdGenre = tr.insertCell();
    tdGenre.textContent = hit.genre || "—";

    const tdYear = tr.insertCell();
    tdYear.textContent = hit.release_year != null ? hit.release_year : "—";

    const tdSynopsis = tr.insertCell();
    tdSynopsis.className = "synopsis-cell";
    tdSynopsis.textContent = hit.synopsis || "—";

    const tdCert = tr.insertCell();
    const certainty = hit._certainty != null ? hit._certainty : null;
    if (certainty !== null) {
      const pct = Math.round(certainty * 100);
      tdCert.innerHTML = `
        <div class="certainty-bar">
          <div class="certainty-track">
            <div class="certainty-fill" style="width:${pct}%"></div>
          </div>
          <span class="certainty-label">${pct}%</span>
        </div>`;
    } else {
      tdCert.textContent = "—";
    }
  });

  hitsBox.replaceChildren(table);
}

// ── Sample questions ─────────────────────────────────────────────────

const sampleDropdown = document.getElementById("sampleDropdown");
const sampleList = document.getElementById("sampleList");

document.body.appendChild(sampleList);

function rebuildSampleList(questions) {
  sampleList.innerHTML = "";
  questions.forEach((q, i) => {
    const li = document.createElement("li");
    li.textContent = q;
    li.setAttribute("role", "option");
    li.addEventListener("click", () => {
      questionInput.value = q;
      sampleButton.textContent = `Sample question (${i + 1}/${questions.length}) ▾`;
      closeSampleDropdown();
      questionInput.focus();
    });
    sampleList.appendChild(li);
  });
}

rebuildSampleList(GRAPH_SAMPLE_QUESTIONS);

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

// ── Form submission ──────────────────────────────────────────────────

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
  setStatus(currentMode === "graph" ? "Planning query and asking the graph..." : "Searching the vector store...");
  setAnswer("Working on your question...");
  renderTrace([]);

  if (currentMode === "graph") {
    cypherBox.textContent = "Waiting for generated Cypher...";
    cypherBox.classList.add("empty");
    renderRows([]);
  } else {
    renderHits([]);
  }

  const model = modelInput.value.trim();

  try {
    let response, data;

    if (currentMode === "graph") {
      const payload = { question, include_rows: includeRowsInput.checked };
      if (model) payload.model = model;

      response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      data = await response.json();

      if (!response.ok) {
        const traceId = response.headers.get("X-Trace-Id");
        setTraceLink(traceId);
        throw new Error(typeof data.detail === "string" ? data.detail : "Request failed.");
      }

      setTraceLink(null);
      setStatus("Answer ready");
      setAnswer(data.answer || "No answer returned.");
      cypherBox.textContent = data.cypher || "No Cypher returned.";
      cypherBox.classList.remove("empty");
      renderTrace(data.agent_trace || []);
      renderRows(data.rows || []);

    } else {
      const limit = parseInt(vectorLimitInput.value, 10) || 10;
      const payload = { question, limit };
      if (model) payload.model = model;

      response = await fetch("/api/v1/vector-ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      data = await response.json();

      if (!response.ok) {
        const traceId = response.headers.get("X-Trace-Id");
        setTraceLink(traceId);
        throw new Error(typeof data.detail === "string" ? data.detail : "Request failed.");
      }

      setTraceLink(null);
      setStatus("Answer ready");
      setAnswer(data.answer || "No answer returned.");
      renderTrace(data.agent_trace || []);
      renderHits(data.hits || []);
    }

  } catch (error) {
    setStatus("Request failed", true);
    setAnswer(error.message || "Unknown error.", true);
    if (currentMode === "graph") {
      cypherBox.textContent = "No Cypher available because the request failed.";
      cypherBox.classList.add("empty");
      renderRows([]);
    } else {
      renderHits([]);
    }
    renderTrace([]);
  } finally {
    setLoading(false);
  }
});

// ── Health check ─────────────────────────────────────────────────────

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error(`status ${response.status}`);
    const data = await response.json();
    healthBadge.textContent = `Neo4j + Ollama ready (${data.model})`;
    healthBadge.classList.remove("pending", "error");
  } catch {
    healthBadge.textContent = "Service unavailable";
    healthBadge.classList.remove("pending");
    healthBadge.classList.add("error");
  }
}

async function checkServices() {
  try {
    const response = await fetch("/api/v1/services");
    if (!response.ok) return;
    const services = await response.json();

    const healthyCount = services.filter((s) => s.healthy === true).length;
    const total = services.length;
    const summary = document.getElementById("servicesSummary");
    if (summary) summary.textContent = `${healthyCount} / ${total} healthy`;

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
  } catch {
    const summary = document.getElementById("servicesSummary");
    if (summary) summary.textContent = "Status unavailable";
  }
}

checkHealth();
checkServices();
