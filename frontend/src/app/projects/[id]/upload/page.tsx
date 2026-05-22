"use client";

import { useState, useEffect, use } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { DropZone } from "@/components/upload/DropZone";
import { SequenceList } from "@/components/upload/SequenceList";
import type { Clip } from "@/lib/types";
import { api } from "@/lib/api-client";

export default function UploadPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [clips, setClips] = useState<Clip[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    api.getClips(id).then(setClips).catch(() => {});
  }, [id]);

  const handleFilesSelected = async (files: File[]) => {
    setUploading(true);
    try {
      const uploaded = await api.uploadClips(id, files);
      setClips((prev) => [...prev, ...uploaded]);
    } finally {
      setUploading(false);
    }
  };

  const handleReorder = (reordered: Clip[]) => {
    setClips(reordered);
    const order = reordered.map((c, i) => ({ id: c.id, sequence_order: i }));
    api.reorderClips(id, order);
  };

  const handleDelete = (clipId: string) => {
    setClips((prev) => prev.filter((c) => c.id !== clipId));
    api.deleteClip(id, clipId);
  };

  const handleProcess = async () => {
    await api.startProcessing(id);
    router.push(`/projects/${id}`);
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800 px-8 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link href={`/projects/${id}`} className="flex items-center gap-2 text-gray-400 hover:text-gray-200 text-sm">
            <ArrowLeft size={16} /> Back to project
          </Link>
          <Button onClick={handleProcess} disabled={clips.length === 0}>
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
