import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, post, errorText, type Row } from "../api";
import { Button, Notice } from "../components/ui";
import { ConfirmDialog } from "../components/feedback";
export function AccessManagement({
  token,
  role,
}: {
  token: string;
  role: string;
}) {
  const [username, setUsername] = useState("");
  const [kind, setKind] = useState("EDITOR");
  const [global, setGlobal] = useState(false);
  const [issued, setIssued] = useState<Row>();
  const [revoke, setRevoke] = useState<Row>();
  const [offset, setOffset] = useState(0);
  const client = useQueryClient();
  const list = useQuery({
    queryKey: ["local-users", token, offset],
    queryFn: () =>
      api(`/admin/data/users?offset=${offset}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    enabled: role === "ADMIN",
  });
  const create = useMutation({
    mutationFn: () => {
      const operator = sessionStorage.getItem("rtc-admin-operator");
      if (!operator && !global)
        throw new Error(
          "Choose one managing operator above, or explicitly authorize a global independent reviewer.",
        );
      return post(
        "/admin/data/users",
        {
          username,
          role: kind,
          operator_ids: global ? [] : [operator],
          global_scope: global && kind === "APPROVER",
        },
        token,
      );
    },
    onSuccess: (r) => {
      setIssued(r.data);
      void client.invalidateQueries({ queryKey: ["local-users"] });
    },
  });
  const deactivate = useMutation({
    mutationFn: (id: string) =>
      api(`/admin/data/users/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }),
    onSuccess: () => {
      setRevoke(undefined);
      void client.invalidateQueries({ queryKey: ["local-users"] });
    },
  });
  if (role !== "ADMIN")
    return (
      <Notice>
        Only a global administrator can provision local access. Your role and
        operator permissions are enforced by the backend.
      </Notice>
    );
  return (
    <section className="panel">
      <h2>Local access & independent approval</h2>
      <p>
        Create separate named editor and approver capabilities. A draft creator
        cannot approve their own work. Tokens are displayed once and only hashes
        are stored in the local database.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <div className="edit-grid">
          <label className="field">
            New local username
            <input
              required
              minLength={3}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label className="field">
            New local role
            <select
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                setGlobal(false);
              }}
            >
              <option value="EDITOR">Data editor</option>
              <option value="APPROVER">Independent approver</option>
            </select>
          </label>
        </div>
        {kind === "APPROVER" && (
          <label>
            <input
              type="checkbox"
              checked={global}
              onChange={(e) => setGlobal(e.target.checked)}
            />{" "}
            Explicit global approval authority for shared/all-operator changes
          </label>
        )}
        <Button disabled={create.isPending}>Provision scoped access</Button>
      </form>
      {create.error && <Notice error>{errorText(create.error)}</Notice>}
      {deactivate.error && <Notice error>{errorText(deactivate.error)}</Notice>}
      {issued && (
        <Notice>
          <p>
            Copy this capability to the authorized local user, then dismiss it.
            The token is not kept in browser storage.
          </p>
          <label className="field">
            One-time local token
            <input readOnly autoComplete="off" value={issued.token} />
          </label>
          <Button variant="secondary" onClick={() => setIssued(undefined)}>
            Dismiss displayed capability
          </Button>
        </Notice>
      )}
      <h3>Stored local identities</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Role / scope</th>
              <th>Status</th>
              <th>Access</th>
            </tr>
          </thead>
          <tbody>
            {list.data?.data.map((user: Row) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>
                  {user.grants
                    .map(
                      (g: Row) =>
                        `${g.role}: ${g.operator_id || "Explicit global scope"}`,
                    )
                    .join(", ")}
                </td>
                <td>{user.active ? "Active" : "Revoked"}</td>
                <td>
                  <Button
                    variant="ghost"
                    disabled={!user.active}
                    onClick={() => setRevoke(user)}
                  >
                    Revoke local access
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <Button
          variant="ghost"
          disabled={!offset}
          onClick={() => setOffset((n) => Math.max(0, n - 25))}
        >
          Previous users
        </Button>
        <Button
          variant="ghost"
          disabled={offset + 25 >= (list.data?.total || 0)}
          onClick={() => setOffset((n) => n + 25)}
        >
          Next users
        </Button>
      </div>
      <ConfirmDialog
        open={!!revoke}
        onOpenChange={(open) => {
          if (!open) setRevoke(undefined);
        }}
        title="Revoke this local capability?"
        description="Future requests with this user's token will be rejected. Audit history and published data are preserved."
        onConfirm={() => revoke && deactivate.mutate(String(revoke.id))}
        pending={deactivate.isPending}
      />
    </section>
  );
}
