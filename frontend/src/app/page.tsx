"use client";

import { useState, useEffect } from "react";
import { Plus, Scissors, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { useProjectStore } from "@/stores/project-store";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();
  const { projects, loading, fetchProjects, createProject } = useProjectStore();
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      const project = await createProject({ name: name.trim(), description: description.trim() || undefined });
      setShowModal(false);
      setName("");
      setDescription("");
      router.push(`/projects/${project.id}/upload`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-800 px-8 py-5">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Scissors className="text-blue-500" size={28} />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              ClipFlow
            </h1>
          </div>
          <Button onClick={() => setShowModal(true)}>
            <Plus size={18} className="mr-1.5" /> New Project
          </Button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-10">
        {loading ? (
          <div className="text-center py-20 text-gray-500">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="text-center py-20 space-y-4">
            <FolderOpen size={64} className="mx-auto text-gray-800" />
            <h2 className="text-xl font-medium text-gray-400">No projects yet</h2>
            <p className="text-sm text-gray-600">Create your first project to start editing</p>
            <Button onClick={() => setShowModal(true)}>
              <Plus size={18} className="mr-1.5" /> Create Project
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <div
                key={project.id}
                onClick={() => router.push(`/projects/${project.id}`)}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 cursor-pointer hover:border-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-base font-medium text-gray-100 truncate">{project.name}</h3>
                  <Badge status={project.status} />
                </div>
                {project.description && (
                  <p className="text-sm text-gray-500 mb-3 line-clamp-2">{project.description}</p>
                )}
                <p className="text-xs text-gray-600">
                  {new Date(project.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>

      <Modal open={showModal} onClose={() => setShowModal(false)} title="New Project">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Project Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Video Project"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Description (optional)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What's this project about?"
              rows={3}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={creating} disabled={!name.trim()}>Create Project</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
