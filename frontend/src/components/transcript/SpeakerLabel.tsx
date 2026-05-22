interface SpeakerLabelProps {
  label: string;
  color: string;
}

export function SpeakerLabel({ label, color }: SpeakerLabelProps) {
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium shrink-0"
      style={{ backgroundColor: `${color}20`, color }}
    >
      {label}
    </span>
  );
}
