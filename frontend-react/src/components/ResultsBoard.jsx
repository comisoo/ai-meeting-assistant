import { useMemo, useState } from "react";
import { marked } from "marked";
import {
  buildMeetingExportText,
  formatDateTime,
  formatSeconds,
  formatParticipationBalance,
  formatSentimentLabel,
  getAcademicSurfaceLabels,
  getCollapseLabels,
  getEfficiencyDescriptor,
  getSpeakerStatusMessage,
  getTemplateLabel,
  isAcademicTemplate,
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
          <div className="action-card-strip"></div>
          <div className="action-card-copy">
            <div className="action-card-heading">
              <h3>{item.task}</h3>
              {item.category ? <span className="action-category-chip">{item.category}</span> : null}
            </div>
            <div className="action-card-meta">
              <span>
                <strong>Owner:</strong> {item.assignee}
              </span>
              <span>
                <strong>Deadline:</strong> {item.deadline}
              </span>
            </div>
          </div>
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
    <div className="speaker-timeline">
      {segments.map((segment, index) => (
        <article className="speaker-timeline-item" key={`${segment.start}-${segment.end}-${index}`}>
          <div className="speaker-time-rail">
            <span className="speaker-time-badge">{formatSeconds(segment.start)}</span>
            <div className="speaker-rail-line"></div>
            <span className="speaker-time-badge speaker-time-badge-end">
              {formatSeconds(segment.end)}
            </span>
          </div>
          <div className="speaker-card">
            <div className="speaker-timeline-marker"></div>
            <div className="speaker-card-copy">
              <div className="speaker-head">
                <div className="speaker-head-copy">
                  <p className="speaker-name">{segment.speaker_label || segment.speaker}</p>
                  <span className="speaker-duration-chip">
                    {(segment.end - segment.start).toFixed(1)}s segment
                  </span>
                </div>
                <span className="history-meta">
                  {formatSeconds(segment.start)} - {formatSeconds(segment.end)}
                </span>
              </div>
              <p>{segment.text}</p>
            </div>
          </div>
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

function ResultsSkeleton() {
  return (
    <section className="results-skeleton">
      <div className="result-overview surface-panel skeleton-panel">
        {Array.from({ length: 4 }).map((_, index) => (
          <div className="overview-pill skeleton-block" key={index}></div>
        ))}
      </div>

      <section className="summary-card summary-card-primary skeleton-panel">
        <div className="skeleton-heading skeleton-block"></div>
        <div className="skeleton-lines">
          <div className="skeleton-line skeleton-block"></div>
          <div className="skeleton-line skeleton-block"></div>
          <div className="skeleton-line skeleton-block short"></div>
        </div>
      </section>

      <div className="results-main-grid">
        <section className="result-card skeleton-panel">
          <div className="skeleton-heading skeleton-block"></div>
          <div className="skeleton-card-stack">
            {Array.from({ length: 3 }).map((_, index) => (
              <div className="skeleton-item-card skeleton-block" key={index}></div>
            ))}
          </div>
        </section>

        <section className="secondary-card skeleton-panel">
          <div className="skeleton-heading skeleton-block"></div>
          <div className="skeleton-metrics-grid">
            {Array.from({ length: 3 }).map((_, index) => (
              <div className="quality-metric skeleton-block" key={index}></div>
            ))}
          </div>
          <div className="skeleton-line skeleton-block"></div>
          <div className="skeleton-line skeleton-block short"></div>
        </section>
      </div>
    </section>
  );
}

export function ResultsBoard({ data, isProcessing, onSyncFeishu, isSyncingFeishu }) {
  if (!data && isProcessing) {
    return <ResultsSkeleton />;
  }

  if (!data) {
    return (
      <section className="results-empty surface-panel">
        <p className="eyebrow">Awaiting Output</p>
        <h2>No meeting selected yet</h2>
        <p className="panel-caption">
          Upload a meeting file to generate structured minutes, action items,
          insights, and a reusable history record.
        </p>
        <div className="empty-state-grid">
          <article className="empty-state-card">
            <strong>Summary-first review</strong>
            <p className="muted">
              The dashboard prioritizes polished meeting minutes before raw evidence.
            </p>
          </article>
          <article className="empty-state-card">
            <strong>Action-driven output</strong>
            <p className="muted">
              Tasks, owners, and Feishu sync stay close to the main decision surface.
            </p>
          </article>
          <article className="empty-state-card">
            <strong>Evidence on demand</strong>
            <p className="muted">
              Speaker turns and transcript remain available as collapsible proof panels.
            </p>
          </article>
        </div>
      </section>
    );
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
  const qualitySummary = insights.quality_summary || "No meeting quality diagnosis generated.";
  const sentimentLabel = formatSentimentLabel(insights.sentiment_label || insights.meeting_tone);
  const efficiencyLabel = getEfficiencyDescriptor(efficiencyScore);
  const participationBalance = formatParticipationBalance(insights.participation_balance);
  const topSpeaker = insights.speaking_share?.[0]?.speaker_label || "Unavailable";
  const template = data.template || "general";
  const labels = getAcademicSurfaceLabels(template);
  const isAcademic = isAcademicTemplate(template);

  function handleExportText() {
    const exportText = buildMeetingExportText(data);
    const safeBaseName = String(data.filename || "meeting-minutes")
      .replace(/\.[^.]+$/, "")
      .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
      .trim() || "meeting-minutes";

    const blob = new Blob([exportText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${safeBaseName}-minutes.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="results-board">
      <div className="results-layout">
        <section className="result-overview surface-panel">
          <div className="overview-pill">
            <span className="overview-label">Meeting Type</span>
            <strong>{getTemplateLabel(data.template || "general")}</strong>
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

        <section className="summary-card summary-card-primary">
          <div className="result-card-head">
            <div>
              <p className="eyebrow">{labels.summaryEyebrow}</p>
              <h2>{labels.summaryTitle || data.filename || "Meeting Output"}</h2>
              {isAcademic ? (
                <p className="muted summary-context-note">
                  Structured for research goals, experiment updates, findings, and next research steps.
                </p>
              ) : null}
            </div>
            <div className="summary-head-meta">
              <button className="secondary-btn" type="button" onClick={handleExportText}>
                Export .txt
              </button>
              <span className="summary-meta-pill">{getTemplateLabel(template)}</span>
              <span className="history-meta">{formatDateTime(data.created_at)}</span>
            </div>
          </div>
          <MarkdownBlock value={data.summary || "No summary generated."} />
        </section>

        <div className="results-main-grid">
          <section className="result-card action-card-panel">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">{labels.actionEyebrow}</p>
                <h2>{labels.actionTitle}</h2>
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

          <section className="secondary-card insights-panel">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Meeting Insights</p>
                <h2>Quality Analysis</h2>
              </div>
              <span className="history-meta">{labels.insightTag}</span>
            </div>

            <div className="insight-block scroll-surface">
              <article className="insight-cluster insight-summary-card">
              <div className="quality-metrics-grid">
                  <div className="quality-metric quality-metric-sentiment">
                    <span className="quality-metric-label">Sentiment</span>
                    <strong>{sentimentLabel}</strong>
                    <span className="history-meta">{sentimentScore.toFixed(2)}</span>
                  </div>
                  <div className="quality-metric quality-metric-efficiency">
                    <span className="quality-metric-label">Efficiency</span>
                    <strong>{efficiencyLabel}</strong>
                    <span className="history-meta">{efficiencyScore.toFixed(1)}/10</span>
                  </div>
                  <div className="quality-metric quality-metric-participation">
                    <span className="quality-metric-label">Participation</span>
                    <strong>{participationBalance}</strong>
                    <span className="history-meta">Lead: {topSpeaker}</span>
                  </div>
                </div>
                <p className="quality-summary-copy">{qualitySummary}</p>
              </article>

              <div className="insight-diagnostic-grid">
                <article className="insight-cluster">
                  <div className="metric-row">
                    <div>
                      <strong>Sentiment</strong>
                      <p className="muted">Overall meeting tone and emotional alignment.</p>
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
                  <strong>Keyword Cloud</strong>
                  <p className="muted insight-helper-text">
                    Representative topics extracted from the cleaned transcript.
                  </p>
                  <KeywordCloud items={insights.keyword_cloud} />
                </article>

                <article className="insight-cluster">
                  <strong>Meeting Rhythm</strong>
                  <p className="muted insight-helper-text">
                    Phase-based observations about pacing, focus, and drift.
                  </p>
                  <BulletList items={insights.meeting_rhythm} emptyText="No rhythm notes available." />
                </article>
              </div>

              <article className="insight-cluster">
                <div className="metric-row">
                  <div>
                    <strong>Speaking Share</strong>
                    <p className="muted">Participation balance: {participationBalance}</p>
                  </div>
                </div>
                <SpeakingShare items={insights.speaking_share} />
              </article>

              <div className="insight-evidence-grid">
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

              <article className="insight-cluster">
                <strong>Recommended Improvements</strong>
                <BulletList
                  items={insights.recommended_improvements}
                  emptyText="No meeting-quality improvements suggested."
                />
              </article>
            </div>
          </section>
        </div>

        <section className="result-card follow-up-panel">
          <div className="result-card-head">
            <div>
              <p className="eyebrow">{labels.followupEyebrow}</p>
              <h2>{labels.followupTitle}</h2>
            </div>
            <span className="history-meta">
              Derived from summary, action items, and insights
            </span>
          </div>
          <MarkdownBlock value={data.follow_up || "No follow-up generated."} />
        </section>

        <div className="results-evidence-grid">
          <section className="secondary-card">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Speaker Timeline</p>
                <h2>Conversation Review</h2>
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

          <section className="secondary-card">
            <div className="result-card-head">
              <div>
                <p className="eyebrow">Transcript</p>
                <h2>Cleaned Transcript</h2>
              </div>
              <span className="history-meta">Evidence panel</span>
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
