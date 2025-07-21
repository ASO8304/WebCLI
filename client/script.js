const terminal = document.getElementById("terminal");

let socket = new WebSocket("ws://localhost:12000/ws");
let history = [];
let historyIndex = -1;

let inputLine = null;
let restoreInputValue = null;  // 👈 Stores value temporarily across autocomplete

socket.onopen = () => {
  appendLine("🔌 Connecting to server...");
};

socket.onmessage = (event) => {
  const msg = event.data;

  if (msg.startsWith(">>>PROMPT:")) {
    const promptText = msg.slice(10);
    createInputLine(promptText);
  } else if (msg.startsWith("__AUTOCOMPLETE__:")) {
    const suggestion = msg.slice(17).trim();
    console.log("🧠 Received autocomplete:", suggestion);

    if (suggestion.startsWith("[REPLACE]")) {
      const newValue = suggestion.slice(9);
      const input = inputLine.querySelector("input");
      input.value = newValue + " "; // Add a space to continue typing
      input.focus(); // keep focus to continue editing
      console.log("🔁 Replacing input with:", newValue);
    } else if (suggestion.startsWith("[MATCHES]")) {
      const matches = suggestion.slice(9).trim();
      appendLine(matches); // Show suggestions
      // Do NOT create new input line here, keep editing the current input
      const input = inputLine.querySelector("input");
      input.focus();
    } else if (suggestion.startsWith("[NOMATCHES]")) {
      terminal.style.backgroundColor = "#331111"; // red blink
      setTimeout(() => terminal.style.backgroundColor = "", 100);
    } else {
      appendLine("❓ Unknown autocomplete suggestion format.");
    }
  } else {
    appendLine(msg);
  }
};

socket.onclose = () => {
  appendLine("❌ Disconnected from server.");
};

function appendLine(text) {
  const line = document.createElement("div");
  line.className = "line";
  line.textContent = text;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function createInputLine(promptText = "") {
  if (inputLine) {
    inputLine.querySelector("input").disabled = true;
  }
  const line = document.createElement("div");
  line.className = "line";

  const prompt = document.createElement("span");
  prompt.className = "prompt";
  prompt.textContent = promptText;

  const input = document.createElement("input");
  input.className = "input";
  input.type = "text";
  input.autofocus = true;

  // 👇 Restore value only if set (from autocomplete)
  if (restoreInputValue !== null) {
    input.value = restoreInputValue;
    restoreInputValue = null; // clear it after restoring
  }

  line.appendChild(prompt);
  line.appendChild(input);
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;

  input.focus();

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const command = input.value.trim();
      console.log(command);
      restoreInputValue = null; // clear it after restoring


      if (command) {
        history.push(command);
        historyIndex = history.length;
        socket.send(command);
      }
    } else if (e.key === "ArrowUp") {
      if (historyIndex > 0) {
        historyIndex--;
        input.value = history[historyIndex];
      }
      e.preventDefault();
    } else if (e.key === "ArrowDown") {
      if (historyIndex < history.length - 1) {
        historyIndex++;
        input.value = history[historyIndex];
      } else {
        historyIndex = history.length;
        input.value = "";
      }
      e.preventDefault();
    } else if (e.key === "Tab") {
        e.preventDefault();
        setTimeout(() => {
          const currentInput = input.value;
          console.log("Sending TAB for:", currentInput);
          restoreInputValue = currentInput; // 👈 Store it globally for later restoration
          socket.send(`__TAB__:${currentInput.trim()}`);
        }, 0);
    } else if (e.ctrlKey && e.key === "c") {
        e.preventDefault();
        restoreInputValue = null; 
        socket.send("__INTERRUPT__");  // 👈 Special interrupt message
  }

  });
  document.addEventListener("click", () => {
  if (inputLine) {
    const input = inputLine.querySelector("input");
    if (input && !input.disabled) {
      input.focus();
    }
  }
});

  inputLine = line;
}
