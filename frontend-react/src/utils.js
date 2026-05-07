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
    daily: "Agile Daily Stand-up",
    brainstorm: "Brainstorming Session",
    client: "Client Pitch",
    general: "General Meeting",
  };
  return templateLabels[template] || "General Meeting";
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
