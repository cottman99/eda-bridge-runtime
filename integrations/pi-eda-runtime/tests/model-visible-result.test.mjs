import assert from "node:assert/strict";
import { test } from "node:test";

import { modelVisibleResult, runtimeFailed } from "../lib/model-visible-result.mjs";

test("model-visible result exposes durable identifiers and the actual error", () => {
  const value = {
    connection_id: "scratch-connection",
    run: { run_id: "run_1", job_id: "job_1", state: "failed", terminal: true },
    response: { status: "failed", error: { code: "ValueError", message: "bad payload" } },
  };
  const text = modelVisibleResult([{ type: "text", text: "EDA Runtime result: failed" }], value);
  assert.match(text, /"job_id":"job_1"/);
  assert.match(text, /"message":"bad payload"/);
  assert.equal(runtimeFailed(value), true);
});

test("model-visible result keeps a valid compact object when the full value is oversized", () => {
  const value = {
    connection_id: "scratch-connection",
    run: { run_id: "run_2", job_id: "job_2", state: "running", terminal: false },
    response: { status: "accepted", result: { large: "x".repeat(200) } },
  };
  const text = modelVisibleResult([], value, 20);
  const facts = JSON.parse(text.slice(text.indexOf("Runtime facts: ") + 15));
  assert.equal(facts.run.job_id, "job_2");
  assert.equal(facts.model_view_truncated, true);
  assert.equal(runtimeFailed(value), false);
});
