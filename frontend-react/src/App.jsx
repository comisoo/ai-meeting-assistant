import { HistorySidebar } from "./components/HistorySidebar.jsx";
import { UploadWorkspace } from "./components/UploadWorkspace.jsx";
import { ProcessingStatus } from "./components/ProcessingStatus.jsx";
import { ResultsBoard } from "./components/ResultsBoard.jsx";
import { ToastStack } from "./components/ToastStack.jsx";
import { useMeetingWorkspace } from "./hooks/useMeetingWorkspace.js";
import { useToast } from "./hooks/useToast.js";

export default function App() {
  const { notifyError, notifySuccess, removeToast, toasts } = useToast();
  const {
    currentMeetingId,
    handleDeleteMeeting,
    handleOpenMeeting,
    handleProcess,
    handleSyncFeishu,
    history,
    historyLoading,
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
        <section className="hero-shell">
          <div className="hero-copy">
            <p className="eyebrow">Meeting Intelligence Workspace</p>
            <h1>AI Meeting Minutes Assistant</h1>
            <p className="hero-text">
              Turn raw meetings into structured summaries, action items, insights,
              follow-up plans, and reusable session history.
            </p>
          </div>
          <div className="hero-meta-card">
            <span className="meta-kicker">Workflow</span>
            <strong>Transcribe, summarize, extract, review</strong>
            <p>One workspace for upload, processing, retrieval, and transcript review.</p>
          </div>
        </section>

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
              onSyncFeishu={handleSyncFeishu}
              isSyncingFeishu={isSyncingFeishu}
            />
          </section>
        </div>
      </main>
    </>
  );
}
