import { ArrowRight } from "lucide-react";
export function ContextualActions({
  actions,
  onAction,
  disabled = false,
}: {
  actions: { label: string; query: string }[];
  onAction: (query: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="followups" aria-label="Suggested next questions">
      {actions.map((action) => (
        <button
          disabled={disabled}
          key={action.label}
          onClick={() => onAction(action.query)}
        >
          {action.label}
          <ArrowRight size={12} />
        </button>
      ))}
    </div>
  );
}
