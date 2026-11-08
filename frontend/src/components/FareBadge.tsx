import { fareText } from "../api";
export function FareBadge({
  value,
  status,
}: {
  value?: string | number | null;
  status?: string;
}) {
  return (
    <div className="fare">
      <strong>{fareText(value)}</strong>
      <span>
        {value == null
          ? status === "PARTIAL"
            ? "Partial fare; total not confirmed"
            : "Fare not confirmed"
          : "per passenger"}
      </span>
    </div>
  );
}
