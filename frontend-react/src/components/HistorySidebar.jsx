import { formatDateTime, getTemplateLabel } from "../utils.js";

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
    content = (
      <div className="state-card">
        <strong>No saved meetings yet</strong>
        <p className="muted">
          Generated meetings will appear here for quick reopen and deletion.
        </p>
      </div>
    );
  } else {
    content = meetings.map((meeting) => (
      <article className="history-item" key={meeting.id}>
        <button
          className={`history-open ${currentMeetingId === String(meeting.id) ? "is-active" : ""}`}
          type="button"
          onClick={() => onOpenMeeting(meeting.id)}
        >
          <div className="history-item-topline">
            <span className="history-chip">{getTemplateLabel(meeting.template)}</span>
          </div>
          <span className="history-title">{meeting.filename}</span>
          <span className="history-subcopy">Structured summary, actions, insights, and follow-up</span>
          <span className="history-meta history-meta-block">{formatDateTime(meeting.created_at)}</span>
        </button>
        <button
          className="history-delete"
          type="button"
          aria-label="Delete saved meeting"
          onClick={() => onDeleteMeeting(meeting.id)}
        >
          Remove
        </button>
      </article>
    ));
  }

  return (
    <aside className="sidebar-panel surface-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Meeting History</p>
          <h2>Saved sessions</h2>
        </div>
        <span className="count-badge">{meetings.length}</span>
      </div>

      <p className="panel-caption">
        Use the sidebar as a lightweight archive of generated meeting outputs.
      </p>

      <div className="sidebar-actions">
        <button className="secondary-btn" type="button" onClick={onRefresh}>
          Refresh history
        </button>
      </div>

      <div className="history-list scroll-surface">{content}</div>
    </aside>
  );
}
