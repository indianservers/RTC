import { Clock3, AlertCircle, CheckCircle2 } from "lucide-react";
import { Badge } from "./ui";
export function StatusIndicator({
  status,
  verifiedAt,
}: {
  status?: string | null;
  verifiedAt?: string | null;
}) {
  const code = (status || "UNKNOWN").toUpperCase();
  const stale = code === "STALE";
  const cancelled = code === "CANCELLED";
  const known = ["KNOWN", "RUNNING", "ACTUAL"].includes(code);
  return (
    <span className="status-indicator">
      <Badge tone={stale || cancelled ? "amber" : known ? "green" : "muted"}>
        {stale || cancelled ? (
          <AlertCircle size={12} />
        ) : known ? (
          <CheckCircle2 size={12} />
        ) : (
          <Clock3 size={12} />
        )}{" "}
        {code.replaceAll("_", " ")}
      </Badge>
      {verifiedAt && (
        <small>Verified {new Date(verifiedAt).toLocaleString("en-IN")}</small>
      )}
    </span>
  );
}
