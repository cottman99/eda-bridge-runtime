import assert from "node:assert/strict";
import { test } from "node:test";

import { RuntimeClient } from "../lib/runtime-client.mjs";

test("default client timeout exceeds Runtime's bounded five-minute wait", () => {
  const client = new RuntimeClient();
  assert.equal(client.timeoutMs, 330_000);
});

test("generated profile Python launches the Runtime module", () => {
  const client = new RuntimeClient({
    env: { EDA_RUNTIME_PYTHON: "D:/Python/python.exe" },
  });
  assert.equal(client.command, "D:/Python/python.exe");
  assert.deepEqual(client.args, ["-m", "eda_bridge_runtime.cli", "mcp", "serve"]);
});

test("explicit executable override keeps console-script arguments", () => {
  const client = new RuntimeClient({
    command: "D:/runtime/eda-runtime.exe",
    env: { EDA_RUNTIME_PYTHON: "D:/Python/python.exe" },
  });
  assert.equal(client.command, "D:/runtime/eda-runtime.exe");
  assert.deepEqual(client.args, ["mcp", "serve"]);
});

test("environment executable override outranks generated profile Python", () => {
  const client = new RuntimeClient({
    env: {
      EDA_RUNTIME_COMMAND: "D:/runtime/eda-runtime.exe",
      EDA_RUNTIME_PYTHON: "D:/Python/python.exe",
    },
  });
  assert.equal(client.command, "D:/runtime/eda-runtime.exe");
  assert.deepEqual(client.args, ["mcp", "serve"]);
});

test("persistent client lists the installed Runtime tools", async () => {
  const client = new RuntimeClient({
    command: process.env.EDA_RUNTIME_COMMAND ?? "eda-runtime",
    timeoutMs: 10_000,
    clientInfo: { name: "pi-agent-test", version: "0.84.4" },
  });
  try {
    const result = await client.listTools();
    assert.equal(result.tools.length, 11);
    assert.deepEqual(
      result.tools.map((tool) => tool.name),
      [
        "eda.context.resolve",
        "eda.connections.list",
        "eda.connection.reset",
        "eda.capabilities",
        "eda.read",
        "eda.submit",
        "eda.run_plan",
        "eda.run.get",
        "eda.job.status",
        "eda.job.wait",
        "eda.job.events",
      ],
    );
    const listed = await client.callTool("eda.connections.list", {
      purpose: "Verify the isolated Pi Runtime adapter",
    });
    assert.equal(listed.isError, false);
    assert.equal(listed.structuredContent.status, "ready");
  } finally {
    await client.close();
  }
});
