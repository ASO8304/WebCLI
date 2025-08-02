// Get terminal container element
const terminal = document.getElementById("terminal");

// Connect to backend WebSocket server 
// let socket = new WebSocket("ws://<target_server_ip>:<target_server_port>/ws");
let socket = new WebSocket("ws://192.168.56.105:12000/ws");

// Command history tracking
let history = [];
let historyIndex = -1;

// Track current input line and its previous value (used for autocomplete)
let inputLine = null;
let restoreInputValue = null;

// When WebSocket is opened
socket.onopen = () => {
  appendLine("🔌 Connecting to server...");
};

// When a message is received from backend
socket.onmessage = (event) => {
  const msg = event.data;

  // Check if it's a prompt for user input
  if (msg.startsWith(">>>PROMPT:")) {
    const promptText = msg.slice(10);
    createInputLine(promptText); // Create new prompt with input
  }

  // Handle autocomplete response
  else if (msg.startsWith("__AUTOCOMPLETE__:")) {
    const suggestion = msg.slice(17).trim();
    console.log("🧠 Received autocomplete:", suggestion);

    // If backend suggests replacing the input
    if (suggestion.startsWith("[REPLACE]")) {
      const newValue = suggestion.slice(9);
      const input = inputLine.querySelector("input");
      input.value = newValue + " "; // Replace input and add space
      input.focus(); // Focus to keep editing
    }

    // Show multiple autocomplete suggestions
    else if (suggestion.startsWith("[MATCHES]")) {
      const matches = suggestion.slice(9).trim();
      appendLine(matches); // Display suggestions
      const input = inputLine.querySelector("input");
      input.focus(); // Keep focus on input
    }

    // No matches found — flash background
    else if (suggestion.startsWith("[NOMATCHES]")) {
      terminal.style.backgroundColor = "#331111";
      setTimeout(() => terminal.style.backgroundColor = "", 100);
    }

    // Unknown format
    else {
      appendLine("❓ Unknown autocomplete suggestion format.");
    }
  }

  // Default case — just print text
  else {
    appendLine(msg);
  }
};

// Handle disconnection
socket.onclose = () => {
  appendLine("❌ Disconnected from server.");
};

// Append a line of text to terminal
function appendLine(text) {
  const line = document.createElement("div");
  line.className = "line";
  line.textContent = text;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight; // Auto-scroll to bottom
}

// Create a new input line for user command
function createInputLine(promptText = "") {
  // Disable previous input line
  if (inputLine) {
    inputLine.querySelector("input").disabled = true;
  }

  // Create new line
  const line = document.createElement("div");
  line.className = "line";

  // Prompt text (e.g. >>>PROMPT:(root)$ )
  const prompt = document.createElement("span");
  prompt.className = "prompt";
  prompt.textContent = promptText;

  // Input field
  const input = document.createElement("input");
  input.className = "input";
  input.type = "text";
  input.autofocus = true;

  // Restore previous value after autocomplete
  if (restoreInputValue !== null) {
    input.value = restoreInputValue;
    restoreInputValue = null;
  }

  // Assemble line and add to terminal
  line.appendChild(prompt);
  line.appendChild(input);
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
  input.focus();

  // Handle key events inside input
  input.addEventListener("keydown", (e) => {
    // Enter: send command to backend
    if (e.key === "Enter") {
      const command = input.value.trim();
      restoreInputValue = null;
      if (command) {
        history.push(command);
        historyIndex = history.length;
        socket.send(command);
      }
    }

    // Up arrow: show previous command
    else if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex--;
        input.value = history[historyIndex];
      }
      e.preventDefault();
    }

    // Down arrow: show next command
    else if (e.key === "ArrowDown") {
      if (historyIndex < history.length - 1) {
        historyIndex++;
        input.value = history[historyIndex];
      } else {
        historyIndex = history.length;
        input.value = "";
      }
      e.preventDefault();
    }

    // Tab: trigger autocomplete request
    else if (e.key === "Tab") {
      e.preventDefault();
      setTimeout(() => {
        const currentInput = input.value;
        restoreInputValue = currentInput;
        socket.send(`__TAB__:${currentInput}`);
      }, 0);
    }

    // Ctrl+C: send interrupt signal
    else if (e.ctrlKey && e.key === "c") {
      e.preventDefault();
      restoreInputValue = null;
      socket.send("__INTERRUPT__");
    }

    // Ctrl+L: clear screen except input
    else if (e.ctrlKey && (e.key === "l" || e.key === "L")) {
      e.preventDefault();
      if (inputLine) {
        Array.from(terminal.children).forEach(child => {
          if (child !== inputLine) {
            terminal.removeChild(child);
          }
        });
        terminal.scrollTop = 0;
        const input = inputLine.querySelector("input");
        if (input && !input.disabled) {
          input.focus();
        }
      }
    }
  });

  // Auto-focus input on terminal click
  document.addEventListener("click", () => {
    if (inputLine) {
      const input = inputLine.querySelector("input");
      if (input && !input.disabled) {
        input.focus();
      }
    }
  });

  inputLine = line; // Track current input line
}
