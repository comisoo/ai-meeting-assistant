import { useRef, useState } from "react";
import { getTemplateLabel } from "../utils.js";

function getFileFormatSummary(file) {
  if (!file) {
    return "Audio / TXT";
  }

  const extension = file.name?.split(".").pop()?.toUpperCase();
  return extension || file.type || "Unknown";
}

export function UploadWorkspace({
  selectedFile,
  template,
  onTemplateChange,
  onFileSelect,
  onProcess,
  isProcessing,
}) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const title = selectedFile ? selectedFile.name : "Drop a meeting file or click to browse";
  const badge = selectedFile ? "File ready" : "Upload input";
  const subtitle = selectedFile
    ? "The selected file will be cleaned, summarized, analyzed, and stored in history."
    : "Supported formats include meeting audio and plain .txt transcripts.";
  const fileSize = selectedFile ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB` : "Not provided";

  function openFilePicker() {
    inputRef.current?.click();
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  }

  return (
    <section className="workspace-toolbar surface-panel">
      <div className="toolbar-copy">
        <div>
          <p className="eyebrow">New Meeting</p>
          <h2>Upload input and generate minutes</h2>
        </div>
        <p className="panel-caption">
          Use the control panel to prepare a new meeting record. The generated
          output will prioritize summary, action items, quality insights, and
          follow-up guidance.
        </p>
      </div>

      <div className="toolbar-form">
        <div
          className={`drop-zone ${isDragging ? "dragover" : ""}`}
          onClick={openFilePicker}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <div className="drop-badge">{badge}</div>
          <div className="drop-copy">
            <p className="drop-title">{title}</p>
            <p className="subtitle">{subtitle}</p>
          </div>
          <button className="secondary-btn drop-action" type="button">
            Choose file
          </button>
          <input
            ref={inputRef}
            type="file"
            hidden
            accept="audio/*,.txt"
            onChange={handleFileChange}
          />
        </div>

        <div className="workspace-form-grid">
          <div className="field-group surface-subpanel">
            <label htmlFor="template-select">Meeting Template</label>
            <select
              id="template-select"
              value={template}
              onChange={(event) => onTemplateChange(event.target.value)}
            >
              <option value="academic">Academic / Research Meeting</option>
              <option value="daily">Agile Daily Stand-up</option>
              <option value="brainstorm">Brainstorming Session</option>
              <option value="client">Client Pitch</option>
              <option value="general">General Meeting</option>
            </select>
            <p className="field-helper">
              The template shapes summary structure, action extraction, and
              follow-up emphasis.
            </p>
          </div>

          <div className="upload-summary-card">
            <div className="upload-summary-topline">
              <p className="eyebrow">Current File</p>
              <span className={`status-chip ${selectedFile ? "status-chip-ready" : ""}`}>
                {selectedFile ? "Ready to process" : "Waiting for upload"}
              </span>
            </div>

            <div className="upload-summary-grid">
              <div className="upload-summary-row">
                <span className="upload-summary-label">Name</span>
                <strong>{selectedFile?.name || "No file selected"}</strong>
              </div>
              <div className="upload-summary-row">
                <span className="upload-summary-label">Format</span>
                <strong>{getFileFormatSummary(selectedFile)}</strong>
              </div>
              <div className="upload-summary-row">
                <span className="upload-summary-label">Size</span>
                <strong>{fileSize}</strong>
              </div>
              <div className="upload-summary-row">
                <span className="upload-summary-label">Template</span>
                <strong>{getTemplateLabel(template)}</strong>
              </div>
            </div>
          </div>
        </div>

        <div className="control-row control-row-actions">
          <div className="upload-note">
            Output package: <strong>Summary</strong>, <strong>Action Items</strong>,
            <strong> Meeting Insights</strong>, <strong>Follow-up Plan</strong>, and
            evidence panels for transcript review.
          </div>
          <button
            className="primary-btn"
            type="button"
            disabled={!selectedFile || isProcessing}
            onClick={onProcess}
          >
            {isProcessing ? "Generating output..." : "Generate meeting output"}
          </button>
        </div>
      </div>
    </section>
  );
}
