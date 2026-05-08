const STEP_ITEMS = [
  {
    label: "Input Intake",
    description: "Validating the uploaded file and preparing the processing pipeline.",
  },
  {
    label: "Transcript Cleanup",
    description: "Normalizing transcript quality before downstream reasoning.",
  },
  {
    label: "Summary Drafting",
    description: "Generating structured meeting minutes from the cleaned transcript.",
  },
  {
    label: "Action Extraction",
    description: "Identifying tasks, owners, and meeting commitments.",
  },
  {
    label: "Insight Packaging",
    description: "Building quality analysis and follow-up recommendations.",
  },
];

function getStepVisualLabel(stepState, index) {
  if (stepState === "complete") {
    return "✓";
  }
  if (stepState === "error") {
    return "!";
  }
  return index + 1;
}

export function ProcessingStatus({ status }) {
  if (!status.visible) {
    return null;
  }

  return (
    <section className="processing-status surface-panel">
      <div className="panel-head compact">
        <div>
          <p className="eyebrow">Pipeline Status</p>
          <h2>Meeting generation in progress</h2>
        </div>
        <div className="status-progress-meta">
          <span className="status-note">Estimated progress</span>
          <strong>{Math.round(status.progress)}%</strong>
        </div>
      </div>

      <div className="status-stepper">
        {STEP_ITEMS.map((step, index) => {
          const stepState = status.steps[index] || "idle";
          const className = stepState === "idle" ? "status-step-card" : `status-step-card is-${stepState}`;

          return (
            <article className={className} key={step.label}>
              <div className="status-step-marker">{getStepVisualLabel(stepState, index)}</div>
              <div className="status-step-copy">
                <strong>{step.label}</strong>
                <p>{step.description}</p>
              </div>
            </article>
          );
        })}
      </div>

      <div className="loader-bar">
        <div className="fill" style={{ width: `${status.progress}%` }}></div>
      </div>
    </section>
  );
}
