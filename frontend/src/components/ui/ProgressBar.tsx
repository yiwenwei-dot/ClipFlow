interface ProgressBarProps {
  value: number;
  color?: string;
  className?: string;
}

export function ProgressBar({ value, color = "bg-blue-500", className = "" }: ProgressBarProps) {
  return (
    <div className={`w-full h-2 bg-gray-800 rounded-full overflow-hidden ${className}`}>
      <div
        className={`h-full rounded-full transition-all duration-300 ${color}`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}
