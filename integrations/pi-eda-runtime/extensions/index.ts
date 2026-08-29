import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";

import { RuntimeClient } from "../lib/runtime-client.mjs";

const PI_AGENT_VERSION = "0.73.1";
const JsonObject = Type.Record(Type.String(), Type.Unknown());
const TargetFields = {
  target: Type.Optional(JsonObject),
  context: Type.Optional(Type.String()),
  connection_id: Type.Optional(Type.String()),
  eda: Type.Optional(Type.String()),
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
          content: (result.content ?? [{ type: "text", text: "EDA Runtime returned no summary" }])
            .filter((item) => item.type === "text")
            .map((item) => ({ type: "text" as const, text: item.text ?? "" })),
          details: { runtime: value, elapsedMs },
          isError: Boolean(result.isError),
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
    "eda_submit",
    "eda.submit",
    "Submit EDA Operation",
    "Submit one typed operation. Mutations require a stable idempotency key and are never blindly replayed.",
    Type.Object({
      purpose: Type.String({ minLength: 3, maxLength: 240 }),
      operation: Type.String(),
      payload: JsonObject,
      ...TargetFields,
      expected_effect: Type.Optional(Type.String()),
      idempotency_key: Type.Optional(Type.String()),
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
