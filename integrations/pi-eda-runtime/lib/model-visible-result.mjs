const DEFAULT_MAX_CHARS = 64_000;

function runtimeState(value) {
  const run = value && typeof value.run === "object" ? value.run : {};
  const response = value && typeof value.response === "object" ? value.response : {};
  return String(run.state ?? response.status ?? value?.status ?? "unknown");
}

function compactFallback(value) {
  const run = value && typeof value.run === "object" ? value.run : {};
  const response = value && typeof value.response === "object" ? value.response : {};
  const error = response && typeof response.error === "object" ? response.error : null;
  return {
    connection_id: value?.connection_id,
    status: value?.status,
    run: {
      run_id: run.run_id,
      request_id: run.request_id,
      job_id: run.job_id,
      state: run.state,
      terminal: run.terminal,
    },
    response: {
      status: response.status,
      error,
      result_keys:
        response.result && typeof response.result === "object"
          ? Object.keys(response.result)
          : [],
    },
    model_view_truncated: true,
  };
}

export function modelVisibleResult(content, value, maxChars = DEFAULT_MAX_CHARS) {
  const summary = (content ?? [])
    .filter((item) => item?.type === "text")
    .map((item) => item.text ?? "")
    .filter(Boolean)
    .join("\n");
  const serialized = JSON.stringify(value ?? {});
  const facts = serialized.length <= maxChars
    ? serialized
    : JSON.stringify(compactFallback(value));
  return `${summary || "EDA Runtime returned no summary"}\nRuntime facts: ${facts}`;
}

export function runtimeFailed(value, transportError = false) {
  return Boolean(transportError) || runtimeState(value) === "failed";
}
