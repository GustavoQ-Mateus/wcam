import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { LANGUAGE, t } from "./data/language";
import { Router } from "./router";
import "./styles/tokens.scss";
import "./styles/base.scss";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Missing #root element");
}

document.documentElement.lang = LANGUAGE;
document.title = t("app.name");

createRoot(root).render(
  <StrictMode>
    <Router />
  </StrictMode>,
);
