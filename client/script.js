/* ─────────── Terminal + WebSocket Frontend ─────────── */
/* eslint-disable no-console                            */

console.log(
  "%c✅ script.js (suggest-prompt + no spellcheck) loaded",
  "color:lime;font-weight:bold"
);

/* -------------- DOM + WebSocket setup --------------- */
const terminal = document.getElementById("terminal");

// Manual connection (bypass nginx)
// const socket = new WebSocket("ws://192.168.56.105:12000/ws");

// Default: through nginx reverse-proxy
const loc        = window.location;
const wsProtocol = loc.protocol === "https:" ? "wss" : "ws";
const socket     = new WebSocket(`${wsProtocol}://${loc.host}/cli/ws`);

/* ---------------------- State ----------------------- */
let history     = [];
let historyIdx  = -1;
let inputLine   = null;     // active <div class="line">
let restoreBuf  = null;     // temp buffer for autocomplete

/* ------------- WebSocket event handlers ------------- */
socket.addEventListener("open", () => {
  appendLine("🔌 Connecting to server...");
});

socket.addEventListener("message", ({ data }) => {
  if (data.startsWith(">>>PROMPT:")) {
    createInputLine(data.slice(10));           // strip prefix
    return;
  }
  if (data.startsWith("__AUTOCOMPLETE__:")) {
    handleAutocomplete(data.slice(17).trim());
    return;
  }
  appendLine(data);                            // regular output
});

socket.addEventListener("close", () => {
  appendLine("❌ Disconnected from server.");
});

/* ----------------- Helper: print line ---------------- */
function appendLine(text) {
  const line = document.createElement("div");
  line.className = "line";
  line.textContent = text;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

/* ------------ Helper: autocomplete handler ---------- */
function handleAutocomplete(payload) {
  if (!inputLine) return;
  const inp     = inputLine.querySelector("input");
  const prompt  = inputLine.querySelector(".prompt");
  if (!inp) return;

  if (payload.startsWith("[REPLACE]")) {
    inp.value = payload.slice(9) + " ";
    inp.focus();
  } else if (payload.startsWith("[MATCHES]")) {
    /* show list then spawn new prompt pre-filled with existing input */
    appendLine(payload.slice(9).trim());

    const currentTyped = inp.value;
    inp.disabled = true;                 // freeze old input

    restoreBuf = currentTyped;           // will be restored in new prompt
    createInputLine(prompt.textContent); // build fresh prompt on next line
  } else if (payload.startsWith("[NOMATCHES]")) {
    terminal.style.backgroundColor = "#331111";
    setTimeout(() => (terminal.style.backgroundColor = ""), 100);
  } else {
    appendLine("❓ Unknown autocomplete payload.");
  }
}

/* --------------- Visual feedback helper ------------- */
function showTempDot(promptEl) {
  const dot = document.createElement("span");
  dot.className = "pw-dot";
  dot.textContent = " •";
  promptEl.appendChild(dot);
  setTimeout(() => promptEl.removeChild(dot), 120);
}

/* ------------- Core: create new prompt -------------- */
function createInputLine(promptText = "") {
  /* disable previous input */
  if (inputLine) inputLine.querySelector("input").disabled = true;

  const line = document.createElement("div");
  line.className = "line";

  const prompt = document.createElement("span");
  prompt.className = "prompt";

  /* Determine if this is a password prompt */
  const pwMode = promptText.startsWith("[PASSWORD]");
  if (pwMode) {
    prompt.textContent = promptText.replace(/^\[PASSWORD]/, "").trim();
  } else {
    prompt.textContent = promptText;
  }

  /* ---- Create input ---- */
  const inp = document.createElement("input");
  inp.className        = "input";
  inp.spellcheck       = false;      // remove red underline
  inp.autocorrect      = "off";
  inp.autocapitalize   = "off";

  if (pwMode) {
    /* Invisible password capture */
    inp.type            = "password";
    inp.style.opacity   = "0";            // hide bullets
    inp.style.caretColor = "transparent"; // hide caret
    inp.autocomplete    = "off";
  } else {
    inp.type = "text";
  }

  /* Restore buffer after autocomplete (non-pw prompts) */
  if (!pwMode && restoreBuf !== null) {
    inp.value  = restoreBuf;
    restoreBuf = null;
  }

  /* Assemble line */
  line.append(prompt, inp);
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
  inp.focus();

  /* ---------- Key handling ---------- */
  let pwBuf = "";                       // only for password mode

  inp.addEventListener("keydown", (e) => {
    /* -------- Invisible password branch -------- */
    if (pwMode) {
      if (e.key === "Enter") {
        socket.send(pwBuf);
        pwBuf = "";
        showTempDot(prompt);
      } else if (e.key === "Backspace") {
        pwBuf = pwBuf.slice(0, -1);
        showTempDot(prompt);
      } else if (e.key.length === 1) {  // printable char
        pwBuf += e.key;
        showTempDot(prompt);
      }
      e.preventDefault();               // suppress visible changes
      return;
    }

    /* -------- Normal prompt branch -------- */
    if (e.key === "Enter") {
      const cmd = inp.value.trim();
      restoreBuf = null;
      if (cmd) {
        history.push(cmd);
        historyIdx = history.length;
        socket.send(cmd);
      }
    } else if (e.key === "ArrowUp") {
      if (historyIdx > 0) {
        historyIdx--;
        inp.value = history[historyIdx];
      }
      e.preventDefault();
    } else if (e.key === "ArrowDown") {
      if (historyIdx < history.length - 1) {
        historyIdx++;
        inp.value = history[historyIdx];
      } else {
        historyIdx = history.length;
        inp.value  = "";
      }
      e.preventDefault();
    } else if (e.key === "Tab") {
      e.preventDefault();
      setTimeout(() => {
        restoreBuf = inp.value;
        socket.send(`__TAB__:${restoreBuf}`);
      }, 0);
    } else if (e.ctrlKey && e.key === "c") {
      e.preventDefault();
      restoreBuf = null;
      socket.send("__INTERRUPT__");
    } else if (e.ctrlKey && (e.key === "l" || e.key === "L")) {
      e.preventDefault();
      Array.from(terminal.children).forEach((child) => {
        if (child !== line) terminal.removeChild(child);
      });
      terminal.scrollTop = 0;
      inp.focus();
    }
  });

  /* Focus input when clicking anywhere on terminal */
  terminal.addEventListener("click", () => {
    if (!inp.disabled) inp.focus();
  });

  inputLine = line;
}
