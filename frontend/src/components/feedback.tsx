import { ArrowRight, RefreshCw, X } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { Button, Notice } from "./ui";
import type { Row } from "../api";
export function LoadingSkeleton({
  label = "Loading local records…",
}: {
  label?: string;
}) {
  return (
    <div role="status" className="loading-skeleton">
      <span className="sr-only">{label}</span>
      <i />
      <i />
      <i />
    </div>
  );
}
export function ErrorState({
  message,
  onRetry,
  id,
}: {
  message: string;
  onRetry?: () => void;
  id?: string;
}) {
  return (
    <div id={id}>
      <Notice error>
        <span>{message}</span>
        {onRetry && (
          <Button variant="ghost" onClick={onRetry}>
            <RefreshCw size={14} />
            Retry
          </Button>
        )}
      </Notice>
    </div>
  );
}
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  onConfirm,
  pending = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  onConfirm: () => void;
  pending?: boolean;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content className="modal confirm-dialog">
          <Dialog.Title>{title}</Dialog.Title>
          <Dialog.Description>{description}</Dialog.Description>
          <div className="modal-actions">
            <Button
              variant="secondary"
              disabled={pending}
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              disabled={pending}
              onClick={() => {
                onConfirm();
                onOpenChange(false);
              }}
            >
              Confirm <ArrowRight size={14} />
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function RecordDrawer({
  record,
  onClose,
  title = "Record details",
}: {
  record: Row | null;
  onClose: () => void;
  title?: string;
}) {
  return (
    <Dialog.Root
      open={!!record}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content
          className="modal record-drawer"
          aria-describedby={undefined}
        >
          <div className="card-top">
            <Dialog.Title>{title}</Dialog.Title>
            <Button
              variant="ghost"
              aria-label="Close record details"
              onClick={onClose}
            >
              <X size={18} />
            </Button>
          </div>
          <dl className="record-fields">
            {Object.entries(record || {}).map(([key, value]) => (
              <div key={key}>
                <dt>{key.replaceAll("_", " ")}</dt>
                <dd>
                  {value == null
                    ? "Not available"
                    : typeof value === "object"
                      ? JSON.stringify(value, null, 2)
                      : String(value)}
                </dd>
              </div>
            ))}
          </dl>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
