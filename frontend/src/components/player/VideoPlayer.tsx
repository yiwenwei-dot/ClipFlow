"use client";

import { useRef, useEffect, useCallback } from "react";
import { Play, Pause, Volume2 } from "lucide-react";
import { usePlayerStore } from "@/stores/player-store";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

interface VideoPlayerProps {
  src: string | null;
}

export function VideoPlayer({ src }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { isPlaying, currentTime, volume, play, pause, setCurrentTime, setDuration, setVolume } = usePlayerStore();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (isPlaying) video.play(); else video.pause();
  }, [isPlaying]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.volume = volume;
  }, [volume]);

  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
  }, [setCurrentTime]);

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    if (videoRef.current) videoRef.current.currentTime = time;
    setCurrentTime(time);
  };

  const duration = videoRef.current?.duration || 0;

  if (!src) {
    return (
      <div className="aspect-video bg-gray-900 rounded-xl flex items-center justify-center">
        <p className="text-gray-600 text-sm">Select a clip to preview</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="relative aspect-video bg-black rounded-xl overflow-hidden">
        <video
          ref={videoRef}
          src={src}
          className="w-full h-full"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => { if (videoRef.current) setDuration(videoRef.current.duration); }}
          onEnded={pause}
        />
      </div>
      <div className="flex items-center gap-3 px-1">
        <button onClick={() => isPlaying ? pause() : play()} className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-300">
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <span className="text-xs text-gray-500 w-12">{formatTime(currentTime)}</span>
        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.1}
          value={currentTime}
          onChange={handleSeek}
          className="flex-1 h-1 accent-blue-500"
        />
        <span className="text-xs text-gray-500 w-12 text-right">{formatTime(duration)}</span>
        <div className="flex items-center gap-1">
          <Volume2 size={14} className="text-gray-500" />
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="w-16 h-1 accent-blue-500"
          />
        </div>
      </div>
    </div>
  );
}
