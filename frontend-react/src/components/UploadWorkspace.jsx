import { useRef, useState } from "react";
import { getTemplateLabel } from "../utils.js";

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

  const title = selectedFile ? selectedFile.name : "Drag and drop a meeting file";
  const badge = selectedFile ? "Ready" : "Upload";
  const subtitle = selectedFile
    ? `Template: ${getTemplateLabel(template)}`
    : "Supported formats: audio files and `.txt` transcripts";
  const formatHint = selectedFile
    ? `${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`
    : "Audio / TXT";

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
        <p className="eyebrow">Input Workspace</p>
        <h2>Upload and Generate</h2>
        <p className="panel-caption">
          Upload meeting audio or a <code>.txt</code> transcript, choose the most suitable
          template, and generate structured notes.
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
          <input
            ref={inputRef}
            type="file"
            hidden
            accept="audio/*,.txt"
            onChange={handleFileChange}
          />
        </div>

        <div className="workspace-form-grid">
          <div className="field-group">
            <label htmlFor="template-select">Meeting Template</label>
            <select
              id="template-select"
              value={template}
              onChange={(event) => onTemplateChange(event.target.value)}
            >
              <option value="daily">Agile Daily Stand-up</option>
              <option value="brainstorm">Brainstorming Session</option>
              <option value="client">Client Pitch</option>
              <option value="general">General Meeting</option>
            </select>
          </div>

          <div className="upload-summary-card">
            <div className="upload-summary-row">
              <span className="upload-summary-label">Selected</span>
              <strong>{selectedFile ? "1 file ready" : "Waiting for file"}</strong>
            </div>
            <div className="upload-summary-row">
              <span className="upload-summary-label">Format</span>
              <strong>{formatHint}</strong>
            </div>
            <div className="upload-summary-row">
              <span className="upload-summary-label">Template</span>
              <strong>{getTemplateLabel(template)}</strong>
            </div>
          </div>
        </div>

        <div className="control-row control-row-actions">
          <div className="upload-note">
            Structured outputs will include summary, action items, insights, and follow-up.
          </div>
          <button
            className="primary-btn"
            type="button"
            disabled={!selectedFile || isProcessing}
            onClick={onProcess}
          >
            {isProcessing ? "Generating..." : "Generate Minutes"}
          </button>
        </div>
      </div>
    </section>
  );
}
