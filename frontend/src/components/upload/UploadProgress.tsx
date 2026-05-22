"use client";

import { CheckCircle, AlertCircle, Loader } from "lucide-react";
import { ProgressBar } from "@/components/ui/ProgressBar";

export interface FileUploadStatus {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

interface UploadProgressProps {
  files: FileUploadStatus[];
}

export function UploadProgress({ files }: UploadProgressProps) {
  if (files.length === 0) return null;

  const completedCount = files.filter((f) => f.status === "done").length;
  const errorCount = files.filter((f) => f.status === "error").length;
  const totalProgress =
    files.length > 0
      ? Math.round(files.reduce((sum, f) => sum + f.progress, 0) / files.length)
      : 0;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-200">
          Uploading {files.length} {files.length === 1 ? "file" : "files"}
        </h4>
        <span className="text-xs text-gray-500">
          {completedCount}/{files.length} complete
          {errorCount > 0 && ` (${errorCount} failed)`}
        </span>
      </div>

      <ProgressBar value={totalProgress} />

      <div className="space-y-2 max-h-48 overflow-y-auto">
        {files.map((fileStatus, index) => (
          <div key={index} className="flex items-center gap-3">
            <div className="shrink-0">
              {fileStatus.status === "done" && (
                <CheckCircle size={16} className="text-green-500" />
              )}
              {fileStatus.status === "error" && (
                <AlertCircle size={16} className="text-red-500" />
              )}
              {fileStatus.status === "uploading" && (
                <Loader size={16} className="text-blue-500 animate-spin" />
              )}
              {fileStatus.status === "pending" && (
                <div className="w-4 h-4 rounded-full border-2 border-gray-700" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-300 truncate">
                {fileStatus.file.name}
              </p>
              {fileStatus.status === "uploading" && (
                <div className="mt-1">
                  <ProgressBar value={fileStatus.progress} className="h-1" />
                </div>
              )}
              {fileStatus.status === "error" && fileStatus.error && (
                <p className="text-xs text-red-400 mt-0.5">{fileStatus.error}</p>
              )}
            </div>
            <span className="text-xs text-gray-600 shrink-0">
              {fileStatus.status === "uploading" && `${fileStatus.progress}%`}
              {fileStatus.status === "done" && "Done"}
              {fileStatus.status === "error" && "Failed"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
