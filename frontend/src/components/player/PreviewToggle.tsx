"use client";

import { usePlayerStore } from "@/stores/player-store";

export function PreviewToggle() {
  const { previewMode, togglePreviewMode } = usePlayerStore();

  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={`${!previewMode ? "text-gray-200" : "text-gray-500"}`}>Original</span>
      <button
        onClick={togglePreviewMode}
        className={`relative w-10 h-5 rounded-full transition-colors ${previewMode ? "bg-blue-600" : "bg-gray-700"}`}
      >
        <span
          className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${previewMode ? "translate-x-5" : "translate-x-0.5"}`}
        />
      </button>
      <span className={`${previewMode ? "text-gray-200" : "text-gray-500"}`}>Edited</span>
    </div>
  );
}
