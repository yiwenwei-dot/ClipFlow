"use client";

import { useEffect, useState, useCallback, useRef, use } from "react";
import { ArrowLeft, Upload, Settings, RefreshCw, Plus, X } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { VideoPlayer } from "@/components/player/VideoPlayer";
import { PreviewToggle } from "@/components/player/PreviewToggle";
import { TranscriptView } from "@/components/transcript/TranscriptView";
import { ProcessingOverlay } from "@/components/status/ProcessingOverlay";
import { useProjectStore } from "@/stores/project-store";
import { useTranscriptStore } from "@/stores/transcript-store";
import { usePlayerStore } from "@/stores/player-store";
import { useToastStore } from "@/stores/toast-store";
import { api } from "@/lib/api-client";
import type { ProcessingStatusEvent } from "@/lib/api-client";
import type { Clip } from "@/lib/types";

function mapJobTypeToStep(status: string, jobType?: string): number {
  if (status === "completed") return 3;
  if (jobType === "analyze") return 2;
  if (jobType === "transcribe") return 1;
  return 0;
}

function stepMessage(step: number, progress: number): string {
  const messages: Record<number, string> = {
    0: "Preparing...",
    1: `Transcribing audio... ${progress}%`,
    2: `Analyzing content... ${progress}%`,
    3: "Processing complete!",
  };
  return messages[step] || `Processing... ${progress}%`;
}

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { currentProject, fetchProject, updateProject } = useProjectStore();
  const { segments, speakers, fetchTranscript, toggleSegmentCut } = useTranscriptStore();
  const currentTime = usePlayerStore((s) => s.currentTime);
  const activeClipId = usePlayerStore((s) => s.activeClipId);
  const setActiveClip = usePlayerStore((s) => s.setActiveClip);
  const setActiveSegment = usePlayerStore((s) => s.setActiveSegment);
  const seek = usePlayerStore((s) => s.seek);
  const addToast = useToastStore((s) => s.addToast);

  const [clips, setClips] = useState<Clip[]>([]);
  const [processing, setProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState("Starting...");
  const eventSourceRef = useRef<EventSource | null>(null);

  // Settings state
  const [silenceThreshold, setSilenceThreshold] = useState(500);
  const [fillerWords, setFillerWords] = useState<string[]>([]);
  const [newFillerWord, setNewFillerWord] = useState("");
  const [settingsDirty, setSettingsDirty] = useState(false);

  useEffect(() => {
    fetchProject(id);
    fetchTranscript(id);
    api.getClips(id).then((c) => {
      setClips(c);
      if (c.length > 0 && !activeClipId) {
        setActiveClip(c[0].id);
      }
    }).catch(() => {});
  }, [id, fetchProject, fetchTranscript, activeClipId, setActiveClip]);

  // Sync settings from project
  useEffect(() => {
    if (currentProject) {
      setSilenceThreshold(currentProject.silence_threshold_ms);
      setFillerWords(currentProject.filler_words || []);
    }
  }, [currentProject]);

  // Check processing status and start SSE if processing
  useEffect(() => {
    if (!currentProject) return;
    if (currentProject.status !== "processing") return;

    setProcessing(true);

    const es = api.subscribeToProgress(id);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data: ProcessingStatusEvent = JSON.parse(event.data);
        setProcessingProgress(data.progress_pct);
        setProcessingStep(mapJobTypeToStep(data.status, data.job_id ? undefined : undefined));

        if (data.status === "running") {
          setProcessingMessage(`Processing... ${data.progress_pct}%`);
        }

        if (data.status === "completed") {
          setProcessing(false);
          es.close();
          // Refresh project and transcript
          fetchProject(id);
          fetchTranscript(id);
          addToast({ type: "success", message: "Processing complete!" });
        }

        if (data.status === "failed") {
          setProcessing(false);
          es.close();
          fetchProject(id);
          addToast({ type: "error", message: data.error_message || "Processing failed" });
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      // EventSource will auto-reconnect, but if it closes permanently handle it
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [currentProject?.status, id, fetchProject, fetchTranscript, addToast]);

  // Track active segment based on player time
  useEffect(() => {
    if (segments.length === 0) return;
    const activeClipSegments = segments.filter((s) => s.clip_id === activeClipId);
    const active = activeClipSegments.find(
      (seg) => currentTime * 1000 >= seg.start_ms && currentTime * 1000 < seg.end_ms
    );
    if (active) {
      setActiveSegment(active.id);
    }
  }, [currentTime, segments, activeClipId, setActiveSegment]);

  // Build video URL for current clip
  const videoSrc = activeClipId
    ? api.getClipStreamUrl(id, activeClipId)
    : null;

  const handleCancelProcessing = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setProcessing(false);
  }, []);

  // Settings handlers
  const handleSilenceChange = (value: number) => {
    setSilenceThreshold(value);
    setSettingsDirty(true);
  };

  const handleAddFillerWord = () => {
    const word = newFillerWord.trim().toLowerCase();
    if (word && !fillerWords.includes(word)) {
      setFillerWords((prev) => [...prev, word]);
      setNewFillerWord("");
      setSettingsDirty(true);
    }
  };

  const handleRemoveFillerWord = (word: string) => {
    setFillerWords((prev) => prev.filter((w) => w !== word));
    setSettingsDirty(true);
  };

  const handleSaveSettings = async () => {
    try {
      await updateProject(id, {
        silence_threshold_ms: silenceThreshold,
        filler_words: fillerWords,
      });
      setSettingsDirty(false);
      addToast({ type: "success", message: "Settings saved" });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Failed to save settings";
      addToast({ type: "error", message: error });
    }
  };

  const handleReanalyze = async () => {
    try {
      // Save settings first
      if (settingsDirty) {
        await updateProject(id, {
          silence_threshold_ms: silenceThreshold,
          filler_words: fillerWords,
        });
        setSettingsDirty(false);
      }
      await api.startAnalysis(id);
      fetchProject(id);
      addToast({ type: "info", message: "Re-analysis started" });
    } catch (e) {
      const error = e instanceof Error ? e.message : "Failed to start re-analysis";
      addToast({ type: "error", message: error });
    }
  };

  if (!currentProject) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading...</div>;
  }

  return (
    <div className="h-screen flex flex-col">
      <header className="border-b border-gray-800 px-4 py-3 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-gray-400 hover:text-gray-200">
              <ArrowLeft size={18} />
            </Link>
            <h1 className="text-base font-medium text-gray-100">{currentProject.name}</h1>
            <Badge status={currentProject.status} />
          </div>
          <div className="flex items-center gap-2">
            <PreviewToggle />
            <Link href={`/projects/${id}/upload`}>
              <Button variant="ghost" size="sm"><Upload size={16} className="mr-1.5" /> Add Clips</Button>
            </Link>
            <Link href={`/projects/${id}/review`}>
              <Button size="sm">Review & Export</Button>
            </Link>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Video Player */}
        <div className="w-[45%] p-4 border-r border-gray-800 flex flex-col">
          {/* Clip selector tabs */}
          {clips.length > 1 && (
            <div className="flex gap-1 mb-3 overflow-x-auto pb-1">
              {clips.map((clip, index) => (
                <button
                  key={clip.id}
                  onClick={() => setActiveClip(clip.id)}
                  className={`px-3 py-1 text-xs rounded-md whitespace-nowrap transition-colors ${
                    clip.id === activeClipId
                      ? "bg-blue-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  Clip {index + 1}
                </button>
              ))}
            </div>
          )}
          <VideoPlayer src={videoSrc} />
        </div>

        {/* Center: Transcript */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <h2 className="text-sm font-medium text-gray-300">Transcript</h2>
            <span className="text-xs text-gray-600">{segments.length} segments</span>
          </div>
          <div className="flex-1 overflow-hidden">
            <TranscriptView
              segments={segments}
              speakers={speakers}
              onToggleCut={toggleSegmentCut}
              onSeek={(ms) => seek(ms / 1000)}
            />
          </div>
        </div>

        {/* Right: Settings */}
        <div className="w-72 border-l border-gray-800 p-4 overflow-y-auto">
          <h3 className="text-sm font-medium text-gray-300 mb-4 flex items-center gap-2">
            <Settings size={16} /> Project Settings
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Silence Threshold</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={100}
                  max={2000}
                  step={100}
                  value={silenceThreshold}
                  onChange={(e) => handleSilenceChange(Number(e.target.value))}
                  className="flex-1 accent-blue-500"
                />
                <span className="text-xs text-gray-400 w-12 text-right">{silenceThreshold}ms</span>
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-2">Filler Words</label>
              <div className="flex flex-wrap gap-1 mb-2">
                {fillerWords.map((word) => (
                  <span
                    key={word}
                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400 group"
                  >
                    {word}
                    <button
                      onClick={() => handleRemoveFillerWord(word)}
                      className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X size={10} />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-1">
                <input
                  type="text"
                  value={newFillerWord}
                  onChange={(e) => setNewFillerWord(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAddFillerWord()}
                  placeholder="Add word..."
                  className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleAddFillerWord}
                  className="p-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-400"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>

            {settingsDirty && (
              <Button size="sm" onClick={handleSaveSettings} className="w-full">
                Save Settings
              </Button>
            )}

            <div className="pt-2 border-t border-gray-800">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleReanalyze}
                className="w-full"
              >
                <RefreshCw size={14} className="mr-1.5" /> Re-analyze
              </Button>
              <p className="text-xs text-gray-600 mt-1">
                Re-run analysis with current settings
              </p>
            </div>
          </div>
        </div>
      </div>

      {processing && (
        <ProcessingOverlay
          step={processingStep}
          progress={processingProgress}
          message={processingMessage}
          onCancel={handleCancelProcessing}
        />
      )}
    </div>
  );
}
