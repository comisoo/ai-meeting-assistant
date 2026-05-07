import { useCallback, useEffect, useState } from "react";
import {
  fetchMeetingDetail,
  fetchMeetingHistory,
  processMeetingFile,
  removeMeeting,
  syncMeetingToFeishu,
} from "../services/api.js";
import { useProcessingStatus } from "./useProcessingStatus.js";

export function useMeetingWorkspace({ notifyError, notifySuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [template, setTemplate] = useState("general");
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [currentMeetingId, setCurrentMeetingId] = useState(null);
  const [results, setResults] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSyncingFeishu, setIsSyncingFeishu] = useState(false);

  const {
    processingStatus,
    beginProgressSimulation,
    clearProgressTimers,
    markProcessingComplete,
    markProcessingError,
  } = useProcessingStatus();

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const payload = await fetchMeetingHistory(12);
      setHistory(payload.meetings || []);
    } catch (error) {
      notifyError("History Load Failed", error.message);
    } finally {
      setHistoryLoading(false);
    }
  }, [notifyError]);

  useEffect(() => {
    loadHistory();
    return () => {
      clearProgressTimers();
    };
  }, [clearProgressTimers, loadHistory]);

  const handleOpenMeeting = useCallback(
    async (meetingId) => {
      try {
        const meeting = await fetchMeetingDetail(meetingId);
        setCurrentMeetingId(String(meeting.id || meetingId));
        setResults(meeting);
        await loadHistory();
      } catch (error) {
        notifyError("Meeting Load Failed", error.message);
      }
    },
    [loadHistory, notifyError],
  );

  const handleDeleteMeeting = useCallback(
    async (meetingId) => {
      const confirmed = window.confirm("Delete this saved meeting record?");
      if (!confirmed) {
        return;
      }

      try {
        await removeMeeting(meetingId);
        if (currentMeetingId === String(meetingId)) {
          setCurrentMeetingId(null);
          setResults(null);
        }
        await loadHistory();
      } catch (error) {
        notifyError("Delete Failed", error.message);
      }
    },
    [currentMeetingId, loadHistory, notifyError],
  );

  const handleSyncFeishu = useCallback(async (meetingId) => {
    setIsSyncingFeishu(true);
    try {
      const payload = await syncMeetingToFeishu(meetingId);
      const count = payload.synced_count || 0;
      notifySuccess(
        "Feishu Sync Complete",
        `Synced ${count} action item${count === 1 ? "" : "s"} to Feishu.`,
      );
    } catch (error) {
      notifyError("Feishu Sync Failed", error.message);
    } finally {
      setIsSyncingFeishu(false);
    }
  }, [notifyError, notifySuccess]);

  const handleProcess = useCallback(async () => {
    if (!selectedFile || isProcessing) {
      return;
    }

    setIsProcessing(true);
    setResults(null);
    beginProgressSimulation();

    try {
      const data = await processMeetingFile(selectedFile, template);
      markProcessingComplete();
      setCurrentMeetingId(String(data.id || ""));
      setResults(data);
      await loadHistory();
    } catch (error) {
      markProcessingError();
      notifyError("Meeting Generation Failed", error.message);
    } finally {
      setIsProcessing(false);
    }
  }, [
    beginProgressSimulation,
    isProcessing,
    loadHistory,
    markProcessingComplete,
    markProcessingError,
    notifyError,
    selectedFile,
    template,
  ]);

  return {
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
  };
}
