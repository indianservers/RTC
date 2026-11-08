import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Row } from "../api";
import { Badge, Notice } from "../components/ui";
export function ManagementScope({ token, meta }: { token: string; meta: Row }) {
  const client = useQueryClient();
  const [operator, setOperator] = useState(
    sessionStorage.getItem("rtc-admin-operator") || "",
  );
  const [source, setSource] = useState(
    sessionStorage.getItem("rtc-admin-source") || "",
  );
  const options = useQuery({
    queryKey: ["management-operators", token],
    queryFn: () =>
      api("/admin/operators?limit=100", {
        headers: { Authorization: `Bearer ${token}` },
      }),
  });
  const sources = useQuery({
    queryKey: ["management-sources", token, operator],
    queryFn: () =>
      api("/admin/data-sources?limit=100", {
        headers: { Authorization: `Bearer ${token}` },
      }),
  });
  function choose(value: string, key: string) {
    sessionStorage.setItem(key, value);
    void client.invalidateQueries();
  }
  return (
    <section
      className="panel management-scope"
      aria-label="Data management authorization"
    >
      <div className="card-top">
        <span>
          {meta.actor} · <Badge>{meta.role}</Badge>
        </span>
        <span>
          {meta.publication_required
            ? "Draft → validated → independently approved → published"
            : "Explicit demo/test direct-write mode"}
        </span>
      </div>
      <div className="edit-grid">
        <label className="field">
          Managing operator
          <select
            value={operator}
            onChange={(e) => {
              setOperator(e.target.value);
              setSource("");
              sessionStorage.removeItem("rtc-admin-source");
              choose(e.target.value, "rtc-admin-operator");
            }}
          >
            <option value="">
              {meta.role === "ADMIN"
                ? "All / shared records"
                : "Select an authorized operator"}
            </option>
            {options.data?.data.map((row: Row) => (
              <option key={row.id} value={row.id}>
                {row.name} ({row.code})
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Import / change source
          <select
            value={source}
            onChange={(e) => {
              setSource(e.target.value);
              choose(e.target.value, "rtc-admin-source");
            }}
          >
            <option value="">Local input; no official-source claim</option>
            {sources.data?.data.map((row: Row) => (
              <option key={row.id} value={row.id}>
                {row.name}
                {row.is_demo
                  ? " · DEMO"
                  : row.is_official
                    ? " · reviewed official source"
                    : " · unverified local source"}
              </option>
            ))}
          </select>
        </label>
      </div>
      {meta.publication_required && (
        <Notice>
          Saving a record creates an unpublished draft. A different authorized
          user approves it. Shared station/geographic definitions require a
          global administrator.
        </Notice>
      )}
    </section>
  );
}
