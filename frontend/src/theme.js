// Light/dark theme. Applied as a `data-theme` attribute on <html>; the CSS token
// blocks in styles.css key off it. The *initial* value is set by a tiny inline
// script in index.html (before first paint, so there's no flash of the wrong
// theme); this module reads it, flips it, and persists an explicit choice.

const KEY = "cdb-theme";

export function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // storage blocked (e.g. private mode) — the choice just won't survive a reload
  }
}

export function hasStoredChoice() {
  try {
    return localStorage.getItem(KEY) != null;
  } catch {
    return false;
  }
}
