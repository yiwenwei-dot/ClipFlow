"use client";

import { useState, useCallback, DragEvent, useRef } from "react";
import { Upload } from "lucide-react";

const ACCEPTED_TYPES = ["video/mp4", "video/quicktime", "video/webm", "video/x-matroska", "video/avi"];
const ACCEPTED_EXT = [".mp4", ".mov", ".webm", ".mkv", ".avi"];

interface DropZoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export function DropZone({ onFilesSelected, disabled }: DropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFiles = (files: FileList | File[]): File[] => {
    return Array.from(files).filter(
      (f) => ACCEPTED_TYPES.includes(f.type) || ACCEPTED_EXT.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
  };

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragging(false);
      if (disabled) return;
      const valid = validateFiles(e.dataTransfer.files);
      if (valid.length) onFilesSelected(valid);
    },
    [onFilesSelected, disabled]
  );

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
        ${dragging ? "border-blue-500 bg-blue-500/10" : "border-gray-700 hover:border-gray-600 bg-gray-900/50"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <Upload className="mx-auto mb-4 text-gray-500" size={48} />
      <p className="text-lg font-medium text-gray-300 mb-1">Drag & drop video files here</p>
      <p className="text-sm text-gray-500">or click to browse</p>
      <p className="text-xs text-gray-600 mt-2">Supports MP4, MOV, WebM, MKV, AVI</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="video/*"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) {
            const valid = validateFiles(e.target.files);
            if (valid.length) onFilesSelected(valid);
          }
        }}
      />
    </div>
  );
}
