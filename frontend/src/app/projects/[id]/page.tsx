"use client";

import { useEffect, use } from "react";
import { ArrowLeft, Upload, Settings } from "lucide-react";
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

export default function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { currentProject, fetchProject } = useProjectStore();
  const { segments, speakers, fetchTranscript, toggleSegmentCut } = useTranscriptStore();
  const currentTime = usePlayerStore((s) => s.currentTime);
  const seek = usePlayerStore((s) => s.seek);

  useEffect(() => {
    fetchProject(id);
    fetchTranscript(id);
  }, [id, fetchProject, fetchTranscript]);

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
          <VideoPlayer src={null} />
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
                  value={currentProject.silence_threshold_ms}
                  className="flex-1 accent-blue-500"
                  readOnly
                />
                <span className="text-xs text-gray-400 w-12 text-right">{currentProject.silence_threshold_ms}ms</span>
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-2">Filler Words</label>
              <div className="flex flex-wrap gap-1">
                {currentProject.filler_words?.map((word) => (
                  <span key={word} className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-400">
                    {word}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {currentProject.status === "processing" && (
        <ProcessingOverlay step={1} progress={0} message="Starting..." />
      )}
    </div>
  );
}
