import type { Project, Clip, TranscriptSegment, ProcessingJob, VideoExport } from "./types";

const BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error ${res.status}: ${error}`);
  }
  return res.json();
}

export const api = {
  // Projects
  createProject: (data: { name: string; description?: string }) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify(data) }),
  getProjects: () => request<Project[]>("/projects"),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  updateProject: (id: string, data: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),

  // Clips
  uploadClips: async (projectId: string, files: File[]): Promise<Clip[]> => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    const res = await fetch(`${BASE}/projects/${projectId}/clips`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },
  getClips: (projectId: string) =>
    request<Clip[]>(`/projects/${projectId}/clips`),
  reorderClips: (projectId: string, order: { id: string; sequence_order: number }[]) =>
    request<void>(`/projects/${projectId}/clips/reorder`, {
      method: "PATCH",
      body: JSON.stringify({ clips: order }),
    }),
  deleteClip: (projectId: string, clipId: string) =>
    request<void>(`/projects/${projectId}/clips/${clipId}`, { method: "DELETE" }),

  // Transcripts
  getTranscript: (projectId: string) =>
    request<TranscriptSegment[]>(`/projects/${projectId}/transcript`),
  updateSegment: (segmentId: string, data: { cut_decision: string }) =>
    request<TranscriptSegment>(`/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  bulkUpdateSegments: (updates: { id: string; cut_decision: string }[]) =>
    request<void>("/segments/bulk", { method: "PATCH", body: JSON.stringify({ segments: updates }) }),

  // Processing
  startProcessing: (projectId: string) =>
    request<ProcessingJob>(`/projects/${projectId}/process`, { method: "POST" }),
  getProcessingStatus: (projectId: string) =>
    request<ProcessingJob>(`/projects/${projectId}/status`),
  subscribeToProgress: (projectId: string): EventSource =>
    new EventSource(`${BASE}/projects/${projectId}/status/stream`),

  // Export
  startRender: (projectId: string) =>
    request<ProcessingJob>(`/projects/${projectId}/render`, { method: "POST" }),
  getExports: (projectId: string) =>
    request<VideoExport[]>(`/projects/${projectId}/exports`),
  getExportDownloadUrl: (exportId: string) => `${BASE}/exports/${exportId}/download`,
};
