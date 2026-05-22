"use client";

import { GripVertical, Video, X } from "lucide-react";
import type { Clip } from "@/lib/types";

function formatDuration(ms: number | null): string {
  if (!ms) return "--:--";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function formatSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface ClipCardProps {
  clip: Clip;
  onDelete?: () => void;
  dragHandleProps?: Record<string, unknown>;
}

export function ClipCard({ clip, onDelete, dragHandleProps }: ClipCardProps) {
  return (
    <div className="flex items-center gap-3 bg-gray-900 border border-gray-800 rounded-lg p-3 group">
      <div {...dragHandleProps} className="cursor-grab text-gray-600 hover:text-gray-400">
        <GripVertical size={18} />
      </div>
      <div className="w-10 h-10 bg-gray-800 rounded flex items-center justify-center shrink-0">
        <Video size={18} className="text-gray-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-200 truncate">{clip.filename}</p>
        <p className="text-xs text-gray-500">
          {formatDuration(clip.duration_ms)}
          {clip.file_size_bytes ? ` · ${formatSize(clip.file_size_bytes)}` : ""}
        </p>
      </div>
      {onDelete && (
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-800 text-gray-500 hover:text-red-400 transition-all"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
