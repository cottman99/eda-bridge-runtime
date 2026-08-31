import { spawn } from "node:child_process";

// Runtime accepts an explicit wait of at most five minutes. Leave a small
// transport margin so the client never abandons a valid bounded wait first.
const DEFAULT_TIMEOUT_MS = 330_000;

export class RuntimeClient {
  constructor(options = {}) {
    this.env = options.env ?? process.env;
    const executableOverride = options.command ?? this.env.EDA_RUNTIME_COMMAND;
    const runtimePython = this.env.EDA_RUNTIME_PYTHON;
    this.command = executableOverride ?? runtimePython ?? "eda-runtime";
    this.args = options.args ?? (
      executableOverride || !runtimePython
        ? ["mcp", "serve"]
        : ["-m", "eda_bridge_runtime.cli", "mcp", "serve"]
    );
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    this.clientInfo = options.clientInfo ?? { name: "pi-agent", version: "unknown" };
    this.child = undefined;
    this.starting = undefined;
    this.nextId = 1;
    this.pending = new Map();
    this.buffer = "";
    this.stderr = "";
  }

  async start() {
    if (this.child) return;
    if (this.starting) return this.starting;
    this.starting = this.#start();
    try {
      await this.starting;
    } finally {
      this.starting = undefined;
    }
  }

  async #start() {
    const child = spawn(this.command, this.args, {
      env: this.env,
      shell: false,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
    this.child = child;
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => this.#consume(chunk));
    child.stderr.on("data", (chunk) => {
      this.stderr = (this.stderr + chunk).slice(-4096);
    });
    child.on("error", (error) => this.#fail(error));
    child.on("exit", (code, signal) => {
      const detail = this.stderr.trim();
      this.#fail(
        new Error(
          `EDA Runtime exited (code=${code ?? "none"}, signal=${signal ?? "none"})${detail ? `: ${detail}` : ""}`,
        ),
      );
    });
    await new Promise((resolve, reject) => {
      child.once("spawn", resolve);
      child.once("error", reject);
    });
    await this.#request("initialize", {
      protocolVersion: "2025-11-25",
      capabilities: {},
      clientInfo: this.clientInfo,
    });
  }

  async callTool(name, arguments_, actor = {}) {
    await this.start();
    return this.#request("tools/call", {
      name,
      arguments: arguments_,
      _meta: {
        "io.modelcontextprotocol/clientInfo": this.clientInfo,
        "io.eda-runtime/actor": actor,
      },
    });
  }

  async listTools() {
    await this.start();
    return this.#request("tools/list", {});
  }

  async close() {
    const child = this.child;
    if (!child) return;
    this.child = undefined;
    child.stdin.end();
    await Promise.race([
      new Promise((resolve) => child.once("exit", resolve)),
      new Promise((resolve) => setTimeout(resolve, 1_000)),
    ]);
    if (child.exitCode === null) child.kill();
  }

  #request(method, params) {
    const child = this.child;
    if (!child?.stdin.writable) {
      return Promise.reject(new Error("EDA Runtime is not writable"));
    }
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`EDA Runtime request timed out after ${this.timeoutMs} ms: ${method}`));
      }, this.timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    });
  }

  #consume(chunk) {
    this.buffer += chunk;
    while (true) {
      const newline = this.buffer.indexOf("\n");
      if (newline < 0) return;
      const line = this.buffer.slice(0, newline).replace(/\r$/, "");
      this.buffer = this.buffer.slice(newline + 1);
      if (!line) continue;
      let message;
      try {
        message = JSON.parse(line);
      } catch (error) {
        this.#fail(new Error(`Invalid JSON from EDA Runtime: ${error.message}`));
        continue;
      }
      const pending = this.pending.get(message.id);
      if (!pending) continue;
      this.pending.delete(message.id);
      clearTimeout(pending.timer);
      if (message.error) {
        pending.reject(new Error(message.error.message ?? "EDA Runtime request failed"));
      } else {
        pending.resolve(message.result);
      }
    }
  }

  #fail(error) {
    this.child = undefined;
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }
}
