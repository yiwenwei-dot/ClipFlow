"use client";

import { useState, useEffect, useCallback, use } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { DropZone } from "@/components/upload/DropZone";
import { SequenceList } from "@/components/upload/SequenceList";
import { UploadProgress, type FileUploadStatus } from "@/components/upload/UploadProgress";
import type { Clip } from "@/lib/types";
import { api } from "@/lib/api-client";
import { useToastStore } from "@/stores/toast-store";

export default function UploadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const addToast = useToastStore((s) => s.addToast);
  const [clips, setClips] = useState<Clip[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadFiles, setUploadFiles] = useState<FileUploadStatus[]>([]);

  useEffect(() => {
    api.getClips(id).then(setClips).catch((e) => {
      addToast({ type: "error", message: `Failed to load clips: ${e.message}` });
    });
  }, [id, addToast]);

  const handleFilesSelected = useCallback(async (files: File[]) => {
    setUploading(true);

    const fileStatuses: FileUploadStatus[] = files.map((file) => ({
      file,
      progress: 0,
      status: "pending" as const,
    }));
    setUploadFiles(fileStatuses);

    const uploaded: Clip[] = [];

    for (let i = 0; i < files.length; i++) {
      // Mark as uploading
      setUploadFiles((prev) =>
        prev.map((f, idx) =>
          idx === i ? { ...f, status: "uploading" as const } : f
        )
      );

      try {
        const clip = await api.uploadClip(id, files[i], (event) => {
          setUploadFiles((prev) =>
            prev.map((f, idx) =>
              idx === i ? { ...f, progress: event.percent } : f
            )
          );
        });

        uploaded.push(clip);
        setUploadFiles((prev) =>
          prev.map((f, idx) =>
            idx === i ? { ...f, status: "done" as const, progress: 100 } : f
          )
        );
        // Add clip to list immediately
        setClips((prev) => [...prev, clip]);
      } catch (e) {
        const error = e instanceof Error ? e.message : "Upload failed";
        setUploadFiles((prev) =>
          prev.map((f, idx) =>
            idx === i ? { ...f, status: "error" as const, error } : f
          )
        );
        addToast({ type: "error", message: `Failed to upload ${files[i].name}: ${error}` });
      }
    }

    setUploading(false);

    // Clear upload progress after a delay
    setTimeout(() => {
      setUploadFiles([]);
    }, 3000);
  }, [id, addToast]);

  const handleReorder = (reordered: Clip[]) => {
    setClips(reordered);
    const order = reordered.map((c, i) => ({ id: c.id, sequence_order: i }));
    api.reorderClips(id, order).catch((e) => {
      addToast({ type: "error", message: `Failed to reorder: ${e.message}` });
    });
  };

  const handleDelete = (clipId: string) => {
    setClips((prev) => prev.filter((c) => c.id !== clipId));
    api.deleteClip(id, clipId).catch((e) => {
      addToast({ type: "error", message: `Failed to delete clip: ${e.message}` });
    });
  };

  const handleProcess = async () => {
    try {
      await api.startProcessing(id);
      router.push(`/projects/${id}`);
    } catch (e) {
      const error = e instanceof Error ? e.message : "Processing failed";
      addToast({ type: "error", message: `Failed to start processing: ${error}` });
    }
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800 px-8 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link href={`/projects/${id}`} className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm">
            <ArrowLeft size={16} /> Back to project
          </Link>
          <Button onClick={handleProcess} disabled={clips.length === 0 || uploading}>
            Start Processing <ArrowRight size={16} className="ml-1.5" />
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-10 space-y-8">
        <div>
          <h2 className="text-xl font-semibold text-gray-100 mb-2">Upload Clips</h2>
          <p className="text-sm text-gray-500 mb-4">Add your video clips, then drag to set the order</p>
          <DropZone onFilesSelected={handleFilesSelected} disabled={uploading} />
        </div>

        {uploadFiles.length > 0 && (
          <UploadProgress files={uploadFiles} />
        )}

        {clips.length > 0 && (
          <div>
            <h3 className="text-base font-medium text-gray-200 mb-3">
              Clip Sequence ({clips.length} {clips.length === 1 ? "clip" : "clips"})
            </h3>
            <SequenceList clips={clips} onReorder={handleReorder} onDelete={handleDelete} />
          </div>
        )}
      </main>
    </div>
  );
}
