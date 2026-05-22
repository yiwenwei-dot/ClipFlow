"use client";

import { useEffect, useRef } from "react";
import { FileText } from "lucide-react";
import type { TranscriptSegment, Speaker } from "@/lib/types";
import { SegmentBlock } from "./SegmentBlock";
import { usePlayerStore } from "@/stores/player-store";

interface TranscriptViewProps {
  segments: TranscriptSegment[];
  speakers: Speaker[];
  onToggleCut: (segmentId: string) => void;
  onSeek: (timeMs: number) => void;
}

export function TranscriptView({ segments, speakers, onToggleCut, onSeek }: TranscriptViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeSegmentId = usePlayerStore((s) => s.activeSegmentId);

  useEffect(() => {
    if (!activeSegmentId || !containerRef.current) return;
    const el = containerRef.current.querySelector(`[data-segment-id="${activeSegmentId}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeSegmentId]);

  if (segments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 gap-3">
        <FileText size={48} className="text-gray-700" />
        <p className="text-sm">No transcript yet</p>
        <p className="text-xs text-gray-600">Process your clips to generate a transcript</p>
      </div>
    );
  }

  const speakerMap = new Map(speakers.map((s) => [s.id, s]));

  return (
    <div ref={containerRef} className="h-full overflow-y-auto space-y-1 p-4">
      {segments.map((segment) => (
        <div key={segment.id} data-segment-id={segment.id}>
          <SegmentBlock
            segment={segment}
            speaker={segment.speaker_id ? speakerMap.get(segment.speaker_id) : undefined}
            isActive={segment.id === activeSegmentId}
            onClick={() => onSeek(segment.start_ms)}
            onToggleCut={() => onToggleCut(segment.id)}
          />
        </div>
      ))}
    </div>
  );
}
