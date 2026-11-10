import { useEffect, useRef, useState } from "react";

import { useMutation } from "@tanstack/react-query";

import {
  ArrowUp,
  MessageSquareText,
  Plus,
  BusFront,
  Sparkles,
  Mic,
  MapPin,
  Clock3,
} from "lucide-react";

import { useWorkspace } from "../App";
import { useOperationsStream } from "../hooks/useOperationsStream";

import { api, post, errorText, type Conversation, type Row } from "../api";

import { StationPicker } from "../components/StationPicker";

import { BusCard } from "../components/BusCard";

import { JourneyCard } from "../components/JourneyCard";
import { MessageFeedback } from "../components/MessageFeedback";
import { ConversationDetails } from "../components/ConversationDetails";

import { followUpActions } from "../enquiryActions";

import { kioskIdleMinutes } from "../kiosk";

import { ContextualActions } from "../components/ContextualActions";

import { ConfirmDialog } from "../components/feedback";

import { Badge, Button, Notice } from "../components/ui";

interface Message {
  id: string;

  role: "user" | "assistant";

  text: string;

  at: string;

  response?: Conversation;
}

function read<T>(key: string, fallback: T): T {
  try {
    return JSON.parse(sessionStorage.getItem(key) || "null") ?? fallback;
  } catch {
    return fallback;
  }
}

export function ChatPage() {
  const { station, setStation, operator, setOperator, bootstrap } =
    useWorkspace();
  const localConnection = useOperationsStream(station?.id || "");

  const [initial] = useState(() => {
    const raw = read<unknown>("rtc-messages", []);

    const stored: Message[] = Array.isArray(raw)
      ? raw.filter(
          (m) =>
            m &&
            typeof m.id === "string" &&
            ["user", "assistant"].includes(m.role) &&
            typeof m.text === "string" &&
            typeof m.at === "string",
        )
      : [];

    const last = [...stored].reverse().find((m) => m.response)?.response;

    const deadline =
      sessionStorage.getItem("rtc-idle-expiry") || last?.context.expires_at;

    const expired =
      !!deadline &&
      (!Number.isFinite(Date.parse(deadline)) ||
        Date.parse(deadline) <= Date.now());

    if (expired) {
      sessionStorage.removeItem("rtc-session");

      sessionStorage.removeItem("rtc-messages");

      sessionStorage.removeItem("rtc-owner");

      sessionStorage.removeItem("rtc-idle-expiry");

      sessionStorage.removeItem("rtc-draft");
      sessionStorage.removeItem("rtc-pending");
      sessionStorage.removeItem("rtc-pending-request");
      sessionStorage.removeItem("rtc-state-version");

      sessionStorage.setItem("rtc-expired-notice", "true");
    }

    let token = sessionStorage.getItem("rtc-owner");

    if (!token) {
      token = crypto.randomUUID() + crypto.randomUUID();

      sessionStorage.setItem("rtc-owner", token);
    }

    return {
      messages: expired ? [] : stored,
      pending: expired ? "" : sessionStorage.getItem("rtc-pending") || "",

      sid: sessionStorage.getItem("rtc-session") || undefined,

      owner: token,

      expiry: expired ? null : deadline || null,

      expired: expired || !!sessionStorage.getItem("rtc-expired-notice"),
    };
  });

  const [messages, setMessages] = useState<Message[]>(initial.messages);
  const [sessionMode, setSessionMode] = useState<"kiosk" | "personal">(() =>
    sessionStorage.getItem("rtc-session-mode") === "personal"
      ? "personal"
      : "kiosk",
  );

  const [sid, setSid] = useState<string | undefined>(initial.sid);

  const [owner, setOwner] = useState(initial.owner);

  const [expiry, setExpiry] = useState<string | null>(initial.expiry);

  const [sessionNotice, setSessionNotice] = useState(
    initial.expired
      ? "The previous session expired. Your next enquiry starts a private conversation."
      : "",
  );

  const [confirmClear, setConfirmClear] = useState(false);

  const [text, setText] = useState(
    () => sessionStorage.getItem("rtc-draft") || "",
  );

  useEffect(() => {
    sessionStorage.setItem("rtc-draft", text);
  }, [text]);

  useEffect(() => () => requestController.current?.abort(), []);

  const [failure, setFailure] = useState(
    initial.pending
      ? "The previous enquiry was interrupted. Retry to check local records again."
      : "",
  );

  const [failedText, setFailedText] = useState(initial.pending);

  const epoch = useRef(0);

  const requestController = useRef<AbortController | null>(null);

  const end = useRef<HTMLDivElement>(null);

  const scroll = useRef<HTMLElement>(null);

  const nearBottom = useRef(true);

  const [atBottom, setAtBottom] = useState(true);

  const [expandedResults, setExpandedResults] = useState<
    Record<string, boolean>
  >({});

  const composer = useRef<HTMLTextAreaElement>(null);

  const lastOperator = useRef<string | undefined>(undefined);

  const expireAction = useRef<() => void>(() => {});

  const mutation = useMutation({
    mutationFn: async (input: {
      body: Row;

      epoch: number;

      message: string;

      operator: string;
    }) => {
      const controller = new AbortController();

      requestController.current = controller;

      return api<Conversation>("/conversation/message", {
        method: "POST",

        body: JSON.stringify(input.body),

        signal: controller.signal,
      });
    },

    onSuccess: (response, input) => {
      if (input.epoch !== epoch.current) return;
      const version = Number(
        response.context.state_version || response.context.revision || 0,
      );
      if (
        input.body.session_id === response.session_id &&
        version < Number(sessionStorage.getItem("rtc-state-version") || "0")
      )
        return;
      sessionStorage.setItem("rtc-state-version", String(version));
      sessionStorage.removeItem("rtc-pending-request");

      sessionStorage.removeItem("rtc-pending");
      lastOperator.current = input.operator;

      setSid(response.session_id);

      sessionStorage.setItem("rtc-session", response.session_id);

      const assistant: Message = {
        id: response.message_id || crypto.randomUUID(),

        role: "assistant",

        text: response.response_text || response.answer,

        at: new Date().toISOString(),

        response,
      };

      if (
        input.body.session_id &&
        input.body.session_id !== response.session_id
      ) {
        setMessages([
          {
            id: crypto.randomUUID(),

            role: "user",

            text: input.message,

            at: new Date().toISOString(),
          },

          assistant,
        ]);

        setSessionNotice(
          "The previous server session expired. This enquiry started a new conversation.",
        );
      } else
        setMessages((old) =>
          old.some((message) => message.id === assistant.id)
            ? old
            : [...old, assistant].slice(-40),
        );

      setExpiry(
        new Date(
          Math.min(
            response.context.expires_at
              ? Date.parse(response.context.expires_at)
              : Infinity,

            Date.now() +
              (response.context.session_mode === "personal"
                ? 1440
                : kioskIdleMinutes()) *
                60 *
                1000,
          ),
        ).toISOString(),
      );

      setFailure("");
    },

    onError: (error, input) => {
      if (input.epoch === epoch.current) setFailure(errorText(error));
    },
  });

  function clearLocal(message = "") {
    epoch.current += 1;

    requestController.current?.abort();

    lastOperator.current = undefined;

    setMessages([]);

    setExpandedResults({});

    setSid(undefined);

    setExpiry(null);

    setFailure("");

    setFailedText("");

    setText("");

    setOperator("");

    setSessionNotice(message);

    for (const key of [
      "rtc-session",

      "rtc-messages",

      "rtc-owner",

      "rtc-idle-expiry",

      "rtc-expired-notice",

      "rtc-draft",
      "rtc-pending",
      "rtc-pending-request",
      "rtc-state-version",
    ])
      sessionStorage.removeItem(key);

    const token = crypto.randomUUID() + crypto.randomUUID();

    sessionStorage.setItem("rtc-owner", token);

    setOwner(token);

    nearBottom.current = true;

    setAtBottom(true);

    composer.current?.focus();
  }

  const reset = useMutation({
    mutationFn: (retired: { sid?: string; owner: string }) =>
      retired.sid
        ? post("/conversation/reset", {
            session_id: retired.sid,

            owner_token: retired.owner,

            text: "reset",
          })
        : Promise.resolve({}),

    onError: () =>
      setFailure(
        "Conversation cleared on this device. The local backend reset could not be confirmed.",
      ),
  });

  function restart(expired = false) {
    const retired = { sid, owner };

    clearLocal(
      expired
        ? "Your session expired. Previous passenger information has been cleared."
        : "",
    );

    if (expired) sessionStorage.setItem("rtc-expired-notice", "true");

    reset.mutate(retired);
  }

  expireAction.current = () => restart(true);

  useEffect(() => {
    if (!expiry) return;

    sessionStorage.setItem("rtc-idle-expiry", expiry);

    const timer = setTimeout(
      () => expireAction.current(),

      Math.max(0, Date.parse(expiry) - Date.now()),
    );

    return () => clearTimeout(timer);
  }, [expiry]);

  useEffect(() => {
    sessionStorage.setItem("rtc-messages", JSON.stringify(messages));

    if (nearBottom.current && scroll.current)
      scroll.current.scrollTo({
        top: messages.length ? scroll.current.scrollHeight : 0,

        behavior: "auto",
      });
  }, [messages]);

  async function send(
    message: string,
    retry = false,
    contextAction?: Row,
    modeOverride?: "kiosk" | "personal",
  ) {
    if (!message.trim() || mutation.isPending || reset.isPending) return;

    if (!station && !sid) {
      setFailure("Choose your current bus stand first.");

      return;
    }

    setFailure("");

    setSessionNotice("");

    sessionStorage.removeItem("rtc-expired-notice");

    setFailedText(message);
    sessionStorage.setItem("rtc-pending", message);

    nearBottom.current = true;

    setAtBottom(true);

    setExpiry(
      new Date(
        Date.now() +
          (sessionMode === "personal" ? 1440 : kioskIdleMinutes()) * 60 * 1000,
      ).toISOString(),
    );

    if (!retry)
      setMessages((old) => [
        ...old,

        {
          id: crypto.randomUUID(),

          role: "user",

          text: message,

          at: new Date().toISOString(),
        },
      ]);

    setText("");

    const pending = read<Row | null>("rtc-pending-request", null);
    const body =
      retry && pending?.text === message
        ? pending
        : {
            text: message,
            session_id: sid,
            owner_token: owner,
            station_context: station?.id,
            operator: operator !== lastOperator.current ? operator : undefined,
            client_message_id: crypto.randomUUID(),
            expected_state_version: sid
              ? Number(
                  sessionStorage.getItem("rtc-state-version") ||
                    latest?.context.state_version ||
                    latest?.context.revision ||
                    "0",
                )
              : 0,
            session_mode: modeOverride || sessionMode,
            ...(contextAction ? { context_action: contextAction } : {}),
          };
    sessionStorage.setItem("rtc-pending-request", JSON.stringify(body));
    return await mutation

      .mutateAsync({
        body,

        epoch: epoch.current,

        message,

        operator,
      })

      .catch(() => {});
  }

  const latest = [...messages].reverse().find((m) => m.response)?.response;
  const restore = useMutation({
    mutationFn: () =>
      post("/conversation/state", { session_id: sid, owner_token: owner }),
    onSuccess: (saved) => {
      const snapshot: Conversation = {
        ...(latest || {}),
        session_id: saved.session_id,
        message_id: saved.last_message_id,
        context: saved.current_context,
        current_context: saved.current_context,
        answer:
          saved.current_context.last_answer || "Your saved context is ready.",
        state: "ANSWERING",
        results: [],
        warnings: [],
        intents: saved.current_context.last_intents || [],
        requires_clarification: false,
        duration_ms: 0,
        debug: {},
        entities: {},
        context_changes: [],
        selected_journey: saved.selected_journey,
        result_set: saved.result_set,
        data_source: saved.data_source,
        follow_up_suggestions: [],
      };
      const restored: Message[] = saved.history.map(
        (message: Row, index: number) => ({
          id:
            index === saved.history.length - 1 && message.role === "assistant"
              ? saved.last_message_id || message.id
              : message.id,
          role: message.role,
          text: message.text,
          at: "",
          ...(index === saved.history.length - 1 && message.role === "assistant"
            ? { response: snapshot }
            : {}),
        }),
      );
      setMessages(restored);
      setFailure("");
      setExpiry(saved.current_context.expires_at);
      setSessionMode(
        saved.current_context.session_mode === "personal"
          ? "personal"
          : "kiosk",
      );
      sessionStorage.setItem("rtc-state-version", String(saved.state_version));
      sessionStorage.removeItem("rtc-pending-request");
      sessionStorage.removeItem("rtc-pending");
      setSessionNotice(
        "Saved messages and context restored. New questions will recheck current database records.",
      );
    },
  });

  function renewIdle(
    minutes = sessionMode === "personal" ? 1440 : kioskIdleMinutes(),
  ) {
    if (!messages.length) return;
    setExpiry(
      new Date(
        Math.min(
          Date.now() + minutes * 60000,
          latest?.context.expires_at
            ? Date.parse(latest.context.expires_at)
            : Infinity,
        ),
      ).toISOString(),
    );
  }
  const focused = latest?.context.service_id;

  const confirmed = latest?.context.selection_status === "USER_CONFIRMED";

  const currentCandidate = latest?.context.candidates?.find(
    (r: Row) => r.service_id === focused,
  );

  const suggestions = followUpActions(latest);

  function renderedRows(response: Conversation) {
    const seen = new Set<string>();

    return response.results

      .flatMap((r) => r.results || [])

      .filter((r: Row) => {
        const key =
          r.journey_id || `${r.service_id}-${r.service_date}-${r.departure}`;

        if (
          (r.journey_id
            ? !Array.isArray(r.legs)
            : !r.service_id || !r.departure) ||
          seen.has(key)
        )
          return false;

        seen.add(key);

        return true;
      })

      .slice(0, 5);
  }

  return (
    <div className={`chat-page${messages.length ? " has-conversation" : ""}`}>
      <header className="enquiry-masthead">
        <a href="/" className="enquiry-brand">
          <BusFront size={38} />
          <span>
            RTC <b>Smart Enquiry</b>
            <small>PASSENGER INFORMATION SYSTEM</small>
          </span>
        </a>
        <span className="enquiry-live">
          <i /> Local bus information
          <small>For every passenger. Every journey.</small>
        </span>
      </header>
      <div className="chat-heading">
        <div>
          <span className="eyebrow">YOUR LOCAL TRAVEL ASSISTANT</span>

          <h1>
            RTC Smart <em>Enquiry</em>
          </h1>

          <p>Your AI-powered local bus enquiry assistant</p>
          <small role="status">
            Local data: {localConnection}. Ask again to refresh an earlier
            answer.
          </small>
        </div>

        <Button
          variant="secondary"

          disabled={reset.isPending}

          onClick={() => restart()}
        >
          <Plus size={16} />
          New conversation
        </Button>
      </div>

      <section className="assistant-stage" aria-label="Your RTC assistant">
        <div className="assistant-intro">
          <div className="rtc-robot" aria-hidden="true">
            <div className="robot-antenna" />
            <div className="robot-head">
              <div className="robot-face">
                <span>^</span>
                <span>^</span>
                <i />
              </div>
            </div>
            <div className="robot-body">
              <b>RTC</b>
            </div>
          </div>
          <div className="assistant-greeting">
            <span className="eyebrow">MEET YOUR TRAVEL COMPANION</span>
            <h2>
              Hello! I’m your
              <br />
              RTC Smart Assistant
            </h2>
            <p>
              Ask me about buses, timings, fares, platforms and routes. How can
              I help you today?
            </p>
            <span className="assistant-ready">
              <i /> Ready to help you
            </span>
          </div>
        </div>
        <div className="voice-panel">
          <div className="sound-wave" aria-hidden="true">
            {Array.from({ length: 31 }, (_, i) => (
              <i key={i} style={{ height: `${8 + ((i * 17 + 11) % 37)}px` }} />
            ))}
          </div>
          <p>Your next journey starts with a question</p>
          <button
            type="button"
            className="voice-start"
            aria-label="Start an enquiry"
            onClick={() => {
              composer.current?.focus();
              composer.current?.scrollIntoView({
                behavior: "smooth",
                block: "center",
              });
            }}
          >
            <Mic size={32} />
          </button>
          <strong>Let’s find your next bus</strong>
          <small>Type your question below to get started</small>
        </div>
      </section>
      <div className="enquiry-workspace-label">
        <span>
          <MessageSquareText size={17} /> Passenger enquiry
        </span>
        <small>Timings · Fares · Routes · Platforms</small>
      </div>
      <div className="privacy-controls">
        <label className="idle-setting">
          Privacy mode
          <select
            aria-label="Conversation privacy mode"
            value={sessionMode}
            disabled={mutation.isPending}
            onChange={async (event) => {
              const mode = event.target.value as "kiosk" | "personal";
              if (
                sid &&
                !(await send(
                  "Keep this conversation context",
                  false,
                  undefined,
                  mode,
                ))
              )
                return;
              setSessionMode(mode);
              sessionStorage.setItem("rtc-session-mode", mode);
            }}
          >
            <option value="kiosk">Shared kiosk · idle expiry</option>
            <option value="personal">Personal browser · up to 24 hours</option>
          </select>
        </label>
        <label className="idle-setting">
          Kiosk idle timeout
          <select
            aria-label="Kiosk idle timeout"
            disabled={sessionMode === "personal"}
            defaultValue={kioskIdleMinutes()}
            onChange={(e) => {
              sessionStorage.setItem("rtc-kiosk-idle", e.target.value);

              renewIdle(Number(e.target.value));
            }}
          >
            {[2, 5, 10, 15].map((minutes) => (
              <option key={minutes} value={minutes}>
                {minutes} minutes
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="context-bar">
        <StationPicker
          label="Your current bus stand"

          disabled={mutation.isPending || reset.isPending}

          value={station}

          onChange={async (s) => {
            if (sid && s && s.id !== station?.id) {
              const previous = station;
              const updated = await send(`from ${s.code}`);
              if (updated?.context.origin === s.id) setStation(s);
              else if (previous) setStation({ ...previous });
            } else setStation(s);
          }}
        />

        <label className="field">
          RTC operator
          <select
            value={operator}

            disabled={mutation.isPending || reset.isPending}

            onChange={(e) => setOperator(e.target.value)}
          >
            <option value="">All local operators</option>

            {bootstrap?.operators.map((op) => (
              <option key={op.id} value={op.code}>
                {op.name}
              </option>
            ))}
          </select>
        </label>

        <div className="context-note">
          <BusFront size={18} />

          <span>
            Ask in English
            <br />
            <small>Timings, routes, fares & more</small>
          </span>
        </div>
      </div>

      {sessionNotice && <Notice>{sessionNotice}</Notice>}
      {latest?.state === "NO_RESULTS" && (
        <Notice>
          Searched from{" "}
          {latest.results[0]?.matched_stations?.origin?.candidates
            ?.map((c: Row) => c.name)
            .join(", ") ||
            station?.name ||
            "your boarding station"}{" "}
          to{" "}
          {latest.results[0]?.matched_stations?.destination?.candidates
            ?.map((c: Row) => c.name)
            .join(", ") || "your selected destination"}{" "}
          on {latest.context.travel_date}.
          {Object.entries(latest.context.filters || {})
            .filter(
              ([key, value]) =>
                ["ac", "sleeper", "max_fare", "accessible"].includes(key) &&
                value != null,
            )
            .map(([key, value]) => (
              <span key={key}>
                {" "}
                {key === "ac"
                  ? value
                    ? "AC required."
                    : "Non-AC required."
                  : key === "sleeper"
                    ? value
                      ? "Sleeper required."
                      : "Seater required."
                    : key === "max_fare"
                      ? `Fare ceiling: ${value}.`
                      : value
                        ? "Accessible service required."
                        : ""}
              </span>
            ))}
          <span>
            {" "}
            Restrictions stay in place until you choose to change them.
          </span>
        </Notice>
      )}

      {latest && (
        <div className="selected-context" aria-label="Active enquiry context">
          <div>
            <strong>
              {latest.context.origin_name ||
                station?.name ||
                "Choose boarding station"}{" "}
              → {latest.context.destination_name || "Choose destination"}
            </strong>
            <small>
              {focused
                ? confirmed
                  ? "Selected service"
                  : "Service in focus"
                : latest.selected_journey
                  ? "Selected journey"
                  : "Journey context"}
            </small>

            <strong>
              {latest.context.selection_summary
                ? `${latest.context.selection_summary.categories.join(" → ")} · ${latest.context.selection_summary.service_numbers.join(" → ")}`
                : focused
                  ? currentCandidate?.service_number || "Service in focus"
                  : latest.context.selected_itinerary
                    ? "Selected connecting journey"
                    : "No service selected"}
            </strong>

            <span>
              {latest.context.travel_date || "Date not selected"}{" "}
              {latest.context.time_window || ""} ·{" "}
              {confirmed ? "User confirmed" : "Local enquiry context"}
            </span>
            <div className="context-chips">
              {Object.entries(latest.context.filters || {})
                .filter(
                  ([key, value]) =>
                    ["ac", "sleeper", "category", "max_fare"].includes(key) &&
                    value != null,
                )
                .map(([key, value]) => (
                  <button
                    key={key}
                    type="button"
                    disabled={mutation.isPending}
                    aria-label={`Remove ${key.replaceAll("_", " ")} filter`}
                    onClick={() =>
                      void send("Next bus", false, {
                        op: "CLEAR_SLOT",
                        slot: key,
                      })
                    }
                  >
                    {key === "ac"
                      ? value
                        ? "AC only"
                        : "Non-AC"
                      : key === "sleeper"
                        ? value
                          ? "Sleeper"
                          : "Seater"
                        : key === "max_fare"
                          ? `Up to INR ${value}`
                          : bootstrap?.categories.find((c) => c.id === value)
                              ?.name || "Category selected"}{" "}
                    ×
                  </button>
                ))}
            </div>
          </div>

          <Button
            variant="ghost"

            disabled={mutation.isPending || reset.isPending}

            onClick={() => setConfirmClear(true)}
          >
            Clear context
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={confirmClear}

        onOpenChange={setConfirmClear}

        title="Clear this conversation?"

        description="Messages, selected services and preferences will be removed from this device, and the backend session will be reset."

        onConfirm={() => restart()}
      />

      <section
        ref={scroll}

        onScroll={(event) => {
          const box = event.currentTarget;

          const near = box.scrollHeight - box.scrollTop - box.clientHeight < 80;

          nearBottom.current = near;

          setAtBottom(near);
        }}

        className="conversation"

        aria-label="Conversation"

        aria-live="polite"
      >
        {!messages.length && (
          <div className="welcome">
            <div className="welcome-mark">
              <MessageSquareText size={32} />
            </div>

            <span className="eyebrow">LET’S GET YOU THERE</span>

            <h2>Where would you like to go?</h2>

            <p>
              Ask a question just as you would at the enquiry counter.
              <br />
              I’ll check the local RTC records for you.
            </p>

            <div className="starter-grid">
              {[
                ["Next bus to Nellore?", "Find your next departure"],

                ["How can I reach Tirupati?", "Explore connecting journeys"],

                ["First bus tomorrow to Guntur?", "Plan an early start"],

                ["Is there an AC bus to Hyderabad?", "Travel your way"],
              ].map(([prompt, caption]) => (
                <button
                  key={prompt}

                  onClick={() => void send(prompt)}

                  disabled={mutation.isPending}
                >
                  <span>
                    <BusFront size={17} />

                    <strong>{prompt}</strong>

                    <ArrowUp size={15} />
                  </span>

                  <small>{caption}</small>
                </button>
              ))}
            </div>

            <p className="privacy-note">
              Answers use local records. Missing information stays unconfirmed.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div className={`message ${message.role}`} key={message.id}>
            {message.role === "assistant" && (
              <span className="avatar">
                <BusFront size={17} />
              </span>
            )}

            <div className="message-content">
              <div className="bubble">
                <div className="message-label">
                  {message.role === "assistant" ? "RTC Smart Enquiry" : "You"}
                  {message.response?.data_source?.some((source) =>
                    ["DEMO", "SYNTHETIC"].includes(source),
                  ) && <Badge tone="warning">DEMO</Badge>}

                  <time>
                    {message.at
                      ? new Date(message.at).toLocaleTimeString("en-IN", {
                          hour: "2-digit",

                          minute: "2-digit",
                        })
                      : "Saved message"}
                  </time>
                </div>

                <p>{message.text}</p>
                {message.response && (
                  <>
                    <ConversationDetails response={message.response} />
                    <MessageFeedback
                      response={message.response}
                      owner={owner}
                    />
                  </>
                )}
                {message.response?.requires_clarification &&
                  !!message.response.clarification_choices?.length && (
                    <ContextualActions
                      actions={message.response.clarification_choices.map(
                        (choice) => ({
                          label: choice.label,
                          query: choice.text,
                        }),
                      )}
                      onAction={(query) => void send(query)}
                      disabled={
                        mutation.isPending || message.response !== latest
                      }
                    />
                  )}
              </div>

              {message.response &&
                message.response !== latest &&
                !expandedResults[message.id] &&
                renderedRows(message.response).length > 0 && (
                  <Button
                    variant="ghost"

                    onClick={() =>
                      setExpandedResults((old) => ({
                        ...old,

                        [message.id]: true,
                      }))
                    }
                  >
                    Show previous result cards (
                    {renderedRows(message.response).length})
                  </Button>
                )}

              {message.response &&
                (message.response === latest ||
                  expandedResults[message.id]) && (
                  <div className="rich-results">
                    {message.response === latest &&
                      message.response.requires_clarification &&
                      message.response.context.station_clarification && (
                        <ContextualActions
                          actions={message.response.context.station_clarification.choices.map(
                            (choice: Row) => ({
                              label: `${choice.name} (${choice.code})`,
                              query: choice.code,
                            }),
                          )}
                          onAction={(query) => void send(query)}
                          disabled={mutation.isPending}
                        />
                      )}

                    {renderedRows(message.response).map((row: Row) => {
                      const candidateIndex = (
                        message.response!.context.candidates || []
                      ).findIndex((c: Row) =>
                        row.journey_id
                          ? c.journey_id === row.journey_id
                          : c.service_id === row.service_id &&
                            c.departure === row.departure,
                      );

                      const selectable =
                        message.response?.context.result_revision ===
                          latest?.context.result_revision &&
                        candidateIndex >= 0 &&
                        latest?.context.candidates?.[candidateIndex]
                          ?.result_id ===
                          message.response?.context.candidates?.[candidateIndex]
                            ?.result_id;

                      return row.journey_id ? (
                        <JourneyCard
                          key={row.journey_id}

                          journey={row}

                          index={candidateIndex + 1}

                          onSelect={
                            selectable ? (n) => void send(String(n)) : undefined
                          }
                        />
                      ) : (
                        <BusCard
                          key={`${row.service_id}-${row.departure}`}

                          row={row}

                          liveRefresh={message.response === latest}

                          index={candidateIndex + 1}

                          onSelect={
                            selectable ? (n) => void send(String(n)) : undefined
                          }

                          onAsk={
                            selectable
                              ? async (n) => {
                                  const selected = await send(String(n));

                                  if (selected) {
                                    composer.current?.focus();

                                    setText("Which platform?");
                                  }
                                }
                              : undefined
                          }

                          onCompare={
                            selectable
                              ? () => void send("Fare comparison")
                              : undefined
                          }
                        />
                      );
                    })}

                    {message.response.requires_clarification &&
                      message.response === latest &&
                      ["AWAITING_DESTINATION", "AWAITING_ORIGIN"].includes(
                        message.response.state,
                      ) && (
                        <StationPicker
                          label={
                            message.response.state === "AWAITING_DESTINATION"
                              ? "Choose destination for this enquiry"
                              : "Choose boarding station for this enquiry"
                          }

                          disabled={mutation.isPending}

                          onChange={(station) => {
                            if (station)
                              void send(
                                message.response!.state === "AWAITING_ORIGIN"
                                  ? `from ${station.code}`
                                  : station.code,
                              );
                          }}
                        />
                      )}

                    {message.response === latest &&
                      message.response.requires_clarification && (
                        <ContextualActions
                          actions={message.response.results.flatMap(
                            (result: Row) =>
                              Object.values(result.matched_stations || {})
                                .flatMap((match) =>
                                  (match as Row).status ===
                                  "DISAMBIGUATION_REQUIRED"
                                    ? (match as Row).candidates || []
                                    : [],
                                )
                                .map((choice: Row) => ({
                                  label: choice.name || choice.code,
                                  query: choice.code || choice.id,
                                })),
                          )}
                          onAction={(query) => void send(query)}
                          disabled={mutation.isPending}
                        />
                      )}

                    {message.response.requires_clarification && (
                      <Badge tone="blue">
                        Your reply will continue this enquiry
                      </Badge>
                    )}
                  </div>
                )}
            </div>
          </div>
        ))}

        {mutation.isPending && (
          <div className="typing" role="status">
            <span className="avatar">
              <BusFront size={17} />
            </span>
            <span className="loading-dot" />
            Checking local records…
          </div>
        )}

        <div ref={end} />
      </section>

      {messages.length > 0 && !atBottom && (
        <Button
          variant="secondary"

          className="jump-latest"

          onClick={() => {
            nearBottom.current = true;

            setAtBottom(true);

            scroll.current?.scrollTo({
              top: scroll.current.scrollHeight,

              behavior: "auto",
            });
          }}
        >
          Jump to latest reply
        </Button>
      )}

      {failure && (
        <div id="chat-error">
          <Notice error>
            {failure}

            {failedText && (
              <Button
                variant="ghost"

                onClick={() => void send(failedText, true)}

                disabled={mutation.isPending}
              >
                Retry enquiry
              </Button>
            )}
          </Notice>
          {sid && (
            <Button
              variant="secondary"
              onClick={() => restore.mutate()}
              disabled={restore.isPending}
            >
              Restore saved context
            </Button>
          )}
          {restore.error && (
            <Notice error>
              {errorText(restore.error)} Start a new conversation if this
              session expired.
            </Notice>
          )}
        </div>
      )}

      <div className="enquiry-capabilities">
        <span>
          <Clock3 size={15} /> Departure timings
        </span>
        <span>
          <MapPin size={15} /> Routes & platforms
        </span>
        <span>
          <BusFront size={15} /> Bus services & fares
        </span>
      </div>
      <div className="composer-wrap">
        {messages.length > 0 && (
          <ContextualActions
            actions={suggestions}

            disabled={mutation.isPending || reset.isPending}

            onAction={(query) => {
              const suggestion = [...messages]
                .reverse()
                .find((m) => m.response)
                ?.response?.follow_up_suggestions?.find(
                  (item) => item.text === query,
                );
              void send(query, false, suggestion?.context_action ?? undefined);
            }}
          />
        )}

        <form
          className="composer"

          onSubmit={(e) => {
            e.preventDefault();

            void send(text);
          }}
        >
          <textarea
            ref={composer}

            aria-label="Your enquiry"

            aria-invalid={!!failure}

            aria-describedby={failure ? "chat-error" : undefined}

            placeholder={
              latest?.requires_clarification
                ? "Reply to the clarification above…"
                : "Ask about a bus, route, fare or journey…"
            }

            rows={1}

            maxLength={2000}

            value={text}

            disabled={mutation.isPending || reset.isPending}

            onChange={(e) => {
              setText(e.target.value);
              renewIdle();
            }}

            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();

                void send(text);
              }
            }}
          />

          <Button
            type="submit"

            aria-label="Send enquiry"

            disabled={!text.trim() || mutation.isPending || reset.isPending}
          >
            <ArrowUp size={20} />
          </Button>
        </form>

        <div className="composer-caption">
          <span>
            <Sparkles size={12} />{" "}
            {sid
              ? `Private session · clears after ${kioskIdleMinutes()} min without activity`
              : "Grounded in your local RTC database"}
          </span>

          <span>Enter to send · Shift + Enter for a new line</span>
        </div>
      </div>
    </div>
  );
}
