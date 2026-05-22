const statusColors = {
  draft: "bg-gray-700 text-gray-300",
  processing: "bg-yellow-900/50 text-yellow-400",
  ready: "bg-green-900/50 text-green-400",
  exported: "bg-blue-900/50 text-blue-400",
};

interface BadgeProps {
  status: keyof typeof statusColors;
  className?: string;
}

export function Badge({ status, className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[status]} ${className}`}>
      {status}
    </span>
  );
}
