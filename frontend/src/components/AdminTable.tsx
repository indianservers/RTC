import { useEffect, useMemo, useState } from "react";

import * as Dialog from "@radix-ui/react-dialog";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";

import {
  useMutation,
  useQuery,
  useQueries,
  useQueryClient,
} from "@tanstack/react-query";

import {
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Plus,
  Pencil,
  Trash2,
  Columns3,
  X,
} from "lucide-react";

import { useSearchParams } from "react-router-dom";

import {
  ConfirmDialog,
  RecordDrawer,
  LoadingSkeleton,
  ErrorState,
} from "./feedback";

import { api, errorText, type Row } from "../api";

import { SearchField } from "./SearchField";

import { FilterBar } from "./FilterBar";

import { Badge, Button, Notice } from "./ui";

export function AdminTable({
  resource,

  token,

  definition,

  readonly = false,
}: {
  resource: string;

  token: string;

  definition?: Row;

  readonly?: boolean;
}) {
  const [offset, setOffset] = useState(0);
  const [staged, setStaged] = useState("");

  const [params] = useSearchParams();

  const [filter, setFilter] = useState(
    params.get("record") || params.get("q") || "",
  );

  const [debouncedFilter, setDebouncedFilter] = useState(filter);

  const [status, setStatus] = useState("");

  const [detail, setDetail] = useState<Row | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedFilter(filter), 200);

    return () => clearTimeout(timer);
  }, [filter]);

  const [sorting, setSorting] = useState<SortingState>([]);

  const [visibility, setVisibility] = useState<VisibilityState>({});

  const [editing, setEditing] = useState<Row | null>(null);

  const [creating, setCreating] = useState(false);

  const [values, setValues] = useState<Row>({});

  const [baseline, setBaseline] = useState("");

  const [discard, setDiscard] = useState(false);
  const [leaving, setLeaving] = useState<string | null>(null);

  const dirty = !!editing && JSON.stringify(values) !== baseline;

  useEffect(() => {
    if (!dirty) return;

    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };

    window.addEventListener("beforeunload", warn);

    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function closeEditor() {
    if (save.isPending) return;

    if (dirty) setDiscard(true);
    else {
      setEditing(null);
      setCreating(false);
    }
  }

  const [referenceSearch, setReferenceSearch] = useState("");
  const [referenceQuery, setReferenceQuery] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setReferenceQuery(referenceSearch), 180);
    return () => clearTimeout(timer);
  }, [referenceSearch]);
  const [error, setError] = useState("");

  const client = useQueryClient();

  const headers = { Authorization: `Bearer ${token}` };

  const q = useQuery({
    queryKey: [
      "admin-list",

      resource,

      offset,

      token,

      debouncedFilter,

      sorting,

      status,
    ],

    queryFn: ({ signal }) =>
      api(
        `${readonly ? "/admin/ui/catalog/" : "/admin/"}${resource}?limit=25&offset=${offset}&q=${encodeURIComponent(debouncedFilter)}&sort_by=${encodeURIComponent(sorting[0]?.id || "id")}&descending=${sorting[0]?.desc || false}${status ? `&active=${status}` : ""}`,

        { headers, signal },
      ),

    retry: false,
  });

  const referenceKeys = Array.from(
    new Set<string>(Object.values(definition?.references || {}) as string[]),
  );

  const referenceData = useQueries({
    queries: referenceKeys.map((key) => ({
      queryKey: ["admin-reference", key, token, referenceQuery],

      queryFn: ({ signal }) =>
        api(`/admin/${key}?limit=100&q=${encodeURIComponent(referenceQuery)}`, {
          headers,
          signal,
        }),

      enabled: !!editing,
    })),
  });

  const references: Record<string, Row[]> = {};

  referenceData.forEach((q, i) => {
    references[referenceKeys[i]] = q.data?.data || [];
  });

  const tableBusy = q.isFetching || filter !== debouncedFilter;

  const rows: Row[] = useMemo(() => q.data?.data || [], [q.data]);

  const columns = useMemo<ColumnDef<Row>[]>(
    () =>
      Array.from(new Set(rows.flatMap((r) => Object.keys(r))))

        .filter((k) => !["taxonomy", "_owner_hash"].includes(k))

        .map((key) => ({
          accessorKey: key,

          header: key.replaceAll("_", " "),

          cell: ({ getValue }) =>
            key === "active" ? (
              <Badge tone={getValue() ? "green" : "muted"}>
                {getValue() ? "Active" : "Inactive"}
              </Badge>
            ) : (
              <span title={String(getValue() ?? "Not available")}>
                {typeof getValue() === "object"
                  ? JSON.stringify(getValue())
                  : String(getValue() ?? "Not available")}
              </span>
            ),
        })),

    [rows],
  );

  const table = useReactTable({
    data: rows,

    columns,

    state: { sorting, globalFilter: filter, columnVisibility: visibility },

    onSortingChange: (updater) => {
      setSorting(updater);

      setOffset(0);
    },

    onGlobalFilterChange: setFilter,

    onColumnVisibilityChange: setVisibility,

    getCoreRowModel: getCoreRowModel(),

    manualSorting: true,

    manualFiltering: true,
  });

  const save = useMutation({
    mutationFn: () =>
      api(`/admin/${resource}${creating ? "" : `/${editing!.id}`}`, {
        method: creating ? "POST" : "PUT",

        headers,

        body: JSON.stringify(
          Object.fromEntries(
            Object.entries(values).map(([key, value]) => [
              key,
              value === "" &&
              definition?.schema.properties[key]?.anyOf?.some(
                (option: Row) => option.type === "null",
              )
                ? null
                : value,
            ]),
          ),
        ),
      }),

    onSuccess: (response) => {
      if (response.publication_state) setStaged(response.data.id);
      setEditing(null);

      setCreating(false);

      setError("");

      void client.invalidateQueries({ queryKey: ["admin-list", resource] });

      void client.invalidateQueries({ queryKey: ["bootstrap"] });
    },

    onError: (e) => setError(errorText(e)),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) =>
      api(`/admin/${resource}/${id}`, { method: "DELETE", headers }),

    onSuccess: () =>
      void client.invalidateQueries({ queryKey: ["admin-list", resource] }),

    onError: (e) => setError(errorText(e)),
  });

  function open(row?: Row) {
    setCreating(!row);

    setEditing(row || {});

    setError("");

    const defaults = Object.fromEntries(
      Object.entries(definition?.schema.properties || {}).map(
        ([key, property]: [string, any]) => [
          key,

          row?.[key] ??
            (key === "recorded_at"
              ? new Date().toISOString()
              : key === "source_id"
                ? sessionStorage.getItem("rtc-admin-source")
                : undefined) ??
            property.default ??
            "",
        ],
      ),
    );

    setValues(defaults);

    setBaseline(JSON.stringify(defaults));
  }

  return (
    <div className="panel data-panel">
      {staged && (
        <Notice>
          Draft saved. Passenger data is unchanged.{" "}
          <a href={`/admin/imports?batch=${staged}`}>
            Validate and review this change set
          </a>
        </Notice>
      )}
      <ConfirmDialog
        open={discard}
        onOpenChange={(open) => {
          setDiscard(open);
          if (!open) setLeaving(null);
        }}
        title="Discard unsaved changes?"
        description="Your edits have not been saved to the database."
        onConfirm={() => {
          setEditing(null);
          setCreating(false);
          if (leaving) window.location.assign(leaving);
        }}
      />

      {definition && (
        <Button
          variant="secondary"
          onClick={async () => {
            try {
              const operator = sessionStorage.getItem("rtc-admin-operator");
              const response = await fetch(
                `/api/v1/admin/data/export/${resource}${operator ? `?operator_id=${encodeURIComponent(operator)}` : ""}`,
                { headers },
              );
              if (!response.ok)
                throw new Error(
                  "Export failed; narrow the operator scope or check authorization.",
                );
              const url = URL.createObjectURL(await response.blob());
              const link = document.createElement("a");
              link.href = url;
              link.download = `local-${resource}.csv`;
              link.click();
              URL.revokeObjectURL(url);
            } catch (e) {
              setError(errorText(e));
            }
          }}
        >
          Export scoped records
        </Button>
      )}
      <RecordDrawer record={detail} onClose={() => setDetail(null)} />

      <ConfirmDialog
        open={!!deleteTarget}

        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}

        title="Deactivate this record?"

        description="This performs a server-authorized soft deletion. Existing references are preserved."

        onConfirm={() => {
          if (deleteTarget) deactivate.mutate(deleteTarget);
        }}

        pending={deactivate.isPending}
      />

      <FilterBar className="table-toolbar" label="Record search and filters">
        <SearchField
          label="Search records"

          placeholder="Search all local records…"

          value={filter}

          onChange={(value) => {
            setFilter(value);

            setOffset(0);
          }}
        />

        <div>
          <select
            aria-label="Record status"

            value={status}

            onChange={(e) => {
              setStatus(e.target.value);

              setOffset(0);
            }}
          >
            <option value="">All statuses</option>

            <option value="true">Active</option>

            <option value="false">Inactive</option>
          </select>

          <details className="column-menu">
            <summary>
              <Columns3 size={15} />
              Columns
            </summary>

            <div>
              {table.getAllLeafColumns().map((column) => (
                <label key={column.id}>
                  <input
                    type="checkbox"

                    checked={column.getIsVisible()}

                    onChange={column.getToggleVisibilityHandler()}
                  />

                  {column.id}
                </label>
              ))}
            </div>
          </details>

          {!readonly && (
            <Button onClick={() => open()}>
              <Plus size={15} />
              Add record
            </Button>
          )}
        </div>
      </FilterBar>

      {readonly && (
        <Notice>
          Read-only. No compatible write API is available for this domain.
        </Notice>
      )}

      {q.isPending && <LoadingSkeleton />}

      {q.error && (
        <ErrorState
          message={q.error.message}

          onRetry={() => void q.refetch()}
        />
      )}

      {error && <Notice error>{error}</Notice>}

      <div className="table-scroll" aria-busy={tableBusy}>
        <table>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id}>
                    <button onClick={header.column.getToggleSortingHandler()}>
                      {flexRender(
                        header.column.columnDef.header,

                        header.getContext(),
                      )}

                      <ArrowUpDown size={12} />
                    </button>
                  </th>
                ))}

                <th>Actions</th>
              </tr>
            ))}
          </thead>

          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.original.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}

                <td>
                  <div className="row-actions">
                    <Button
                      variant="ghost"

                      aria-label="View record details"

                      onClick={() => setDetail(row.original)}
                    >
                      Details
                    </Button>

                    {!readonly && (
                      <>
                        <Button
                          variant="ghost"

                          aria-label={`Edit ${row.original.name || row.original.code || row.original.number || "record"}`}

                          disabled={tableBusy}

                          onClick={() => open(row.original)}
                        >
                          <Pencil size={14} />
                        </Button>

                        <Button
                          variant="ghost"

                          aria-label={`Deactivate ${row.original.name || row.original.code || row.original.number || "record"}`}

                          disabled={
                            tableBusy ||
                            deactivate.isPending ||
                            !row.original.active
                          }

                          onClick={() => setDeleteTarget(row.original.id)}
                        >
                          <Trash2 size={14} />
                        </Button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!q.isPending && !rows.length && (
        <p className="empty">No records in this page.</p>
      )}

      <div className="pagination">
        <span>
          Records {rows.length ? offset + 1 : 0}–{offset + rows.length} · of{" "}
          {q.data?.total ?? "unknown"} matching local records
        </span>

        <div>
          <Button
            variant="secondary"

            disabled={!offset}

            onClick={() => setOffset((n) => Math.max(0, n - 25))}
          >
            <ChevronLeft size={15} />
            Previous
          </Button>

          <Button
            variant="secondary"

            disabled={
              offset + rows.length >= (q.data?.total ?? offset + rows.length)
            }

            onClick={() => setOffset((n) => n + 25)}
          >
            Next
            <ChevronRight size={15} />
          </Button>
        </div>
      </div>

      <Dialog.Root
        open={!!editing}

        onOpenChange={(open) => {
          if (!open) closeEditor();
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="modal-overlay" />

          <Dialog.Content className="modal" aria-describedby={undefined}>
            <div className="card-top">
              <Dialog.Title asChild>
                <h2>
                  {creating ? "Add" : "Edit"} {resource}
                </h2>
              </Dialog.Title>

              <Button
                variant="ghost"

                aria-label="Close form"

                onClick={closeEditor}
              >
                <X size={18} />
              </Button>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();

                save.mutate();
              }}
            >
              {referenceKeys.length > 0 && (
                <label className="field">
                  Search local reference records
                  <input
                    value={referenceSearch}
                    onChange={(e) => setReferenceSearch(e.target.value)}
                    placeholder="Name, code or local ID"
                  />
                  <small>
                    Search applies to the reference selectors below. Selected
                    IDs remain preserved.
                  </small>
                </label>
              )}
              <div className="edit-grid">
                {Object.entries(definition?.schema.properties || {}).map(
                  ([key, property]: [string, any]) => {
                    const spec =
                      property.anyOf?.find((v: Row) => v.type !== "null") ||
                      property;

                    const type = spec.type;

                    if (definition?.references?.[key]) {
                      const options =
                        references[definition.references[key]] || [];

                      return (
                        <label className="field" key={key}>
                          {key.replaceAll("_", " ")}

                          <select
                            required={definition?.schema.required?.includes(
                              key,
                            )}

                            value={values[key] || ""}

                            onChange={(e) =>
                              setValues({ ...values, [key]: e.target.value })
                            }
                          >
                            <option value="">Choose a local record</option>

                            {values[key] &&
                              !options.some((r) => r.id === values[key]) && (
                                <option value={values[key]}>
                                  Current reference: {values[key]}
                                </option>
                              )}

                            {options.map((row) => (
                              <option key={row.id} value={row.id}>
                                {row.name || row.number || row.code || row.id}

                                {row.code && row.name ? ` (${row.code})` : ""}
                              </option>
                            ))}
                          </select>

                          <small className="subtle">
                            Up to 100 matching references shown; search above to
                            find other records.
                          </small>
                        </label>
                      );
                    }

                    if (type === "object" || type === "array")
                      return (
                        <label className="field" key={key}>
                          {key.replaceAll("_", " ")}
                          <textarea
                            aria-label={key.replaceAll("_", " ")}
                            value={
                              typeof values[key] === "object"
                                ? JSON.stringify(values[key], null, 2)
                                : values[key] || ""
                            }
                            onChange={(e) => {
                              let value: unknown = e.target.value;
                              try {
                                value = JSON.parse(e.target.value);
                              } catch {
                                /* backend validation reports malformed JSON fields */
                              }
                              setValues({ ...values, [key]: value });
                            }}
                          />
                        </label>
                      );
                    if (
                      type === "boolean" &&
                      property.anyOf?.some(
                        (option: Row) => option.type === "null",
                      )
                    )
                      return (
                        <label className="field" key={key}>
                          {key.replaceAll("_", " ")}
                          <select
                            value={
                              values[key] == null ? "" : String(values[key])
                            }
                            onChange={(e) =>
                              setValues({
                                ...values,
                                [key]:
                                  e.target.value === ""
                                    ? null
                                    : e.target.value === "true",
                              })
                            }
                          >
                            <option value="">Not confirmed</option>
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                          </select>
                        </label>
                      );
                    return type === "boolean" ? (
                      <label className="check-field" key={key}>
                        <input
                          type="checkbox"

                          checked={values[key] === true}

                          onChange={(e) =>
                            setValues({ ...values, [key]: e.target.checked })
                          }
                        />

                        {key.replaceAll("_", " ")}
                      </label>
                    ) : (
                      <label className="field" key={key}>
                        {key.replaceAll("_", " ")}

                        <input
                          required={definition?.schema.required?.includes(key)}

                          type={
                            type === "integer" || type === "number"
                              ? "number"
                              : spec.format === "date"
                                ? "date"
                                : "text"
                          }

                          step={type === "integer" ? 1 : "any"}

                          min={spec.minimum}

                          max={spec.maximum}

                          maxLength={spec.maxLength}

                          value={values[key] ?? ""}

                          onChange={(e) =>
                            setValues({
                              ...values,

                              [key]:
                                type === "integer" || type === "number"
                                  ? e.target.value === ""
                                    ? ""
                                    : Number(e.target.value)
                                  : e.target.value,
                            })
                          }
                        />
                      </label>
                    );
                  },
                )}
              </div>

              {error && <Notice error>{error}</Notice>}

              <div className="modal-actions">
                <Button
                  type="button"

                  variant="secondary"

                  onClick={closeEditor}
                >
                  Cancel
                </Button>

                <Button type="submit" disabled={save.isPending}>
                  {save.isPending ? "Saving…" : "Save record"}
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
