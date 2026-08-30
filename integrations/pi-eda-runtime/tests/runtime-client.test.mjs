import assert from "node:assert/strict";
import { test } from "node:test";

import { RuntimeClient } from "../lib/runtime-client.mjs";

test("default client timeout exceeds Runtime's bounded five-minute wait", () => {
  const client = new RuntimeClient();
  assert.equal(client.timeoutMs, 330_000);
});

test("persistent client lists the ten installed Runtime tools", async () => {
  const client = new RuntimeClient({
    command: process.env.EDA_RUNTIME_COMMAND ?? "eda-runtime",
    timeoutMs: 10_000,
    clientInfo: { name: "pi-agent-test", version: "0.84.4" },
  });
  try {
    const result = await client.listTools();
    assert.equal(result.tools.length, 10);
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
