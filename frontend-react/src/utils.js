export function formatDateTime(value) {
  if (!value) {
    return "Unknown time";
  }

  const date = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString();
}

export function formatSeconds(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "";
  }
  const totalSeconds = Math.max(0, Math.floor(value));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function getTemplateLabel(template) {
  const templateLabels = {
    academic: "Academic / Research Meeting",
    daily: "Agile Daily Stand-up",
    brainstorm: "Brainstorming Session",
    client: "Client Pitch",
    general: "General Meeting",
  };
  return templateLabels[template] || "General Meeting";
}

export function isAcademicTemplate(template) {
  return template === "academic";
}

export function getAcademicSurfaceLabels(template) {
  if (template === "academic") {
    return {
      summaryEyebrow: "Research Summary",
      summaryTitle: "Research Discussion Brief",
      actionEyebrow: "Research Action Items",
      actionTitle: "Experiment & Task Snapshot",
      followupEyebrow: "Research Follow-up",
      followupTitle: "Next Research Checkpoints",
      insightTag: "Research-focused diagnostics",
    };
  }

  return {
    summaryEyebrow: "Summary",
    summaryTitle: null,
    actionEyebrow: "Action Items",
    actionTitle: "Execution Snapshot",
    followupEyebrow: "Follow-up Plan",
    followupTitle: "Next-step coordination",
    insightTag: "Multi-dimensional diagnostics",
  };
}

export function getSpeakerStatusMessage(status) {
  const statusMessages = {
    disabled: "Speaker diarization is disabled for this deployment.",
    unconfigured:
      "Speaker diarization is not configured yet. Add the required tokens to enable it.",
    not_available: "Speaker parsing is not available for this meeting.",
    text_input: "Speaker diarization is only available for uploaded audio files.",
    error: "Speaker diarization encountered an error. Check the backend token and pyannote setup.",
  };
  return statusMessages[status] || "No speaker turns were detected in this meeting.";
}

export function getCollapseLabels(targetId) {
  return targetId === "raw-transcript"
    ? { open: "Hide transcript", closed: "Show transcript" }
    : { open: "Collapse speaker turns", closed: "Show speaker turns" };
}

export function formatSentimentLabel(label) {
  const normalized = String(label || "").trim();
  if (!normalized) {
    return "Unavailable";
  }
  return normalized
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getEfficiencyDescriptor(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) {
    return "Unavailable";
  }
  if (value >= 8.5) {
    return "Very efficient";
  }
  if (value >= 7) {
    return "Effective";
  }
  if (value >= 5) {
    return "Mixed";
  }
  return "Needs improvement";
}

export function formatParticipationBalance(value) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return "Unavailable";
  }
  return normalized
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function section(title, content) {
  return `${title}\n${"=".repeat(title.length)}\n${content}\n`;
}

function listOrFallback(items, formatter = (item) => String(item), fallback = "None") {
  if (!Array.isArray(items) || !items.length) {
    return fallback;
  }
  return items.map((item, index) => formatter(item, index)).join("\n");
}

export function buildMeetingExportText(data) {
  const insights = data?.insights || {};
  const transcriptText =
    data?.cleaned_transcript || data?.speaker_aware_transcript || data?.transcript || "";

  const header = [
    `Meeting File: ${data?.filename || "Unknown"}`,
    `Template: ${getTemplateLabel(data?.template || "general")}`,
    `Created At: ${formatDateTime(data?.created_at)}`,
    `Diarization Status: ${data?.diarization_status || "not_available"}`,
    `Diarization Backend: ${data?.diarization_backend || "none"}`,
  ].join("\n");

  const actionItems = listOrFallback(
    data?.action_items,
    (item, index) =>
      `${index + 1}. ${item.task}\n   Category: ${item.category || "General"}\n   Owner: ${item.assignee}\n   Deadline: ${item.deadline}`,
  );

  const speakingShare = listOrFallback(
    insights?.speaking_share,
    (item) => `- ${item.speaker_label}: ${item.share_percent}% (${item.duration_seconds}s)`,
  );

  const keywordCloud = Array.isArray(insights?.keyword_cloud) && insights.keyword_cloud.length
    ? insights.keyword_cloud.join(", ")
    : "None";

  const decisions = listOrFallback(insights?.key_decisions, (item) => `- ${item}`);
  const blockers = listOrFallback(insights?.blockers, (item) => `- ${item}`);
  const nextFocus = listOrFallback(insights?.next_focus, (item) => `- ${item}`);
  const improvements = listOrFallback(
    insights?.recommended_improvements,
    (item) => `- ${item}`,
  );
  const rhythm = listOrFallback(insights?.meeting_rhythm, (item) => `- ${item}`);
  const speakerTimeline = listOrFallback(
    data?.speaker_segments,
    (segment) =>
      `[${formatSeconds(segment.start)} - ${formatSeconds(segment.end)}] ${segment.speaker_label || segment.speaker}: ${segment.text}`,
  );

  return [
    section("Meeting Metadata", header),
    section("Summary", data?.summary || "No summary generated."),
    section("Action Items", actionItems),
    section(
      "Meeting Insights",
      [
        `Quality Summary: ${insights?.quality_summary || "Unavailable"}`,
        `Sentiment: ${formatSentimentLabel(insights?.sentiment_label || insights?.meeting_tone)} (${Number.isFinite(insights?.sentiment_score) ? insights.sentiment_score.toFixed(2) : "0.50"})`,
        `Efficiency: ${getEfficiencyDescriptor(insights?.efficiency_score)} (${Number.isFinite(insights?.efficiency_score) ? insights.efficiency_score.toFixed(1) : "0.0"}/10)`,
        `Efficiency Reason: ${insights?.efficiency_reason || "Unavailable"}`,
        `Participation Balance: ${formatParticipationBalance(insights?.participation_balance)}`,
        "",
        "Speaking Share:",
        speakingShare,
        "",
        `Keyword Cloud: ${keywordCloud}`,
        "",
        "Meeting Rhythm:",
        rhythm,
        "",
        "Key Decisions:",
        decisions,
        "",
        "Blockers:",
        blockers,
        "",
        "Next Focus:",
        nextFocus,
        "",
        "Recommended Improvements:",
        improvements,
      ].join("\n"),
    ),
    section("Follow-up Plan", data?.follow_up || "No follow-up generated."),
    section("Speaker Timeline", speakerTimeline),
    section("Cleaned Transcript", transcriptText || "No transcript available."),
  ].join("\n");
}
