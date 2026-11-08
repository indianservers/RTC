import { useId } from "react";
import { Search } from "lucide-react";
export function SearchField({
  label,
  value,
  onChange,
  placeholder = "Search local records…",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const id = useId();
  return (
    <div className="search-field">
      <label className="sr-only" htmlFor={id}>
        {label}
      </label>
      <div className="input-icon">
        <Search size={15} />
        <input
          id={id}
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          type="search"
        />
      </div>
    </div>
  );
}
