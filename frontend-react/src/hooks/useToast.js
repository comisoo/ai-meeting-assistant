import { useCallback, useRef, useState } from "react";

export function useToast() {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());

  const removeToast = useCallback((id) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      window.clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((items) => items.filter((item) => item.id !== id));
  }, []);

  const pushToast = useCallback(
    ({ title, message, tone = "info", duration = 3600 }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setToasts((items) => [...items, { id, title, message, tone }]);

      const timer = window.setTimeout(() => {
        removeToast(id);
      }, duration);
      timersRef.current.set(id, timer);
    },
    [removeToast],
  );

  const notifySuccess = useCallback(
    (title, message) => pushToast({ title, message, tone: "success" }),
    [pushToast],
  );

  const notifyError = useCallback(
    (title, message) => pushToast({ title, message, tone: "error", duration: 4800 }),
    [pushToast],
  );

  const notifyInfo = useCallback(
    (title, message) => pushToast({ title, message, tone: "info" }),
    [pushToast],
  );

  return {
    toasts,
    removeToast,
    notifyError,
    notifyInfo,
    notifySuccess,
  };
}
