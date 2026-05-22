"use client";

import { useState, useEffect, use } from "react";
import { ArrowLeft, Download, CheckCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Spinner } from "@/components/ui/Spinner";
import type { VideoExport } from "@/lib/types";
import { api } from "@/lib/api-client";

function formatSize(bytes: number | null): string {
  if (!bytes) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function formatDuration(ms: number | null): string {
  if (!ms) return "";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

export default function ExportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [exports, setExports] = useState<VideoExport[]>([]);
  const [rendering, setRendering] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    api.getExports(id).then(setExports).catch(() => {});

    const status = api.getProcessingStatus(id).then((job) => {
      if (job.status === "running" && job.job_type === "render") {
        setRendering(true);
        setProgress(job.progress_pct);
      }
    }).catch(() => {});
  }, [id]);

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800 px-8 py-4">
        <div className="max-w-4xl mx-auto">
          <Link href={`/projects/${id}`} className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm">
            <ArrowLeft size={16} /> Back to project
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-10">
        <h2 className="text-xl font-semibold text-gray-100 mb-6">Export</h2>

        {rendering && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8 text-center space-y-4">
            <Spinner size={32} className="mx-auto" />
            <p className="text-gray-300">Rendering your final video...</p>
            <ProgressBar value={progress} />
            <p className="text-xs text-gray-500">{progress}% complete</p>
          </div>
        )}

        {exports.length > 0 ? (
          <div className="space-y-4">
            {exports.map((exp) => (
              <div key={exp.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle size={20} className="text-green-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-200">
                      {exp.format.toUpperCase()} {exp.resolution && `· ${exp.resolution}`}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatDuration(exp.duration_ms)} · {formatSize(exp.file_size_bytes)}
                    </p>
                  </div>
                </div>
                <a href={api.getExportDownloadUrl(exp.id)} download>
                  <Button variant="secondary" size="sm">
                    <Download size={16} className="mr-1.5" /> Download
                  </Button>
                </a>
              </div>
            ))}
          </div>
        ) : !rendering ? (
          <div className="text-center py-16 text-gray-500 space-y-2">
            <p>No exports yet</p>
            <p className="text-xs text-gray-600">Go to Review to approve your edit and start rendering</p>
          </div>
        ) : null}
      </main>
    </div>
  );
}
