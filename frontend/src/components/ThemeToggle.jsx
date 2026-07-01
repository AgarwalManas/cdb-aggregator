import { useEffect, useState } from "react";

import { applyTheme, currentTheme, hasStoredChoice } from "../theme.js";

const Moon = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
  </svg>
);

const Sun = () => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
);

export default function ThemeToggle() {
  const [theme, setTheme] = useState(currentTheme);

  // Follow the OS setting live — but only until the user makes an explicit choice.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (event) => {
      if (!hasStoredChoice()) {
        const sys = event.matches ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", sys);
        setTheme(sys);
      }
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    applyTheme(next);
    setTheme(next);
  }

  const isDark = theme === "dark";
  const label = `Switch to ${isDark ? "light" : "dark"} mode`;
  return (
    <button className="theme-toggle" onClick={toggle} aria-label={label} title={label}>
      {isDark ? <Sun /> : <Moon />}
    </button>
  );
}
