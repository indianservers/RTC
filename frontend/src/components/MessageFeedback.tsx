import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { post, errorText, type Conversation } from "../api";

export function MessageFeedback({
  response,
  owner,
}: {
  response: Conversation;
  owner: string;
}) {
  const [retain, setRetain] = useState(false);
  const save = useMutation({
    mutationFn: (category: string) =>
      post("/conversation/feedback", {
        session_id: response.session_id,
        message_id: response.message_id,
        owner_token: owner,
        category,
        retain_question: retain,
      }),
  });
  if (!response.message_id || !response.feedback_policy?.enabled) return null;
  if (save.isSuccess)
    return (
      <small role="status" className="feedback-saved">
        Feedback saved locally. Thank you.
      </small>
    );
  return (
    <div className="message-feedback" aria-label="Reply feedback">
      <button disabled={save.isPending} onClick={() => save.mutate("HELPFUL")}>
        Helpful
      </button>
      <button
        disabled={save.isPending}
        onClick={() => save.mutate("NOT_HELPFUL")}
      >
        Not helpful
      </button>
      <select
        aria-label="Report a reply issue"
        value=""
        disabled={save.isPending}
        onChange={(e) => {
          if (e.target.value) save.mutate(e.target.value);
        }}
      >
        <option value="">Report an issue…</option>
        {[
          ["INCORRECT_INFORMATION", "Incorrect information"],
          ["WRONG_DESTINATION", "Wrong destination"],
          ["WRONG_BUS", "Wrong bus"],
          ["WRONG_FARE", "Wrong fare"],
          ["WRONG_TIMING", "Wrong timing"],
          ["WRONG_INTENT", "Wrong intent"],
          ["OTHER", "Other"],
        ].map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      {response.feedback_policy.retain_text_enabled && (
        <label>
          <input
            type="checkbox"
            checked={retain}
            onChange={(e) => setRetain(e.target.checked)}
          />
          Include my question for review
        </label>
      )}
      {save.error && <small role="alert">{errorText(save.error)}</small>}
    </div>
  );
}
