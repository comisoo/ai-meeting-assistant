import { HistorySidebar } from "./components/HistorySidebar.jsx";
import { UploadWorkspace } from "./components/UploadWorkspace.jsx";
import { ProcessingStatus } from "./components/ProcessingStatus.jsx";
import { ResultsBoard } from "./components/ResultsBoard.jsx";
import { MeetingAssistantPanel } from "./components/MeetingAssistantPanel.jsx";
import { ToastStack } from "./components/ToastStack.jsx";
import { useMeetingWorkspace } from "./hooks/useMeetingWorkspace.js";
import { useToast } from "./hooks/useToast.js";

const CAPABILITY_BADGES = [
  "Speaker-aware",
  "Multi-Agent Workflow",
  "Structured Insights",
  "Feishu Sync Ready",
];

export default function App() {
  const { notifyError, notifySuccess, removeToast, toasts } = useToast();
  const {
    currentMeetingId,
    assistantMessages,
    handleAskAssistant,
    handleDeleteMeeting,
    handleOpenMeeting,
    handleProcess,
    handleSyncFeishu,
    history,
    historyLoading,
    isAssistantLoading,
    isProcessing,
    isSyncingFeishu,
    processingStatus,
    results,
    selectedFile,
    setSelectedFile,
    setTemplate,
    template,
    loadHistory,
  } = useMeetingWorkspace({
    notifyError,
    notifySuccess,
  });

  return (
    <>
      <div className="app-bg"></div>
      <ToastStack toasts={toasts} onDismiss={removeToast} />
      <main className="app-shell">
        <header className="top-header surface-panel">
          <div className="top-header-main">
            <p className="eyebrow">Professional Dashboard</p>
            <h1>AI Meeting Minutes Assistant</h1>
            <p className="hero-text">
              Turn raw meeting audio or transcripts into polished summaries,
              actionable follow-ups, and speaker-aware review artifacts.
            </p>
            <div className="capability-row">
              {CAPABILITY_BADGES.map((badge) => (
                <span className="capability-badge" key={badge}>
                  {badge}
                </span>
              ))}
            </div>
          </div>

          <div className="header-status-board">
            <article className="status-kpi-card">
              <span className="status-kpi-label">Current Template</span>
              <strong>{template}</strong>
              <p>Template-sensitive summarization and action extraction.</p>
            </article>
            <article className="status-kpi-card">
              <span className="status-kpi-label">Saved Meetings</span>
              <strong>{history.length}</strong>
              <p>Persistent history lets users reopen and sync prior outputs.</p>
            </article>
            <article className="status-kpi-card status-kpi-card-accent">
              <span className="status-kpi-label">Workspace Focus</span>
              <strong>
                {results ? "Reviewing generated outputs" : "Ready for a new meeting"}
              </strong>
              <p>
                Summary and Action Items remain the primary decision-making surfaces.
              </p>
            </article>
          </div>
        </header>

        <div className="dashboard-grid">
          <HistorySidebar
            meetings={history}
            isLoading={historyLoading}
            currentMeetingId={currentMeetingId}
            onRefresh={loadHistory}
            onOpenMeeting={handleOpenMeeting}
            onDeleteMeeting={handleDeleteMeeting}
          />

          <section className="workspace-shell">
            <div className="workspace-intro surface-panel">
              <div>
                <p className="eyebrow">Workspace</p>
                <h2>Generate structured meeting output</h2>
              </div>
              <p className="panel-caption">
                Start with a file upload, follow the processing pipeline, and
                review the final outputs in a summary-first dashboard.
              </p>
            </div>

            <section className="control-stack">
              <UploadWorkspace
                selectedFile={selectedFile}
                template={template}
                onTemplateChange={setTemplate}
                onFileSelect={setSelectedFile}
                onProcess={handleProcess}
                isProcessing={isProcessing}
              />
              <ProcessingStatus status={processingStatus} />
            </section>

            <ResultsBoard
              data={results}
              isProcessing={isProcessing}
              onSyncFeishu={handleSyncFeishu}
              isSyncingFeishu={isSyncingFeishu}
            />

          </section>
        </div>
      </main>
      <MeetingAssistantPanel
        meeting={results}
        messages={assistantMessages}
        isLoading={isAssistantLoading}
        onAsk={handleAskAssistant}
      />
    </>
  );
}
