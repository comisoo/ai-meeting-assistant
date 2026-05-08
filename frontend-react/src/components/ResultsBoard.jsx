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

function KeywordCloud({ items }) {
  if (!items?.length) {
    return <p className="muted">No keyword cloud available.</p>;
  }

  return (
    <div className="keyword-cloud">
      {items.map((item, index) => (
        <span className="keyword-chip" key={`${item}-${index}`}>
          {item}
        </span>
      ))}
    </div>
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

function SpeakingShare({ items }) {
  if (!items?.length) {
    return <p className="muted">No speaker-share data available.</p>;
  }

  return (
    <div className="share-stack">
      {items.map((item, index) => (
        <article className="share-row" key={`${item.speaker_label}-${index}`}>
          <div className="share-copy">
            <strong>{item.speaker_label}</strong>
            <span className="history-meta">{item.duration_seconds}s spoken</span>
          </div>
          <div className="share-meter">
            <div
              className="share-meter-fill"
              style={{ width: `${Math.max(4, item.share_percent || 0)}%` }}
            ></div>
          </div>
          <strong className="share-percent">{item.share_percent}%</strong>
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
  const actionCount = (data.action_items || []).length;
  const speakerCount = (data.speaker_segments || []).length;
  const sentimentScore = Number.isFinite(insights.sentiment_score)
    ? insights.sentiment_score
    : 0.5;
  const efficiencyScore = Number.isFinite(insights.efficiency_score)
    ? insights.efficiency_score
    : 0;

  return (
    <section className="results-board">
      <div className="results-layout">
        <section className="result-overview surface-panel">
          <div className="overview-pill">
            <span className="overview-label">Template</span>
            <strong>{data.template || "general"}</strong>
          </div>
          <div className="overview-pill">
            <span className="overview-label">Action Items</span>
            <strong>{actionCount}</strong>
          </div>
          <div className="overview-pill">
            <span className="overview-label">Speaker Turns</span>
            <strong>{speakerCount}</strong>
          </div>
          <div className="overview-pill">
            <span className="overview-label">Diarization</span>
            <strong>{data.diarization_status || "not_available"}</strong>
          </div>
        </section>

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
                <span className="history-meta">{actionCount} items</span>
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
                <h2>Quality Analysis</h2>
              </div>
              <span className="history-meta">Secondary analysis</span>
            </div>
            <div className="insight-block scroll-surface">
              <article className="insight-cluster">
                <div className="metric-row">
                  <div>
                    <strong>Sentiment</strong>
                    <p className="muted">
                      {insights.sentiment_label || insights.meeting_tone || "Unavailable"}
                    </p>
                  </div>
                  <span className="metric-pill">{sentimentScore.toFixed(2)}</span>
                </div>
                <div className="score-track">
                  <div
                    className="score-track-fill"
                    style={{ width: `${Math.max(6, sentimentScore * 100)}%` }}
                  ></div>
                </div>
              </article>
              <article className="insight-cluster">
                <div className="metric-row">
                  <div>
                    <strong>Efficiency Score</strong>
                    <p className="muted">{insights.efficiency_reason || "No explanation available."}</p>
                  </div>
                  <span className="metric-pill">{efficiencyScore.toFixed(1)}/10</span>
                </div>
                <div className="score-track score-track-wide">
                  <div
                    className="score-track-fill score-track-fill-accent"
                    style={{ width: `${Math.max(6, efficiencyScore * 10)}%` }}
                  ></div>
                </div>
              </article>
              <article className="insight-cluster">
                <strong>Speaking Share</strong>
                <SpeakingShare items={insights.speaking_share} />
              </article>
              <article className="insight-cluster">
                <strong>Keyword Cloud</strong>
                <KeywordCloud items={insights.keyword_cloud} />
              </article>
              <article className="insight-cluster">
                <strong>Meeting Rhythm</strong>
                <BulletList items={insights.meeting_rhythm} emptyText="No rhythm notes available." />
              </article>
              <article className="insight-cluster">
                <strong>Key Decisions</strong>
                <BulletList items={insights.key_decisions} emptyText="No decisions captured." />
              </article>
              <article className="insight-cluster">
                <strong>Blockers</strong>
                <BulletList items={insights.blockers} emptyText="No blockers captured." />
              </article>
              <article className="insight-cluster">
                <strong>Next Focus</strong>
                <BulletList items={insights.next_focus} emptyText="No next-focus items captured." />
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
