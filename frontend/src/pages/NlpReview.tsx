import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, post, errorText, type Row } from "../api";
import { Button, Notice } from "../components/ui";

export function NlpReview({ token }: { token: string }) {
  const client = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Row | null>(null);
  const [status, setStatus] = useState("TRIAGED");
  const [group, setGroup] = useState("MODEL_ERROR");
  const [category, setCategory] = useState("INTENT_MISCLASSIFICATION");
  const [intent, setIntent] = useState("");
  const [notes, setNotes] = useState("");
  const [split, setSplit] = useState("train");
  const [independent, setIndependent] = useState(false);
  const [answerCorrect, setAnswerCorrect] = useState("");
  const [exampleKind, setExampleKind] = useState("CORRECTION");
  const [provenance, setProvenance] = useState("HUMAN_REVIEWED");
  const [spans, setSpans] = useState("[]");
  const [slots, setSlots] = useState("{}");
  const headers = { Authorization: `Bearer ${token}` };
  const quality = useQuery({
    queryKey: ["nlp-quality", token],
    queryFn: () => api("/admin/nlp/quality", { headers }),
  });
  const queue = useQuery({
    queryKey: ["nlp-reviews", token, offset],
    queryFn: () =>
      api(`/admin/nlp/reviews?limit=20&offset=${offset}`, { headers }),
  });
  const labels = useQuery({
    queryKey: ["review-intents"],
    queryFn: () => api("/nlp/intents"),
  });
  const invalidate = () => {
    void client.invalidateQueries({ queryKey: ["nlp-quality"] });
    void client.invalidateQueries({ queryKey: ["nlp-reviews"] });
  };
  const review = useMutation({
    mutationFn: () =>
      post(
        `/admin/nlp/reviews/${selected!.id}/review`,
        {
          expected_version: selected!.version,
          status,
          error_group: group,
          error_category: category,
          corrected_intent: intent || null,
          corrected_entities: JSON.parse(spans),
          corrected_slots: JSON.parse(slots),
          notes,
          split,
          independent,
          answer_correct:
            answerCorrect === "" ? null : answerCorrect === "true",
          example_kind: exampleKind,
          label_provenance: provenance,
        },
        token,
      ),
    onSuccess: (data) => {
      setSelected(data.data);
      invalidate();
    },
  });
  const action = useMutation({
    mutationFn: async ({
      path,
      body,
      method,
    }: {
      path: string;
      body: Row;
      method?: "DELETE";
    }) =>
      method
        ? api(path, { method, headers: { Authorization: `Bearer ${token}` } })
        : post(path, body, token),
    onSuccess: () => {
      invalidate();
      setSelected(null);
    },
  });
  const download = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/v1/admin/nlp/export", { headers });
      if (!response.ok) throw new Error("Reviewed export was unavailable");
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = "reviewed-feedback.jsonl";
      a.click();
      URL.revokeObjectURL(url);
    },
  });
  const data = quality.data?.data;
  return (
    <section className="panel">
      <h2>NLP review and reliability</h2>
      <p>
        Local, supervised feedback. Unreviewed feedback never trains or deploys
        a model.
      </p>
      {quality.error && <Notice error>{errorText(quality.error)}</Notice>}
      {data && (
        <>
          <dl className="diagnostic-grid">
            <dt>Model readiness</dt>
            <dd>{data.model_readiness}</dd>
            <dt>Model version</dt>
            <dd>{data.model_version || "No approved active model"}</dd>
            <dt>Dataset version</dt>
            <dd>{data.dataset_version || "Not recorded"}</dd>
            <dt>Reviewed intent accuracy</dt>
            <dd>
              {data.intent_accuracy == null
                ? "Not measured"
                : `${(data.intent_accuracy * 100).toFixed(1)}% (${data.reviewed_intent_examples} labelled cases)`}
            </dd>
            <dt>Entity slot accuracy</dt>
            <dd>
              {data.entity_slot_accuracy == null
                ? "Not measured"
                : `${(data.entity_slot_accuracy * 100).toFixed(1)}% (${data.entity_labelled_cases} cases)`}
            </dd>
            <dt>Reviewed answer correctness</dt>
            <dd>
              {data.answer_correctness == null
                ? "Not measured"
                : `${(data.answer_correctness * 100).toFixed(1)}%`}
            </dd>
            <dt>Question mix</dt>
            <dd>
              {data.drift.status} · {data.drift.recent_samples} recent /{" "}
              {data.drift.previous_samples} previous samples
            </dd>
            <dt>Retention</dt>
            <dd>
              {data.retention_days} days · question storage{" "}
              {data.text_retention_enabled
                ? "requires passenger opt-in"
                : "disabled"}
            </dd>
          </dl>
          <details>
            <summary>Stored error and usage statistics</summary>
            <pre>
              {JSON.stringify(
                {
                  feedback: data.feedback_categories,
                  error_groups: data.error_groups,
                  error_categories: data.error_categories,
                  usage: data.recent_usage,
                  rates: data.usage_rates,
                  confusions: data.confusions,
                },
                null,
                2,
              )}
            </pre>
          </details>
        </>
      )}
      <div className="toolbar">
        <Button onClick={() => download.mutate()}>
          Export approved feedback
        </Button>
        <Button
          variant="secondary"
          disabled={action.isPending}
          onClick={() =>
            action.mutate({ path: "/admin/nlp/training", body: {} })
          }
        >
          Train reviewed candidate
        </Button>
        <Button
          variant="ghost"
          onClick={() =>
            action.mutate({ path: "/admin/nlp/retention", body: {} })
          }
        >
          Apply feedback retention
        </Button>
      </div>
      {(action.error || download.error || review.error) && (
        <Notice error>
          {errorText(action.error || download.error || review.error)}
        </Notice>
      )}
      {queue.error && <Notice error>{errorText(queue.error)}</Notice>}
      <h3>Feedback queue</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Question</th>
              <th>Feedback</th>
              <th>Status</th>
              <th>Model</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {queue.data?.data.map((r: Row) => (
              <tr key={r.id}>
                <td>{r.text || "Question not retained"}</td>
                <td>{r.feedback}</td>
                <td>{r.status}</td>
                <td>{r.model_version || "Not recorded"}</td>
                <td>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setSelected(r);
                      setStatus(r.status === "NEW" ? "TRIAGED" : r.status);
                      setGroup(r.error_group || "MODEL_ERROR");
                      setCategory(
                        r.error_category || "INTENT_MISCLASSIFICATION",
                      );
                      setSplit(r.split || "train");
                      setIndependent(!!r.independent);
                      setAnswerCorrect(
                        r.answer_correct == null
                          ? ""
                          : String(r.answer_correct),
                      );
                      setExampleKind(r.example_kind || "CORRECTION");
                      setProvenance(r.label_provenance || "HUMAN_REVIEWED");
                      setIntent(r.corrected_intent || "");
                      setNotes(r.reviewer_notes || "");
                      setSpans(JSON.stringify(r.corrected_entities || []));
                      setSlots(JSON.stringify(r.corrected_slots || {}));
                    }}
                  >
                    Review
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="toolbar">
        <Button
          disabled={!offset}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Previous feedback
        </Button>
        <span>{queue.data?.total || 0} records</span>
        <Button
          disabled={offset + 20 >= (queue.data?.total || 0)}
          onClick={() => setOffset(offset + 20)}
        >
          Next feedback
        </Button>
      </div>
      {selected && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            review.mutate();
          }}
        >
          <h3>Review retained evidence</h3>
          <p>
            {selected.text ||
              "No text retained; this record cannot be approved for training."}
          </p>
          <details>
            <summary>Intent, entities, context and source evidence</summary>
            <pre>
              {JSON.stringify(
                {
                  intents: selected.predicted_intents,
                  entities: selected.extracted_entities,
                  context: selected.context,
                  source: selected.source,
                  results: selected.structured_results,
                },
                null,
                2,
              )}
            </pre>
          </details>
          <label className="field">
            Review status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {data?.statuses.map((s: string) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Error group
            <select value={group} onChange={(e) => setGroup(e.target.value)}>
              {[
                "MODEL_ERROR",
                "DATA_ERROR",
                "CONTEXT_ERROR",
                "RESPONSE_ERROR",
                "OPERATIONAL_ERROR",
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Error category
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {data?.taxonomy.map((s: string) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Corrected intent
            <input
              list="review-labels"
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
            />
          </label>
          <datalist id="review-labels">
            {labels.data?.data.map((r: Row) => (
              <option key={r.code} value={r.code} />
            ))}
          </datalist>
          <label className="field">
            Reviewer notes
            <textarea
              value={notes}
              maxLength={2000}
              onChange={(e) => setNotes(e.target.value)}
            />
          </label>
          <label className="field">
            Dataset split
            <select value={split} onChange={(e) => setSplit(e.target.value)}>
              {["train", "validation", "test"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={independent}
              onChange={(e) => setIndependent(e.target.checked)}
            />
            Independently collected holdout evidence
          </label>
          <label className="field">
            Answer correctness
            <select
              value={answerCorrect}
              onChange={(e) => setAnswerCorrect(e.target.value)}
            >
              <option value="">Not assessed</option>
              <option value="true">Correct</option>
              <option value="false">Incorrect</option>
            </select>
          </label>
          <label className="field">
            Example kind
            <select
              value={exampleKind}
              onChange={(e) => setExampleKind(e.target.value)}
            >
              {[
                "CORRECTION",
                "HARD_NEGATIVE",
                "CONFUSION",
                "SHORT_FOLLOWUP",
                "CONTEXTUAL",
                "OUT_OF_SCOPE",
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Label provenance
            <select
              value={provenance}
              onChange={(e) => setProvenance(e.target.value)}
            >
              <option value="HUMAN_REVIEWED">Human reviewed</option>
              <option value="AUTOMATED_DEMO_ACCEPTANCE">
                Automated DEMO acceptance
              </option>
            </select>
          </label>
          <details>
            <summary>Entity labels</summary>
            <label className="field">
              Corrected entity spans (JSON)
              <textarea
                value={spans}
                onChange={(e) => setSpans(e.target.value)}
              />
            </label>
            <label className="field">
              Corrected entity slots (JSON)
              <textarea
                value={slots}
                onChange={(e) => setSlots(e.target.value)}
              />
            </label>
          </details>
          <Button type="submit" disabled={review.isPending}>
            Save review
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() =>
              action.mutate({
                path: `/admin/nlp/reviews/${selected.id}/anonymize`,
                body: { expected_version: selected.version },
              })
            }
          >
            Anonymize retained text
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() =>
              action.mutate({
                path: `/admin/nlp/reviews/${selected.id}?expected_version=${selected.version}`,
                body: {},
                method: "DELETE",
              })
            }
          >
            Delete feedback
          </Button>
        </form>
      )}
      <h3>Training candidates and deployment history</h3>
      <details>
        <summary>Manual model transitions</summary>
        <pre>{JSON.stringify(data?.deployment_history || [], null, 2)}</pre>
      </details>
      {data?.runs.map((r: Row) => (
        <details key={r.id}>
          <summary>
            {r.status} · {r.run_id}
          </summary>
          <pre>
            {JSON.stringify({ metrics: r.metrics, gates: r.gates }, null, 2)}
          </pre>
          {["approve", "deploy", "rollback"].map((step) => (
            <Button
              key={step}
              disabled={action.isPending}
              variant="secondary"
              onClick={() =>
                action.mutate({
                  path: `/admin/nlp/models/${r.id}/${step}`,
                  body: { expected_version: r.version },
                })
              }
            >
              {step} model
            </Button>
          ))}
        </details>
      ))}
    </section>
  );
}
