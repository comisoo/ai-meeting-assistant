function copyToastMessage(title, message) {
  const content = `${title}\n${message || ""}`.trim();
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(content).catch(() => {});
  }
}

export function ToastStack({ toasts, onDismiss }) {
  if (!toasts.length) {
    return null;
  }

  return (
    <section className="toast-stack" aria-live="polite" aria-atomic="true">
      {toasts.map((toast) => (
        <article className={`toast-card toast-${toast.tone}`} key={toast.id}>
          <div className="toast-copy">
            <strong>{toast.title}</strong>
            <p>{toast.message}</p>
          </div>
          <div className="toast-actions">
            <button
              className="toast-copy-btn"
              type="button"
              onClick={() => copyToastMessage(toast.title, toast.message)}
            >
              Copy
            </button>
            <button
              className="toast-dismiss"
              type="button"
              aria-label="Dismiss notification"
              onClick={() => onDismiss(toast.id)}
            >
              ×
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
