import React from "react";
import { createRoot } from "react-dom/client";

// Self-hosted variable fonts (no CDN dependency): a technical mono face for
// headings/figures/IDs/audit, and a clean sans for body copy. See docs/polish-todo.md.
import "@fontsource-variable/jetbrains-mono";
import "@fontsource-variable/inter";

import App from "./App.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
