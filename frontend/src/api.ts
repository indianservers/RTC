export type Row = Record<string, any>;

export interface Station {
  id: string;

  code: string;

  name: string;

  timezone: string;
}

export interface Conversation {
  feedback_policy?: {
    enabled: boolean;
    retain_text_enabled: boolean;
    retention_days: number;
  };
  reliability?: {
    confidence_state: string;
    error_category: string | null;
    failure_group: string | null;
    diagnosis: Row[];
  };
  dialogue_act?: string;
  query_plan?: {
    primary_intent: string | null;
    secondary_intents: string[];
    shared_entities: Row;
    dependencies: Row[];
  };
  answer_sections?: {
    intent: string;
    title: string;
    text: string;
    status: string;
  }[];
  clarification_choices?: { id: string; label: string; text: string }[];
  source_metadata?: Row[];
  message_id?: string;
  response_text?: string;
  selected_journey?: Row | null;
  result_set?: Row[];
  current_context?: Row;
  follow_up_suggestions?: {
    id: string;
    label: string;
    text: string;
    context_action?: Row | null;
  }[];
  data_source?: string[];
  session_id: string;

  answer: string;

  state: string;

  context: Row;

  results: Row[];

  warnings: string[];

  duration_ms: number;

  intents: string[];

  requires_clarification: boolean;

  debug: Row;

  entities: Row;

  context_changes: Row[];
}

export interface Bootstrap {
  counts: Record<string, number>;

  sources: string[];

  operators: Row[];

  categories: Row[];
}

export async function api<T = Row>(
  path: string,

  options: RequestInit = {},
): Promise<T> {
  const adminHeaders: Record<string, string> = {};
  if (path.startsWith("/admin/")) {
    const operator = sessionStorage.getItem("rtc-admin-operator");
    const source = sessionStorage.getItem("rtc-admin-source");
    if (operator) {
      adminHeaders["X-Operator-ID"] = operator;
      if (
        (!options.method || options.method === "GET") &&
        !new URLSearchParams(path.split("?")[1] || "").has("operator_id")
      )
        path +=
          (path.includes("?") ? "&" : "?") +
          "operator_id=" +
          encodeURIComponent(operator);
    }
    if (source) adminHeaders["X-Data-Source"] = source;
  }
  const controller = new AbortController();

  const timeout = setTimeout(
    () => controller.abort(),
    path.startsWith("/admin/imports/") ? 180000 : 45000,
  );

  const externalSignal = options.signal;

  const externalAbort = () => controller.abort();

  externalSignal?.addEventListener("abort", externalAbort, { once: true });

  if (externalSignal?.aborted) controller.abort();

  try {
    const response = await fetch("/api/v1" + path, {
      ...options,

      signal: controller.signal,

      headers: {
        "Content-Type": "application/json",
        ...adminHeaders,
        ...options.headers,
      },
    });

    let data;

    try {
      data = await response.json();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError")
        throw error;

      throw new Error(
        response.ok
          ? "The local backend returned an unreadable response. Please retry."
          : `Local backend request failed (${response.status}). Please retry or check the backend logs.`,
      );
    }

    if (!response.ok) {
      const reference = response.headers.get("X-Request-ID");

      const details = data.error?.details

        ?.map((e: Row) => `${e.loc?.slice(1).join(".")}: ${e.msg}`)

        .join("; ");

      throw new Error(
        (details ||
          data.error?.message ||
          "The local backend could not complete this request.") +
          (reference ? ` Reference: ${reference}` : ""),
      );
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError)
      throw new Error(
        "Cannot reach the local RTC backend. Check that it is running, then retry.",
      );

    if (
      error instanceof DOMException &&
      error.name === "AbortError" &&
      externalSignal?.aborted
    )
      throw error;

    if (error instanceof DOMException && error.name === "AbortError")
      throw new Error(
        path.startsWith("/admin/imports/")
          ? "The local data task timed out. Check change-set history before retrying."
          : "This enquiry timed out. Please narrow the search or retry.",
      );

    throw error;
  } finally {
    clearTimeout(timeout);

    externalSignal?.removeEventListener("abort", externalAbort);
  }
}

export const post = <T = Row>(path: string, body: unknown, token?: string) =>
  api<T>(path, {
    method: "POST",

    body: JSON.stringify(body),

    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

export const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",

    year: "numeric",

    month: "2-digit",

    day: "2-digit",
  }).format(new Date());

export const timeText = (value?: string | null) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        hour: "numeric",

        minute: "2-digit",

        hour12: true,

        timeZone: "Asia/Kolkata",
      }).format(new Date(value))
    : "Not available";

export const fareText = (value?: string | number | null) =>
  value === undefined || value === null
    ? "Not available"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",

        currency: "INR",

        maximumFractionDigits: 2,
      }).format(Number(value));

export const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "An unexpected error occurred.";

export function localTimestamp(
  day: string,

  clock: string,

  zone = "Asia/Kolkata",
) {
  let timestamp = Date.parse(`${day}T${clock}:00Z`);

  const target = timestamp;

  for (let i = 0; i < 2; i++) {
    const p = Object.fromEntries(
      new Intl.DateTimeFormat("en-GB", {
        timeZone: zone,

        year: "numeric",

        month: "2-digit",

        day: "2-digit",

        hour: "2-digit",

        minute: "2-digit",

        second: "2-digit",

        hourCycle: "h23",
      })

        .formatToParts(new Date(timestamp))

        .map((p) => [p.type, p.value]),
    );

    const wall = Date.parse(
      `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}Z`,
    );

    timestamp += target - wall;
  }

  return new Date(timestamp).toISOString();
}

export const dateText = (value?: string | null) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",

        month: "short",

        year: "numeric",

        timeZone: "Asia/Kolkata",
      }).format(new Date(value))
    : "Date not available";
