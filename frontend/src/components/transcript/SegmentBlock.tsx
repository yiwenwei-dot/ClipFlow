"use client";

import { Eye, EyeOff } from "lucide-react";
import type { TranscriptSegment, Speaker } from "@/lib/types";
import { SpeakerLabel } from "./SpeakerLabel";

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

interface SegmentBlockProps {
  segment: TranscriptSegment;
  speaker?: Speaker;
  isActive: boolean;
  onClick: () => void;
  onToggleCut: () => void;
}

export function SegmentBlock({ segment, speaker, isActive, onClick, onToggleCut }: SegmentBlockProps) {
  const isCut = segment.cut_decision === "cut" || segment.cut_decision === "user_cut";

  return (
    <div
      onClick={onClick}
      className={`group flex gap-3 p-3 rounded-lg cursor-pointer transition-colors
        ${isActive ? "bg-blue-500/10 border border-blue-500/30" : "hover:bg-gray-800/50 border border-transparent"}
        ${isCut ? "bg-red-500/5" : ""}`}
    >
      <div className="w-20 shrink-0 space-y-1">
        {speaker && <SpeakerLabel label={speaker.label} color={speaker.color} />}
        <p className="text-xs text-gray-600">{formatTime(segment.start_ms)}</p>
      </div>

      <div className="flex-1 min-w-0">
        <p className={`text-sm leading-relaxed ${isCut ? "line-through text-gray-600" : "text-gray-200"}`}>
          {segment.text}
        </p>
        {isCut && segment.cut_reason && (
          <p className="text-xs text-gray-600 mt-1">{segment.cut_reason}</p>
        )}
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); onToggleCut(); }}
        className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-gray-700 text-gray-500 hover:text-gray-300 transition-all shrink-0 self-start"
        title={isCut ? "Restore segment" : "Cut segment"}
      >
        {isCut ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}
