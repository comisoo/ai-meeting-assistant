import { useMemo, useState } from "react";
import { marked } from "marked";
import {
  formatDateTime,
  formatSeconds,
  getCollapseLabels,
  getSpeakerStatusMessage,
} from "../utils.js";

function MarkdownBlock({ value, className = "markdown-body scroll-surface" }) {
  const markup = useMemo(
    () => ({ __html: marked.parse(value || "No content generated.") }),
    [value],
  );

  return <div className={className} dangerouslySetInnerHTML={markup}></div>;
}

function BulletList({ items, emptyText }) {
  if (!items?.length) {
    return <p className="muted">{emptyText}</p>;
  }

  return (
    <ul className="bullet-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  );
}

function ActionItems({ items }) {
  if (!items?.length) {
    return <p className="muted">No specific action items found.</p>;
  }

  return (
    <div className="action-stack scroll-surface">
      {items.map((item, index) => (
        <article className="action-card" key={`${item.task}-${index}`}>
          <h3>{item.task}</h3>
          <p>
            <strong>Owner:</strong> {item.assignee}
          </p>
          <p>
            <strong>Deadline:</strong> {item.deadline}
          </p>
        </article>
      ))}
    </div>
  );
}

function SpeakerSegmentList({ segments, status }) {
  if (!segments?.length) {
    return <p className="muted">{getSpeakerStatusMessage(status)}</p>;
  }

  return (
    <div className="speaker-list">
      {segments.map((segment, index) => (
        <article className="speaker-card" key={`${segment.start}-${segment.end}-${index}`}>
          <div className="speaker-head">
            <p className="speaker-name">{segment.speaker_label || segment.speaker}</p>
            <span className="history-meta">
              {formatSeconds(segment.start)} - {formatSeconds(segment.end)}
            </span>
          </div>
          <p>{segment.text}</p>
        </article>
      ))}
    </div>
  );
}

function CollapseSection({ targetId, initialCollapsed = false, children }) {
  const [isCollapsed, setIsCollapsed] = useState(initialCollapsed);
  const labels = getCollapseLabels(targetId);

  return (
    <div className="collapse-shell">
      <button
        className="collapse-btn"
        type="button"
        onClick={() => setIsCollapsed((value) => !value)}
      >
        {isCollapsed ? labels.closed : labels.open}
      </button>
      <div id={targetId} className={isCollapsed ? "is-collapsed" : ""}>
        {children}
      </div>
    </div>
  );
}

export function ResultsBoard({ data, onSyncFeishu, isSyncingFeishu }) {
  if (!data) {
    return null;
  }

  const insights = data.insights || {};
  const transcriptText =
    data.cleaned_transcript || data.speaker_aware_transcript || data.transcript || "";

  return (
    <section className="results-board">
      <div className="results-layout">
        <div className="results-primary">
          <section className="summary-card">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Summary</p>
                <h2>{data.filename || "Meeting Output"}</h2>
              </div>
              <span className="history-meta">
                {data.template || "general"} | {formatDateTime(data.created_at)}
              </span>
            </div>
            <MarkdownBlock value={data.summary || "No summary generated."} />
          </section>

          <section className="result-card">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Action Items</p>
                <h2>Execution Snapshot</h2>
              </div>
              <div className="result-card-actions">
                <span className="history-meta">{(data.action_items || []).length} items</span>
                {data.id ? (
                  <button
                    className="secondary-btn"
                    type="button"
                    disabled={isSyncingFeishu}
                    onClick={() => onSyncFeishu(data.id)}
                  >
                    {isSyncingFeishu ? "Syncing..." : "Sync to Feishu"}
                  </button>
                ) : null}
              </div>
            </div>
            <div className="result-card-body">
              <ActionItems items={data.action_items || []} />
            </div>
          </section>
        </div>

        <section className="result-card">
          <div className="result-card-head">
            <div>
              <p className="eyebrow">Follow-up Plan</p>
              <h2>Next-step Coordination</h2>
            </div>
            <span className="history-meta">
              Generated from summary, action items, and insights
            </span>
          </div>
          <MarkdownBlock value={data.follow_up || "No follow-up generated."} />
        </section>

        <div className="results-secondary">
          <section className="secondary-card">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Meeting Insights</p>
                <h2>Signals and Decisions</h2>
              </div>
              <span className="history-meta">Secondary analysis</span>
            </div>
            <div className="insight-block scroll-surface">
              <article className="insight-cluster">
                <p>
                  <strong>Tone:</strong> {insights.meeting_tone || "Unavailable"}
                </p>
              </article>
              <article className="insight-cluster">
                <strong>Key Decisions</strong>
                <BulletList
                  items={insights.key_decisions}
                  emptyText="No decisions captured."
                />
              </article>
              <article className="insight-cluster">
                <strong>Blockers</strong>
                <BulletList items={insights.blockers} emptyText="No blockers captured." />
              </article>
              <article className="insight-cluster">
                <strong>Next Focus</strong>
                <BulletList
                  items={insights.next_focus}
                  emptyText="No next-focus items captured."
                />
              </article>
            </div>
          </section>

          <section className="secondary-card">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Speaker Turns</p>
                <h2>Conversation Timeline</h2>
              </div>
              <span className="history-meta">{data.diarization_status || "not_available"}</span>
            </div>
            <div className="collapse-shell">
              <p className="muted">
                Diarization: {data.diarization_status || "not_available"} (
                {data.diarization_backend || "none"})
              </p>
              {data.diarization_error ? (
                <p className="muted">Detail: {data.diarization_error}</p>
              ) : null}
              <CollapseSection targetId="speaker-scroll">
                <div className="speaker-scroll scroll-surface">
                  <SpeakerSegmentList
                    segments={data.speaker_segments || []}
                    status={data.diarization_status}
                  />
                </div>
              </CollapseSection>
            </div>
          </section>

          <section className="secondary-card secondary-card-wide">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Transcript</p>
                <h2>Cleaned Meeting Transcript</h2>
              </div>
              <span className="history-meta">Review reference</span>
            </div>
            <CollapseSection targetId="raw-transcript">
              <div className="transcript-panel scroll-surface">{transcriptText}</div>
            </CollapseSection>
          </section>
        </div>
      </div>
    </section>
  );
}
