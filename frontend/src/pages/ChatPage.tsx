import { useEffect, useRef, useState } from "react";

import { useMutation } from "@tanstack/react-query";

import {
  ArrowUp,
  MessageSquareText,
  Plus,
  BusFront,
  Sparkles,
} from "lucide-react";

import { useWorkspace } from "../App";

import { api, post, errorText, type Conversation, type Row } from "../api";

import { StationPicker } from "../components/StationPicker";

import { BusCard } from "../components/BusCard";

import { JourneyCard } from "../components/JourneyCard";

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

      sessionStorage.removeItem("rtc-pending");
      lastOperator.current = input.operator;

      setSid(response.session_id);

      sessionStorage.setItem("rtc-session", response.session_id);

      const assistant: Message = {
        id: crypto.randomUUID(),

        role: "assistant",

        text: response.answer,

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
      } else setMessages((old) => [...old, assistant].slice(-40));

      setExpiry(
        new Date(
          Math.min(
            response.context.expires_at
              ? Date.parse(response.context.expires_at)
              : Infinity,

            Date.now() + kioskIdleMinutes() * 60 * 1000,
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

            language: "en",
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

  async function send(message: string, retry = false) {
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
      new Date(Date.now() + kioskIdleMinutes() * 60 * 1000).toISOString(),
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

    return await mutation

      .mutateAsync({
        body: {
          text: message,

          session_id: sid,

          owner_token: owner,

          language: "en",

          station_context: station?.id,

          operator: operator !== lastOperator.current ? operator : undefined,
        },

        epoch: epoch.current,

        message,

        operator,
      })

      .catch(() => {});
  }

  const latest = [...messages].reverse().find((m) => m.response)?.response;

  function renewIdle(minutes = kioskIdleMinutes()) {
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

        if ((!r.service_id && !r.journey_id) || seen.has(key)) return false;

        seen.add(key);

        return true;
      })

      .slice(0, 5);
  }

  return (
    <div className="chat-page">
      <div className="chat-heading">
        <div>
          <span className="eyebrow">YOUR LOCAL TRAVEL ASSISTANT</span>

          <h1>
            Smart enquiry <span className="title-dot" />
          </h1>

          <p>Clear answers. Real timetables. A smoother journey.</p>
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

      <label className="idle-setting">
        Kiosk idle timeout
        <select
          aria-label="Kiosk idle timeout"
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
            <small>
              {focused
                ? confirmed
                  ? "Selected service"
                  : "Service in focus"
                : "Journey context"}
            </small>

            <strong>
              {focused
                ? currentCandidate?.service_number || focused
                : latest.context.selected_itinerary
                  ? `Journey ${latest.context.selected_itinerary.journey_id.slice(0, 8)}`
                  : "No service selected"}
            </strong>

            <span>
              {latest.context.travel_date || "Date not selected"} ·{" "}
              {confirmed ? "User confirmed" : "Local enquiry context"}
            </span>
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

                  <time>
                    {new Date(message.at).toLocaleTimeString("en-IN", {
                      hour: "2-digit",

                      minute: "2-digit",
                    })}
                  </time>
                </div>

                <p>{message.text}</p>
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
                        message.response === messages.at(-1)?.response &&
                        candidateIndex >= 0;

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
        </div>
      )}

      <div className="composer-wrap">
        {messages.length > 0 && (
          <ContextualActions
            actions={suggestions}

            disabled={mutation.isPending || reset.isPending}

            onAction={(query) => void send(query)}
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
