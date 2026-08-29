import assert from "node:assert/strict";
import { test } from "node:test";

import { RuntimeClient } from "../lib/runtime-client.mjs";

test("persistent client lists the seven installed Runtime tools", async () => {
  const client = new RuntimeClient({
    command: process.env.EDA_RUNTIME_COMMAND ?? "eda-runtime",
    timeoutMs: 10_000,
    clientInfo: { name: "pi-agent-test", version: "0.73.1" },
  });
  try {
    const result = await client.listTools();
    assert.equal(result.tools.length, 7);
    assert.deepEqual(
      result.tools.map((tool) => tool.name),
      [
        "eda.context.resolve",
        "eda.connections.list",
        "eda.connection.reset",
        "eda.capabilities",
        "eda.submit",
        "eda.job.status",
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
