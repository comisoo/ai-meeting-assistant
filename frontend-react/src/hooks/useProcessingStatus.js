import { useCallback, useMemo, useRef, useState } from "react";

const STEP_COUNT = 5;

function updateStatusStep(steps, index, value) {
  return steps.map((item, stepIndex) => (stepIndex === index ? value : item));
}

export function useProcessingStatus() {
  const initialStatus = useMemo(
    () => ({
      visible: false,
      progress: 10,
      steps: Array.from({ length: STEP_COUNT }, () => "idle"),
    }),
    [],
  );

  const [processingStatus, setProcessingStatus] = useState(initialStatus);
  const timeoutsRef = useRef([]);

  const clearProgressTimers = useCallback(() => {
    timeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
    timeoutsRef.current = [];
  }, []);

  const resetProcessingStatus = useCallback(() => {
    clearProgressTimers();
    setProcessingStatus(initialStatus);
  }, [clearProgressTimers, initialStatus]);

  const beginProgressSimulation = useCallback(() => {
    clearProgressTimers();
    setProcessingStatus({
      visible: true,
      progress: 18,
      steps: updateStatusStep(initialStatus.steps, 0, "active"),
    });

    const milestones = [
      {
        delay: 300,
        next: (state) => ({
          ...state,
          progress: 36,
          steps: updateStatusStep(
            updateStatusStep(state.steps, 0, "complete"),
            1,
            "active",
          ),
        }),
      },
      {
        delay: 900,
        next: (state) => ({
          ...state,
          progress: 58,
          steps: updateStatusStep(
            updateStatusStep(state.steps, 1, "complete"),
            2,
            "active",
          ),
        }),
      },
      {
        delay: 1500,
        next: (state) => ({
          ...state,
          progress: 78,
          steps: updateStatusStep(
            updateStatusStep(state.steps, 2, "complete"),
            3,
            "active",
          ),
        }),
      },
      {
        delay: 2100,
        next: (state) => ({
          ...state,
          progress: 92,
          steps: updateStatusStep(
            updateStatusStep(state.steps, 3, "complete"),
            4,
            "active",
          ),
        }),
      },
    ];

    timeoutsRef.current = milestones.map(({ delay, next }) =>
      window.setTimeout(() => {
        setProcessingStatus((state) => next(state));
      }, delay),
    );
  }, [clearProgressTimers, initialStatus]);

  const markProcessingError = useCallback(() => {
    clearProgressTimers();
    setProcessingStatus((state) => ({
      ...state,
      steps: state.steps.map((item) => (item === "complete" ? item : "error")),
    }));
  }, [clearProgressTimers]);

  const markProcessingComplete = useCallback(() => {
    clearProgressTimers();
    setProcessingStatus((state) => ({
      ...state,
      progress: 100,
      steps: state.steps.map((item, index) => {
        if (index < STEP_COUNT - 1) {
          return item === "idle" ? "complete" : item === "error" ? "error" : "complete";
        }
        return "complete";
      }),
    }));
  }, [clearProgressTimers]);

  return {
    processingStatus,
    beginProgressSimulation,
    clearProgressTimers,
    markProcessingComplete,
    markProcessingError,
    resetProcessingStatus,
  };
}
