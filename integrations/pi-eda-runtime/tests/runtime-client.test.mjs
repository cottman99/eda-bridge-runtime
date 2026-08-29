import assert from "node:assert/strict";
import { test } from "node:test";

import { RuntimeClient } from "../lib/runtime-client.mjs";

test("persistent client lists the nine installed Runtime tools", async () => {
  const client = new RuntimeClient({
    command: process.env.EDA_RUNTIME_COMMAND ?? "eda-runtime",
    timeoutMs: 10_000,
    clientInfo: { name: "pi-agent-test", version: "0.84.4" },
  });
  try {
    const result = await client.listTools();
    assert.equal(result.tools.length, 9);
    assert.deepEqual(
      result.tools.map((tool) => tool.name),
      [
        "eda.context.resolve",
        "eda.connections.list",
        "eda.connection.reset",
        "eda.capabilities",
        "eda.read",
        "eda.submit",
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
