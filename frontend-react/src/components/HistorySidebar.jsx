import { formatDateTime } from "../utils.js";

export function HistorySidebar({
  meetings,
  isLoading,
  currentMeetingId,
  onRefresh,
  onOpenMeeting,
  onDeleteMeeting,
}) {
  let content = null;

  if (isLoading) {
    content = <p className="muted state-message">Loading saved meetings...</p>;
  } else if (!meetings.length) {
    content = <p className="muted state-message">No meetings saved yet.</p>;
  } else {
    content = meetings.map((meeting) => (
      <article className="history-item" key={meeting.id}>
        <button
          className={`history-open ${currentMeetingId === String(meeting.id) ? "is-active" : ""}`}
          type="button"
          onClick={() => onOpenMeeting(meeting.id)}
        >
          <span className="history-title">{meeting.filename}</span>
          <span className="history-meta">
            {meeting.template} | {formatDateTime(meeting.created_at)}
          </span>
        </button>
        <button
          className="history-delete"
          type="button"
          aria-label="Delete saved meeting"
          onClick={() => onDeleteMeeting(meeting.id)}
        >
          Delete
        </button>
      </article>
    ));
  }

  return (
    <aside className="sidebar-panel surface-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Meeting History</p>
          <h2>Recent Sessions</h2>
        </div>
        <button className="secondary-btn" type="button" onClick={onRefresh}>
          Refresh
        </button>
      </div>
      <p className="panel-caption">
        Open or delete saved meeting records without leaving the workspace.
      </p>
      <div className="history-list scroll-surface">{content}</div>
    </aside>
  );
}
