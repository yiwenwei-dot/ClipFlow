"use client";

import type { Clip, TranscriptSegment } from "@/lib/types";

interface VisualTimelineProps {
  clips: Clip[];
  segments: TranscriptSegment[];
  currentTime: number;
  onSeek: (time: number) => void;
}

export function VisualTimeline({ clips, segments, currentTime, onSeek }: VisualTimelineProps) {
  const totalDuration = clips.reduce((sum, c) => sum + (c.duration_ms || 0), 0);
  if (!totalDuration) return null;

  const cutSegments = segments.filter(
    (s) => s.cut_decision === "cut" || s.cut_decision === "user_cut"
  );

  return (
    <div className="relative w-full h-8 bg-gray-900 rounded-lg overflow-hidden cursor-pointer"
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        onSeek(pct * totalDuration);
      }}
    >
      {clips.map((clip, i) => {
        const offset = clips.slice(0, i).reduce((sum, c) => sum + (c.duration_ms || 0), 0);
        const width = ((clip.duration_ms || 0) / totalDuration) * 100;
        const colors = ["bg-blue-600/40", "bg-purple-600/40", "bg-green-600/40", "bg-orange-600/40"];
        return (
          <div
            key={clip.id}
            className={`absolute top-0 h-full ${colors[i % colors.length]} border-r border-gray-800`}
            style={{ left: `${(offset / totalDuration) * 100}%`, width: `${width}%` }}
          />
        );
      })}
      {cutSegments.map((seg) => (
        <div
          key={seg.id}
          className="absolute top-0 h-full bg-red-500/20"
          style={{
            left: `${(seg.start_ms / totalDuration) * 100}%`,
            width: `${((seg.end_ms - seg.start_ms) / totalDuration) * 100}%`,
          }}
        />
      ))}
      <div
        className="absolute top-0 h-full w-0.5 bg-white z-10"
        style={{ left: `${(currentTime / totalDuration) * 100}%` }}
      />
    </div>
  );
}
