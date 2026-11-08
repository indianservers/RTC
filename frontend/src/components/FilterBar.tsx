import type { ReactNode } from "react";
export function FilterBar({
  children,
  label,
  className = "",
}: {
  children: ReactNode;
  label: string;
  className?: string;
}) {
  return (
    <div className={`filter-bar ${className}`} role="group" aria-label={label}>
      {children}
    </div>
  );
}
