const API_BASE_URL = "http://localhost:8000";
const API_URL = `${API_BASE_URL}/api/process-audio`;
const HISTORY_URL = `${API_BASE_URL}/api/meetings`;

const dropZone = document.getElementById("drop-zone");
const dropBadge = document.getElementById("drop-badge");
const dropTitle = document.getElementById("drop-title");
const dropSubtitle = document.getElementById("drop-subtitle");
const fileInput = document.getElementById("file-input");
const processBtn = document.getElementById("process-btn");
const statusSection = document.getElementById("processing-status");
const templateSelect = document.getElementById("template-select");
const resultsSection = document.getElementById("results-section");
const statusFill = document.querySelector(".fill");
const historyList = document.getElementById("history-list");
const refreshHistoryBtn = document.getElementById("refresh-history-btn");

let selectedFile = null;
let currentMeetingId = null;

dropZone.addEventListener("click", () => fileInput.click());
refreshHistoryBtn.addEventListener("click", () => loadHistory());

dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
    if (event.dataTransfer.files.length > 0) {
        selectedFile = event.dataTransfer.files[0];
        updateDropZoneUI();
    }
});

fileInput.addEventListener("change", (event) => {
    if (event.target.files.length > 0) {
        selectedFile = event.target.files[0];
        updateDropZoneUI();
    }
});

function updateDropZoneUI() {
    if (!selectedFile) {
        return;
    }

    dropBadge.textContent = "Ready";
    dropTitle.textContent = selectedFile.name;
    dropSubtitle.textContent = `Template: ${templateSelect.options[templateSelect.selectedIndex].text}`;
    processBtn.disabled = false;
}

function resetSteps() {
    const steps = document.querySelectorAll(".step");
    steps.forEach((step) => {
        step.classList.remove("active", "complete", "error");
    });
    statusFill.style.width = "10%";
    return steps;
}

function markStep(steps, index, status) {
    const step = steps[index];
    if (!step) {
        return;
    }
    step.classList.remove("active", "complete", "error");
    step.classList.add(status);
}

function advanceProgress(percent) {
    statusFill.style.width = `${percent}%`;
}

function formatDateTime(value) {
    if (!value) {
        return "Unknown time";
    }
    const date = new Date(value.replace(" ", "T"));
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString();
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatSeconds(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return "";
    }
    const totalSeconds = Math.max(0, Math.floor(value));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function getCollapseLabels(targetId) {
    return targetId === "raw-transcript"
        ? { open: "Hide transcript", closed: "Show transcript" }
        : { open: "Collapse speaker turns", closed: "Show speaker turns" };
}

function renderHistoryState(message) {
    historyList.innerHTML = `<p class="muted state-message">${escapeHtml(message)}</p>`;
}

async function loadHistory() {
    renderHistoryState("Loading saved meetings...");

    try {
        const response = await fetch(`${HISTORY_URL}?limit=12`);
        if (!response.ok) {
            throw new Error("Failed to load meeting history.");
        }

        const payload = await response.json();
        const meetings = payload.meetings || [];

        if (meetings.length === 0) {
            renderHistoryState("No meetings saved yet.");
            return;
        }

        historyList.innerHTML = meetings
            .map(
                (meeting) => `
                    <article class="history-item">
                        <button class="history-open ${currentMeetingId === String(meeting.id) ? "is-active" : ""}" type="button" data-meeting-id="${meeting.id}">
                            <span class="history-title">${escapeHtml(meeting.filename)}</span>
                            <span class="history-meta">${escapeHtml(meeting.template)} | ${escapeHtml(formatDateTime(meeting.created_at))}</span>
                        </button>
                        <button class="history-delete" type="button" data-meeting-id="${meeting.id}" aria-label="Delete saved meeting">
                            Delete
                        </button>
                    </article>
                `
            )
            .join("");

        document.querySelectorAll(".history-open").forEach((button) => {
            button.addEventListener("click", () => {
                const meetingId = button.dataset.meetingId;
                loadMeetingDetail(meetingId);
            });
        });

        document.querySelectorAll(".history-delete").forEach((button) => {
            button.addEventListener("click", async () => {
                const meetingId = button.dataset.meetingId;
                await deleteMeeting(meetingId);
            });
        });
    } catch (error) {
        renderHistoryState(`Unable to load history. ${error.message}`);
    }
}

async function loadMeetingDetail(meetingId) {
    try {
        const response = await fetch(`${HISTORY_URL}/${meetingId}`);
        if (!response.ok) {
            throw new Error("Failed to load the selected meeting.");
        }
        const meeting = await response.json();
        currentMeetingId = String(meeting.id || meetingId);
        renderResults(meeting);
        loadHistory();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function deleteMeeting(meetingId) {
    const confirmed = window.confirm("Delete this saved meeting record?");
    if (!confirmed) {
        return;
    }

    try {
        const response = await fetch(`${HISTORY_URL}/${meetingId}`, {
            method: "DELETE",
        });
        if (!response.ok) {
            const errorPayload = await response.json();
            throw new Error(errorPayload.detail || "Failed to delete meeting.");
        }

        if (currentMeetingId === String(meetingId)) {
            currentMeetingId = null;
            resultsSection.innerHTML = "";
            resultsSection.classList.add("hidden");
        }

        await loadHistory();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

processBtn.addEventListener("click", async () => {
    if (!selectedFile) {
        return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("template", templateSelect.value);

    statusSection.classList.remove("hidden");
    resultsSection.classList.add("hidden");
    resultsSection.innerHTML = "";
    processBtn.disabled = true;

    const steps = resetSteps();
    markStep(steps, 0, "active");
    advanceProgress(18);

    try {
        const responsePromise = fetch(API_URL, {
            method: "POST",
            body: formData,
        });

        window.setTimeout(() => {
            markStep(steps, 0, "complete");
            markStep(steps, 1, "active");
            advanceProgress(36);
        }, 300);

        window.setTimeout(() => {
            markStep(steps, 1, "complete");
            markStep(steps, 2, "active");
            advanceProgress(58);
        }, 900);

        window.setTimeout(() => {
            markStep(steps, 2, "complete");
            markStep(steps, 3, "active");
            advanceProgress(78);
        }, 1500);

        window.setTimeout(() => {
            markStep(steps, 3, "complete");
            markStep(steps, 4, "active");
            advanceProgress(92);
        }, 2100);

        const response = await responsePromise;

        if (!response.ok) {
            const errorPayload = await response.json();
            throw new Error(errorPayload.detail || "Server error occurred");
        }

        const data = await response.json();
        markStep(steps, 4, "complete");
        advanceProgress(100);
        currentMeetingId = String(data.id || "");
        renderResults(data);
        loadHistory();
    } catch (error) {
        console.error(error);
        document.querySelectorAll(".step").forEach((step) => {
            if (!step.classList.contains("complete")) {
                step.classList.add("error");
            }
        });
        alert(`Error: ${error.message}`);
    } finally {
        processBtn.disabled = false;
    }
});

function renderList(items, emptyText) {
    if (!items || items.length === 0) {
        return `<p class="muted">${emptyText}</p>`;
    }

    return `
        <ul class="bullet-list">
            ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
        </ul>
    `;
}

function renderActionItems(actionItems) {
    if (!actionItems || actionItems.length === 0) {
        return `<p class="muted">No specific action items found.</p>`;
    }

    return `
        <div class="action-stack scroll-surface">
            ${actionItems
                .map(
                    (item) => `
                        <article class="action-card">
                            <h3>${escapeHtml(item.task)}</h3>
                            <p><strong>Owner:</strong> ${escapeHtml(item.assignee)}</p>
                            <p><strong>Deadline:</strong> ${escapeHtml(item.deadline)}</p>
                        </article>
                    `
                )
                .join("")}
        </div>
    `;
}

function renderSpeakerSegments(segments, status) {
    if (!segments || segments.length === 0) {
        const statusMessages = {
            disabled: "Speaker diarization is disabled for this deployment.",
            unconfigured: "Speaker diarization is not configured yet. Add the required tokens to enable it.",
            not_available: "Speaker parsing is not available for this meeting.",
            text_input: "Speaker diarization is only available for uploaded audio files.",
            error: "Speaker diarization encountered an error. Check the backend token and pyannote setup.",
        };
        const message = statusMessages[status] || "No speaker turns were detected in this meeting.";
        return `<p class="muted">${message}</p>`;
    }

    return `
        <div class="speaker-list">
            ${segments
                .map(
                    (segment) => `
                        <article class="speaker-card">
                            <div class="speaker-head">
                                <p class="speaker-name">${escapeHtml(segment.speaker_label || segment.speaker)}</p>
                                <span class="history-meta">${escapeHtml(formatSeconds(segment.start))} - ${escapeHtml(formatSeconds(segment.end))}</span>
                            </div>
                            <p>${escapeHtml(segment.text)}</p>
                        </article>
                    `
                )
                .join("")}
        </div>
    `;
}

function renderResults(data) {
    const summaryHTML = marked.parse(data.summary || "No summary generated.");
    const followUpHTML = marked.parse(data.follow_up || "No follow-up generated.");
    const insights = data.insights || {};
    const transcriptText = data.cleaned_transcript || data.speaker_aware_transcript || data.transcript || "";

    resultsSection.innerHTML = `
        <div class="results-layout">
            <div class="results-primary">
                <section class="summary-card">
                    <div class="result-card-head">
                        <div>
                            <p class="eyebrow">Summary</p>
                            <h2>${escapeHtml(data.filename || "Meeting Output")}</h2>
                        </div>
                        <span class="history-meta">${escapeHtml(data.template || "general")} | ${escapeHtml(formatDateTime(data.created_at))}</span>
                    </div>
                    <div class="markdown-body scroll-surface">${summaryHTML}</div>
                </section>

                <section class="result-card">
                    <div class="result-card-head">
                        <div>
                            <p class="eyebrow">Action Items</p>
                            <h2>Execution Snapshot</h2>
                        </div>
                        <span class="history-meta">${escapeHtml((data.action_items || []).length)} items</span>
                    </div>
                    <div class="result-card-body">${renderActionItems(data.action_items || [])}</div>
                </section>
            </div>

            <section class="result-card">
                <div class="result-card-head">
                    <div>
                        <p class="eyebrow">Follow-up Plan</p>
                        <h2>Next-step Coordination</h2>
                    </div>
                    <span class="history-meta">Generated from summary, action items, and insights</span>
                </div>
                <div class="markdown-body scroll-surface">${followUpHTML}</div>
            </section>

            <div class="results-secondary">
                <section class="secondary-card">
                    <div class="result-card-head">
                        <div>
                            <p class="eyebrow">Meeting Insights</p>
                            <h2>Signals and Decisions</h2>
                        </div>
                        <span class="history-meta">Secondary analysis</span>
                    </div>
                    <div class="insight-block scroll-surface">
                        <article class="insight-cluster">
                            <p><strong>Tone:</strong> ${escapeHtml(insights.meeting_tone || "Unavailable")}</p>
                        </article>
                        <article class="insight-cluster">
                            <strong>Key Decisions</strong>
                            ${renderList(insights.key_decisions, "No decisions captured.")}
                        </article>
                        <article class="insight-cluster">
                            <strong>Blockers</strong>
                            ${renderList(insights.blockers, "No blockers captured.")}
                        </article>
                        <article class="insight-cluster">
                            <strong>Next Focus</strong>
                            ${renderList(insights.next_focus, "No next-focus items captured.")}
                        </article>
                    </div>
                </section>

                <section class="secondary-card">
                    <div class="result-card-head">
                        <div>
                            <p class="eyebrow">Speaker Turns</p>
                            <h2>Conversation Timeline</h2>
                        </div>
                        <span class="history-meta">${escapeHtml(data.diarization_status || "not_available")}</span>
                    </div>
                    <div class="collapse-shell">
                        <p class="muted">Diarization: ${escapeHtml(data.diarization_status || "not_available")} (${escapeHtml(data.diarization_backend || "none")})</p>
                        ${data.diarization_error ? `<p class="muted">Detail: ${escapeHtml(data.diarization_error)}</p>` : ""}
                        <button class="collapse-btn" type="button" data-collapse-target="speaker-scroll">Collapse speaker turns</button>
                        <div id="speaker-scroll" class="speaker-scroll scroll-surface">
                            ${renderSpeakerSegments(data.speaker_segments || [], data.diarization_status)}
                        </div>
                    </div>
                </section>

                <section class="secondary-card secondary-card-wide">
                    <div class="result-card-head">
                        <div>
                            <p class="eyebrow">Transcript</p>
                            <h2>Cleaned Meeting Transcript</h2>
                        </div>
                        <span class="history-meta">Review reference</span>
                    </div>
                    <div class="collapse-shell">
                        <button class="collapse-btn" type="button" data-collapse-target="raw-transcript">Hide transcript</button>
                        <div id="raw-transcript" class="transcript-panel scroll-surface">${escapeHtml(transcriptText)}</div>
                    </div>
                </section>
            </div>
        </div>
    `;

    document.querySelectorAll("[data-collapse-target]").forEach((button) => {
        const targetId = button.dataset.collapseTarget;
        const target = document.getElementById(targetId);
        if (!target) {
            return;
        }

        button.addEventListener("click", () => {
            const isCollapsed = target.classList.toggle("is-collapsed");
            const labels = getCollapseLabels(targetId);
            button.textContent = isCollapsed ? labels.closed : labels.open;
        });
    });

    resultsSection.classList.remove("hidden");
}

loadHistory();
