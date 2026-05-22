"use client";

import { useState, useEffect, useRef, use } from "react";
import { ArrowLeft, Download, CheckCircle, Edit } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Spinner } from "@/components/ui/Spinner";
import type { VideoExport } from "@/lib/types";
import { api } from "@/lib/api-client";
import { useToastStore } from "@/stores/toast-store";

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
  const addToast = useToastStore((s) => s.addToast);
  const [exports, setExports] = useState<VideoExport[]>([]);
  const [rendering, setRendering] = useState(false);
  const [progress, setProgress] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const checkRenderStatus = async () => {
    try {
      const status = await api.getProcessingStatus(id);
      const renderJob = status.jobs.find(
        (j) => j.job_type === "render" && (j.status === "queued" || j.status === "running")
      );

      if (renderJob) {
        setRendering(true);
        setProgress(renderJob.progress_pct);
      } else {
        // Rendering done or no render job
        setRendering(false);
        // Refresh exports list
        const exps = await api.getExports(id);
        setExports(exps);
        // Stop polling
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    } catch {
      // Ignore polling errors
    }
  };

  useEffect(() => {
    // Initial load
    api.getExports(id).then(setExports).catch(() => {});

    api.getProcessingStatus(id).then((status) => {
      const renderJob = status.jobs.find(
        (j) => j.job_type === "render" && (j.status === "queued" || j.status === "running")
      );
      if (renderJob) {
        setRendering(true);
        setProgress(renderJob.progress_pct);
        // Start polling
        pollRef.current = setInterval(checkRenderStatus, 3000);
      }
    }).catch(() => {});

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Start polling when rendering is detected
  useEffect(() => {
    if (rendering && !pollRef.current) {
      pollRef.current = setInterval(checkRenderStatus, 3000);
    }
    return () => {
      if (!rendering && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rendering]);

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800 px-8 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link href={`/projects/${id}`} className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm">
            <ArrowLeft size={16} /> Back to project
          </Link>
          <Link href={`/projects/${id}`}>
            <Button variant="ghost" size="sm">
              <Edit size={16} className="mr-1.5" /> Back to Editor
            </Button>
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
                <a href={api.getExportDownloadUrl(id, exp.id)} download>
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
            <Link href={`/projects/${id}/review`}>
              <Button variant="secondary" size="sm" className="mt-4">
                Go to Review
              </Button>
            </Link>
          </div>
        ) : null}
      </main>
    </div>
  );
}
