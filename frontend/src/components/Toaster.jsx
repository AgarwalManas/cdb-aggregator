import { createContext, useCallback, useContext, useState } from "react";

// Minimal toast system: wrap the app in <ToastProvider>, call useToast() to get
// a toast(message) function. Toasts auto-dismiss and announce politely to
// screen readers. Kept tiny on purpose — no dependency, no global store.
const ToastContext = createContext(() => {});

export const useToast = () => useContext(ToastContext);

let nextId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const toast = useCallback((message) => {
    const id = ++nextId;
    setToasts((current) => [...current, { id, message }]);
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 3200);
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toaster" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
