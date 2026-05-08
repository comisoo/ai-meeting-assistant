import { useState } from "react";

const SUGGESTED_QUESTIONS = [
  "What are the main decisions in this meeting?",
  "What should be prioritized next?",
  "Who owns the current action items?",
];

function RobotIcon() {
  return (
    <svg
      aria-hidden="true"
      className="assistant-launcher-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3v3" />
      <path d="M9 6h6" />
      <rect x="5" y="8" width="14" height="10" rx="3" />
      <path d="M8 18v2" />
      <path d="M16 18v2" />
      <path d="M3 11v4" />
      <path d="M21 11v4" />
      <circle cx="9.5" cy="12.5" r="1" fill="currentColor" />
      <circle cx="14.5" cy="12.5" r="1" fill="currentColor" />
      <path d="M9 15.5c1 .7 5 .7 6 0" />
    </svg>
  );
}

export function MeetingAssistantPanel({ meeting, messages, isLoading, onAsk }) {
  const [draft, setDraft] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  function submitQuestion() {
    const normalized = draft.trim();
    if (!normalized || isLoading) {
      return;
    }
    onAsk(normalized);
    setDraft("");
  }

  function askSuggestedQuestion(question) {
    if (isLoading) {
      return;
    }
    onAsk(question);
    setIsOpen(true);
  }

  return (
    <div className={`assistant-float-shell ${isOpen ? "is-open" : ""}`}>
      <button
        className="assistant-launcher"
        type="button"
        aria-label={isOpen ? "Close meeting assistant" : "Open meeting assistant"}
        onClick={() => setIsOpen((value) => !value)}
      >
        <RobotIcon />
        <span className="assistant-launcher-text">AI</span>
      </button>

      {isOpen ? (
        <section className="assistant-panel surface-panel">
          <div className="panel-head assistant-panel-head">
            <div>
              <p className="eyebrow">Meeting Assistant</p>
              <h2>Ask about the selected meeting</h2>
            </div>
            <button
              className="assistant-close-btn"
              type="button"
              aria-label="Close assistant panel"
              onClick={() => setIsOpen(false)}
            >
              x
            </button>
          </div>

          <p className="panel-caption assistant-panel-caption">
            {meeting
              ? "The assistant is scoped to the current meeting record, including summary, action items, insights, and transcript evidence."
              : "Select or generate a meeting first. The assistant will then answer only from that meeting record."}
          </p>

          {meeting ? (
            <>
              <div className="assistant-suggestions">
                {SUGGESTED_QUESTIONS.map((question) => (
                  <button
                    className="assistant-suggestion-chip"
                    key={question}
                    type="button"
                    disabled={isLoading}
                    onClick={() => askSuggestedQuestion(question)}
                  >
                    {question}
                  </button>
                ))}
              </div>

              <div className="assistant-chat scroll-surface">
                {!messages.length ? (
                  <div className="assistant-empty-state">
                    <strong>No questions yet</strong>
                    <p className="muted">
                      Try asking about decisions, action owners, priorities,
                      blockers, or what happened in a specific part of the discussion.
                    </p>
                  </div>
                ) : (
                  messages.map((message, index) => (
                    <article
                      className={`assistant-message assistant-message-${message.role}`}
                      key={`${message.role}-${index}-${message.content.slice(0, 16)}`}
                    >
                      <span className="assistant-role-label">
                        {message.role === "user" ? "You" : "Assistant"}
                      </span>
                      <p>{message.content}</p>
                    </article>
                  ))
                )}

                {isLoading ? (
                  <article className="assistant-message assistant-message-assistant assistant-message-loading">
                    <span className="assistant-role-label">Assistant</span>
                    <p>Thinking about this meeting record...</p>
                  </article>
                ) : null}
              </div>

              <div className="assistant-input-row">
                <textarea
                  className="assistant-input"
                  placeholder="Ask something about the selected meeting..."
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  rows={3}
                />
                <button
                  className="primary-btn assistant-send-btn"
                  type="button"
                  disabled={!draft.trim() || isLoading}
                  onClick={submitQuestion}
                >
                  {isLoading ? "Asking..." : "Ask assistant"}
                </button>
              </div>
            </>
          ) : (
            <div className="assistant-empty-state">
              <strong>No meeting selected</strong>
              <p className="muted">
                Generate or open a meeting from history, then come back to ask
                follow-up questions here.
              </p>
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
