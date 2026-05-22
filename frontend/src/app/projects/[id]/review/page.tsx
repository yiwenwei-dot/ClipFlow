"use client";

import { useState, useEffect, use } from "react";
import { ArrowLeft, ArrowRight, SkipForward, Eye, EyeOff, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { SpeakerLabel } from "@/components/transcript/SpeakerLabel";
import type { TranscriptSegment, Speaker } from "@/lib/types";
import { api } from "@/lib/api-client";
import { useToastStore } from "@/stores/toast-store";

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function ReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const addToast = useToastStore((s) => s.addToast);
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [loading, setLoading] = useState(true);
  const [rendering, setRendering] = useState(false);

  useEffect(() => {
    Promise.all([
      api.getTranscript(id),
      api.getProject(id),
    ]).then(([segs]) => {
      setSegments(segs);
      setLoading(false);
    }).catch((e) => {
      setLoading(false);
      addToast({ type: "error", message: `Failed to load transcript: ${e.message}` });
    });
  }, [id, addToast]);

  const toggleSegment = (segmentId: string) => {
    setSegments((prev) =>
      prev.map((seg) => {
        if (seg.id !== segmentId) return seg;
        const newDecision =
          seg.cut_decision === "keep" || seg.cut_decision === "user_restored"
            ? "user_cut"
            : "user_restored";
        api.updateSegment(id, segmentId, { cut_decision: newDecision }).catch((e) => {
          addToast({ type: "error", message: `Failed to update segment: ${e.message}` });
        });
        return { ...seg, cut_decision: newDecision as TranscriptSegment["cut_decision"] };
      })
    );
  };

  const resetAll = () => {
    setSegments((prev) =>
      prev.map((seg) => {
        if (seg.cut_decision === "user_cut") {
          api.updateSegment(id, seg.id, { cut_decision: "keep" });
          return { ...seg, cut_decision: "keep" };
        }
        if (seg.cut_decision === "user_restored") {
          api.updateSegment(id, seg.id, { cut_decision: "cut" });
          return { ...seg, cut_decision: "cut" };
        }
        return seg;
      })
    );
  };

  const skipReview = async () => {
    setRendering(true);
    try {
      await api.startRender(id);
      router.push(`/projects/${id}/export`);
    } catch (e) {
      setRendering(false);
      const error = e instanceof Error ? e.message : "Render failed";
      addToast({ type: "error", message: `Failed to start render: ${error}` });
    }
  };

  const finishReview = async () => {
    setRendering(true);
    try {
      await api.startRender(id);
      router.push(`/projects/${id}/export`);
    } catch (e) {
      setRendering(false);
      const error = e instanceof Error ? e.message : "Render failed";
      addToast({ type: "error", message: `Failed to start render: ${error}` });
    }
  };

  const speakerMap = new Map(speakers.map((s) => [s.id, s]));
  const keptSegments = segments.filter((s) => s.cut_decision === "keep" || s.cut_decision === "user_restored");
  const cutSegments = segments.filter((s) => s.cut_decision === "cut" || s.cut_decision === "user_cut");
  const keptCount = keptSegments.length;
  const cutCount = cutSegments.length;

  // Duration calculations
  const totalDurationMs = segments.reduce((sum, s) => sum + (s.end_ms - s.start_ms), 0);
  const keptDurationMs = keptSegments.reduce((sum, s) => sum + (s.end_ms - s.start_ms), 0);
  const cutDurationMs = cutSegments.reduce((sum, s) => sum + (s.end_ms - s.start_ms), 0);
  const percentRemoved = totalDurationMs > 0
    ? Math.round((cutDurationMs / totalDurationMs) * 100)
    : 0;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Loading transcript...
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800 px-8 py-4 sticky top-0 bg-gray-950 z-10">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <Link href={`/projects/${id}`} className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm">
            <ArrowLeft size={16} /> Back to project
          </Link>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={skipReview} loading={rendering}>
              <SkipForward size={16} className="mr-1.5" /> Skip Review
            </Button>
            <Button onClick={finishReview} loading={rendering}>
              Looks Good <ArrowRight size={16} className="ml-1.5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-8 py-8">
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-100 mb-2">Review Your Edit</h2>
          <p className="text-sm text-gray-500 mb-4">
            Click any text to remove or restore it. Strikethrough text will be cut from the final video.
            You can skip this step if you trust the AI decisions.
          </p>

          {/* Summary banner */}
          {segments.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-4">
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Original</p>
                  <p className="text-sm font-medium text-gray-200">{formatDuration(totalDurationMs)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">After cuts</p>
                  <p className="text-sm font-medium text-green-400">{formatDuration(keptDurationMs)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Removed</p>
                  <p className="text-sm font-medium text-red-400">{formatDuration(cutDurationMs)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">% removed</p>
                  <p className="text-sm font-medium text-yellow-400">{percentRemoved}%</p>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center gap-4 text-sm">
            <span className="text-green-400">{keptCount} segments kept</span>
            <span className="text-red-400">{cutCount} segments cut</span>
            <button onClick={resetAll} className="flex items-center gap-1 text-gray-500 hover:text-gray-300 ml-auto">
              <RotateCcw size={14} /> Reset all changes
            </button>
          </div>
        </div>

        <div className="space-y-1">
          {segments.map((segment) => {
            const isCut = segment.cut_decision === "cut" || segment.cut_decision === "user_cut";
            const isUserModified = segment.cut_decision === "user_cut" || segment.cut_decision === "user_restored";
            const speaker = segment.speaker_id ? speakerMap.get(segment.speaker_id) : undefined;

            return (
              <div
                key={segment.id}
                onClick={() => toggleSegment(segment.id)}
                className={`group flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all
                  ${isCut ? "bg-red-500/5 hover:bg-red-500/10" : "hover:bg-gray-800/50"}
                  ${isUserModified ? "border border-dashed border-yellow-600/30" : "border border-transparent"}`}
              >
                <div className="w-16 shrink-0 pt-0.5">
                  <p className="text-xs text-gray-600">{formatTime(segment.start_ms)}</p>
                </div>

                {speaker && (
                  <div className="shrink-0 pt-0.5">
                    <SpeakerLabel label={speaker.label} color={speaker.color} />
                  </div>
                )}

                <div className="flex-1 min-w-0">
                  <p className={`text-sm leading-relaxed ${isCut ? "line-through text-gray-600" : "text-gray-200"}`}>
                    {segment.text}
                  </p>
                  {segment.cut_reason && (
                    <p className="text-xs text-gray-600 mt-1">
                      {segment.segment_type === "filler" && "Filler: "}
                      {segment.segment_type === "silence" && "Silence: "}
                      {segment.segment_type === "repeated_take" && "Repeated: "}
                      {segment.cut_reason}
                    </p>
                  )}
                </div>

                <div className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity pt-0.5">
                  {isCut ? (
                    <EyeOff size={16} className="text-red-400" />
                  ) : (
                    <Eye size={16} className="text-green-400" />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-10 flex items-center justify-between border-t border-gray-800 pt-6">
          <Button variant="ghost" onClick={skipReview} loading={rendering}>
            <SkipForward size={16} className="mr-1.5" /> Skip & Render
          </Button>
          <Button onClick={finishReview} size="lg" loading={rendering}>
            Approve & Render <ArrowRight size={16} className="ml-1.5" />
          </Button>
        </div>
      </main>
    </div>
  );
}
