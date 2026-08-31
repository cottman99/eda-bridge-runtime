import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

import { modelVisibleResult, runtimeFailed } from "../lib/model-visible-result.mjs";
import { RuntimeClient } from "../lib/runtime-client.mjs";

const PI_AGENT_VERSION = "0.84.4";
const MAX_WAIT_MS = 300_000;
const JsonObject = Type.Record(Type.String(), Type.Unknown());
const ResultView = Type.Object({
  fields: Type.Array(Type.Object({
    name: Type.String({ minLength: 1, maxLength: 64 }),
    pointer: Type.String({
      maxLength: 256,
      description: "Verified RFC 6901 path inside Bridge response.result; never infer it from final-answer keys.",
    }),
    mode: Type.Optional(Type.Union([
      Type.Literal("value"),
      Type.Literal("count"),
      Type.Literal("exists"),
    ])),
  }, { additionalProperties: false }), { minItems: 1, maxItems: 16 }),
}, {
  additionalProperties: false,
  description: "Advanced response-size optimization. Omit unless every pointer was verified from an earlier successful full response for the same operation and version; guessed value/count pointers fail the otherwise successful read.",
});
const TargetFields = {
  target: Type.Optional(JsonObject),
  context: Type.Optional(Type.String()),
  connection_id: Type.Optional(Type.String({
    description: "Exact registered connection identifier, for example ads-display4. If the request names a connection, put it here rather than in eda.",
  })),
  eda: Type.Optional(Type.String({
    description: "EDA vendor type such as keysight-ads or ansys-electronics-desktop; use only when exactly one registered connection has that type.",
  })),
};

type RuntimeResult = {
  content?: Array<{ type: string; text?: string }>;
  structuredContent?: Record<string, unknown>;
  isError?: boolean;
};

export default function piEdaRuntime(pi: ExtensionAPI) {
  const client = new RuntimeClient({
    clientInfo: { name: "pi-agent", version: PI_AGENT_VERSION },
  });
  let lastStatus = "idle; no Runtime call has been made";

  function actor(ctx: ExtensionContext, toolCallId: string) {
    const metadata: Record<string, string> = {
      agent_family: "pi-agent",
      agent_version: PI_AGENT_VERSION,
      reasoning: pi.getThinkingLevel(),
      skill: "eda-runtime-control",
      session_id: ctx.sessionManager.getSessionId(),
      tool_call_id: toolCallId,
      permission_mode: "runtime-only-profile",
    };
    if (ctx.model?.provider && ctx.model.provider !== "unknown") {
      metadata.provider = ctx.model.provider;
    }
    if (ctx.model?.id && ctx.model.id !== "unknown") metadata.model = ctx.model.id;
    return metadata;
  }

  function register(
    name: string,
    runtimeName: string,
    label: string,
    description: string,
    parameters: ReturnType<typeof Type.Object>,
  ) {
    pi.registerTool({
      name,
      label,
      description,
      promptSnippet: `${label} through the stable EDA Bridge Runtime`,
      promptGuidelines: [
        `Use ${name} only for its named EDA Runtime action; include a concise purpose and never bypass Runtime with shell commands.`,
      ],
      parameters,
      executionMode: "sequential",
      async execute(toolCallId, params, signal, onUpdate, ctx) {
        if (signal?.aborted) throw new Error("EDA Runtime call was cancelled before dispatch");
        const started = performance.now();
        onUpdate?.({ content: [{ type: "text", text: `Calling ${runtimeName}…` }] });
        const result = (await client.callTool(runtimeName, params, actor(ctx, toolCallId))) as RuntimeResult;
        const elapsedMs = Math.round((performance.now() - started) * 10) / 10;
        const value = result.structuredContent ?? {};
        const run = typeof value.run === "object" && value.run ? value.run as Record<string, unknown> : {};
        lastStatus = [
          runtimeName,
          String(value.connection_id ?? "no connection"),
          String(run.state ?? value.status ?? "unknown"),
          `${elapsedMs} ms`,
        ].join(" | ");
        return {
          content: [{
            type: "text" as const,
            text: modelVisibleResult(result.content, value),
          }],
          details: { runtime: value, elapsedMs },
          isError: runtimeFailed(value, Boolean(result.isError)),
        };
      },
    });
  }

  register(
    "eda_context_resolve",
    "eda.context.resolve",
    "Resolve EDA Context",
    "Validate a captured EDA context and select its registered connection without contacting EDA.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      context: Type.String(),
      connection_id: Type.Optional(Type.String()),
    }),
  );
  register(
    "eda_connections_list",
    "eda.connections.list",
    "List EDA Connections",
    "List configured EDA connection identifiers without opening them.",
    Type.Object({ purpose: Type.String({ minLength: 3, maxLength: 240 }) }),
  );
  register(
    "eda_connection_reset",
    "eda.connection.reset",
    "Reset EDA Transport",
    "Close one Runtime-owned transport; this does not close or modify EDA.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      connection_id: Type.String(),
    }),
  );
  register(
    "eda_capabilities",
    "eda.capabilities",
    "Discover EDA Capabilities",
    "Read typed operations only when Context and the selected Skill do not already establish them.",
    Type.Object({ purpose: Type.String({ minLength: 3, maxLength: 240 }), ...TargetFields }),
  );
  register(
    "eda_read",
    "eda.read",
    "Run Read-Only EDA Operation",
    "Run a non-mutating operation; Runtime verifies missing safety metadata and can wait to terminal in this call.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      operation: Type.String({
        description: "Exact operation already advertised as non-mutating by the selected Bridge.",
      }),
      payload: Type.Record(Type.String(), Type.Unknown()),
      result_view: Type.Optional(ResultView),
      wait: Type.Optional(Type.Object({
        timeout_ms: Type.Optional(Type.Integer({ minimum: 1000, maximum: MAX_WAIT_MS })),
        poll_interval_ms: Type.Optional(Type.Integer({ minimum: 100, maximum: 5000 })),
      }, { additionalProperties: false })),
      ...TargetFields,
    }),
  );
  register(
    "eda_submit",
    "eda.submit",
    "Submit EDA Operation",
    "Submit one typed operation; add wait to return a durable terminal result in this call.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      operation: Type.String({
        description: "Exact registered operation name from the selected vendor capability; never guess or translate it.",
      }),
      payload: Type.Record(Type.String(), Type.Unknown(), {
        description: "Payload conforming exactly to that operation's capability schema.",
      }),
      ...TargetFields,
      expected_effect: Type.Optional(Type.String()),
      idempotency_key: Type.Optional(Type.String()),
      wait: Type.Optional(Type.Object({
        timeout_ms: Type.Optional(Type.Integer({ minimum: 1000, maximum: MAX_WAIT_MS })),
        poll_interval_ms: Type.Optional(Type.Integer({ minimum: 100, maximum: 5000 })),
      }, { additionalProperties: false })),
    }),
  );
  register(
    "eda_run_plan",
    "eda.run_plan",
    "Run Validated EDA Plan",
    "Execute 2..16 already-decided typed operations on one connection after complete prevalidation.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      steps: Type.Array(Type.Object({
        step_id: Type.String({ minLength: 1, maxLength: 64 }),
        purpose: Type.String({ minLength: 3, maxLength: 240 }),
        operation: Type.String(),
        payload: Type.Record(Type.String(), Type.Unknown(), {
          description: "Vendor Bridge operation payload only. Do not place Runtime step controls such as wait, idempotency_key, purpose, or result_view inside payload.",
        }),
        target: Type.Optional(JsonObject),
        expected_effect: Type.Optional(Type.String()),
        idempotency_key: Type.Optional(Type.String()),
        wait: Type.Optional(Type.Object({
          timeout_ms: Type.Optional(Type.Integer({ minimum: 1000, maximum: MAX_WAIT_MS })),
          poll_interval_ms: Type.Optional(Type.Integer({ minimum: 100, maximum: 5000 })),
        }, {
          description: "Runtime durable-job wait policy for this plan step. This is a sibling of payload and must never be nested inside payload.",
        })),
        result_view: Type.Optional(ResultView),
      }, { additionalProperties: false }), { minItems: 2, maxItems: 16 }),
      ...TargetFields,
    }),
  );
  register(
    "eda_run_get",
    "eda.run.get",
    "Get Compact EDA Run Receipt",
    "Read one prior execution receipt by run_id without returning its stored raw result or replaying work.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      run_id: Type.String({ minLength: 5, maxLength: 160 }),
      context: Type.Optional(Type.String()),
      connection_id: Type.Optional(Type.String()),
      eda: Type.Optional(Type.String()),
    }),
  );
  register(
    "eda_job_status",
    "eda.job.status",
    "Get EDA Job Status",
    "Read one durable job after reconnecting without restarting it.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      job_id: Type.String(),
      connection_id: Type.Optional(Type.String()),
      eda: Type.Optional(Type.String()),
    }),
  );
  register(
    "eda_job_wait",
    "eda.job.wait",
    "Wait for EDA Job",
    "Wait for one durable job to reach terminal state without replaying it or spending one model turn per poll.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      job_id: Type.String(),
      connection_id: Type.Optional(Type.String()),
      eda: Type.Optional(Type.String()),
      timeout_ms: Type.Optional(Type.Integer({ minimum: 1000, maximum: MAX_WAIT_MS })),
      poll_interval_ms: Type.Optional(Type.Integer({ minimum: 100, maximum: 5000 })),
      result_view: Type.Optional(ResultView),
    }),
  );
  register(
    "eda_job_events",
    "eda.job.events",
    "Read EDA Job Events",
    "Read incremental durable-job events after a cursor without replaying work.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      job_id: Type.String(),
      after_cursor: Type.Optional(Type.Integer({ minimum: 0 })),
      connection_id: Type.Optional(Type.String()),
      eda: Type.Optional(Type.String()),
    }),
  );

  pi.registerCommand("eda-runtime-status", {
    description: "Show the latest Runtime call; add 'refresh' to verify the connection registry",
    handler: async (args, ctx) => {
      if (args.trim() === "refresh") {
        const started = performance.now();
        const result = (await client.callTool(
          "eda.connections.list",
          { purpose: "Refresh the Pi EDA Runtime status" },
          actor(ctx, "command:eda-runtime-status"),
        )) as RuntimeResult;
        const elapsedMs = Math.round((performance.now() - started) * 10) / 10;
        const count = Array.isArray(result.structuredContent?.connections)
          ? result.structuredContent.connections.length
          : 0;
        const toolCount = pi.getAllTools().filter((tool) => tool.name.startsWith("eda_")).length;
        lastStatus = `eda.connections.list | ${toolCount} tools | ${count} configured | ready | ${elapsedMs} ms`;
      }
      ctx.ui.notify(lastStatus, "info");
    },
  });
  pi.on("session_shutdown", async () => client.close());
}
