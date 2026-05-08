const STEP_LABELS = [
  "1. Uploading input",
  "2. Cleaning transcript",
  "3. Generating summary",
  "4. Extracting action items",
  "5. Building insights and follow-up",
];

export function ProcessingStatus({ status }) {
  if (!status.visible) {
    return null;
  }

  return (
    <section className="processing-status surface-panel">
      <div className="panel-head compact">
        <div>
          <p className="eyebrow">Pipeline Status</p>
          <h2>Processing</h2>
        </div>
        <div className="status-progress-meta">
          <span className="status-note">Live progress</span>
          <strong>{Math.round(status.progress)}%</strong>
        </div>
      </div>
      <div className="status-steps">
        {STEP_LABELS.map((label, index) => {
          const stepState = status.steps[index] || "idle";
          const className = stepState === "idle" ? "step" : `step ${stepState}`;
          return (
            <div className={className} key={label}>
              {label}
            </div>
          );
        })}
      </div>
      <div className="loader-bar">
        <div className="fill" style={{ width: `${status.progress}%` }}></div>
      </div>
    </section>
  );
}
