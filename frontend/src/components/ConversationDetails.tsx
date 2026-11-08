import type { Conversation } from "../api";

export function ConversationDetails({ response }: { response: Conversation }) {
  const sections = response.answer_sections || [];
  const comparison = response.results.find(
    (result) => result.intent === "CONTEXT_COMPARISON",
  );
  if (sections.length < 2 && !comparison) return null;
  return (
    <details className="conversation-details">
      <summary>
        {comparison
          ? "Compare recorded journey facts"
          : `Answer details · ${sections.length} topics`}
      </summary>
      {comparison ? (
        <div className="comparison-facts">
          {comparison.results.map((row: any) => (
            <section key={row.result_id}>
              <h4>
                Option {row.option} · {row.service_numbers?.join(" → ")}
              </h4>
              <dl>
                <dt>Fare</dt>
                <dd>{row.fare == null ? "Unknown" : `INR ${row.fare}`}</dd>
                <dt>
                  {row.arrival_kind === "estimated"
                    ? "Estimated arrival"
                    : "Scheduled arrival"}
                </dt>
                <dd>{new Date(row.arrival).toLocaleString("en-IN")}</dd>
                <dt>Journey duration</dt>
                <dd>{row.duration_minutes} minutes</dd>
                <dt>Recorded AC</dt>
                <dd>{row.ac == null ? "Unknown" : row.ac ? "Yes" : "No"}</dd>
                <dt>Source</dt>
                <dd>{row.sources?.join(", ") || "Unspecified"}</dd>
              </dl>
            </section>
          ))}
        </div>
      ) : (
        sections.map((section) => (
          <section key={section.intent}>
            <h4>{section.title}</h4>
            <p>{section.text}</p>
          </section>
        ))
      )}
    </details>
  );
}
