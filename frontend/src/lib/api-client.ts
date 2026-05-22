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

export interface UploadProgressEvent {
  file: File;
  loaded: number;
  total: number;
  percent: number;
}

function uploadFileWithProgress(
  url: string,
  file: File,
  onProgress?: (event: UploadProgressEvent) => void
): Promise<Clip> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress({
          file,
          loaded: e.loaded,
          total: e.total,
          percent: Math.round((e.loaded / e.total) * 100),
        });
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("Invalid JSON response"));
        }
      } else {
        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Network error during upload"));
    });

    xhr.addEventListener("abort", () => {
      reject(new Error("Upload aborted"));
    });

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}

export interface ProcessingStatusEvent {
  project_id: string;
  job_id?: string;
  status: string;
  progress_pct: number;
  error_message?: string | null;
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

  // Clips - upload one file at a time with progress
  uploadClip: (
    projectId: string,
    file: File,
    onProgress?: (event: UploadProgressEvent) => void
  ): Promise<Clip> => {
    return uploadFileWithProgress(
      `${BASE}/projects/${projectId}/clips`,
      file,
      onProgress
    );
  },

  // Upload multiple clips sequentially with progress
  uploadClips: async (
    projectId: string,
    files: File[],
    onProgress?: (event: UploadProgressEvent) => void
  ): Promise<Clip[]> => {
    const clips: Clip[] = [];
    for (const file of files) {
      const clip = await uploadFileWithProgress(
        `${BASE}/projects/${projectId}/clips`,
        file,
        onProgress
      );
      clips.push(clip);
    }
    return clips;
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
  getClipStreamUrl: (projectId: string, clipId: string) =>
    `${BASE}/projects/${projectId}/clips/${clipId}/stream`,

  // Transcripts
  getTranscript: (projectId: string) =>
    request<TranscriptSegment[]>(`/projects/${projectId}/transcript`),
  updateSegment: (projectId: string, segmentId: string, data: { cut_decision: string }) =>
    request<TranscriptSegment>(`/projects/${projectId}/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  bulkUpdateSegments: (projectId: string, segmentIds: string[], cutDecision: string) =>
    request<TranscriptSegment[]>(`/projects/${projectId}/segments`, {
      method: "PATCH",
      body: JSON.stringify({ segment_ids: segmentIds, cut_decision: cutDecision }),
    }),

  // Processing
  startProcessing: (projectId: string) =>
    request<ProcessingJob>(`/projects/${projectId}/processing/transcribe`, { method: "POST" }),
  startAnalysis: (projectId: string) =>
    request<ProcessingJob>(`/projects/${projectId}/processing/analyze`, { method: "POST" }),
  getProcessingStatus: (projectId: string) =>
    request<{ project_id: string; jobs: ProcessingJob[]; overall_status: string; overall_progress_pct: number }>(`/projects/${projectId}/processing/status`),
  subscribeToProgress: (projectId: string): EventSource =>
    new EventSource(`${BASE}/projects/${projectId}/processing/status/stream`),

  // Render / Export
  startRender: (projectId: string) =>
    request<ProcessingJob>(`/projects/${projectId}/processing/render`, { method: "POST" }),
  getExports: (projectId: string) =>
    request<VideoExport[]>(`/projects/${projectId}/exports`),
  getExportDownloadUrl: (projectId: string, exportId: string) =>
    `${BASE}/projects/${projectId}/exports/${exportId}/download`,
};
