const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_URL = `${API_BASE_URL}/api/process-audio`;
const HISTORY_URL = `${API_BASE_URL}/api/meetings`;

async function parseResponse(response, fallbackMessage) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || fallbackMessage);
  }
  return payload;
}

export async function fetchMeetingHistory(limit = 12) {
  const response = await fetch(`${HISTORY_URL}?limit=${limit}`);
  return parseResponse(response, "Failed to load meeting history.");
}

export async function fetchMeetingDetail(meetingId) {
  const response = await fetch(`${HISTORY_URL}/${meetingId}`);
  return parseResponse(response, "Failed to load the selected meeting.");
}

export async function removeMeeting(meetingId) {
  const response = await fetch(`${HISTORY_URL}/${meetingId}`, {
    method: "DELETE",
  });
  return parseResponse(response, "Failed to delete meeting.");
}

export async function syncMeetingToFeishu(meetingId) {
  const response = await fetch(`${HISTORY_URL}/${meetingId}/sync-feishu`, {
    method: "POST",
  });
  return parseResponse(response, "Failed to sync action items to Feishu.");
}

export async function askMeetingAssistant(meetingId, question) {
  const response = await fetch(`${HISTORY_URL}/${meetingId}/assistant`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });
  return parseResponse(response, "Failed to get an answer from the meeting assistant.");
}

export async function processMeetingFile(file, template) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("template", template);

  const response = await fetch(API_URL, {
    method: "POST",
    body: formData,
  });
  return parseResponse(response, "Server error occurred.");
}
