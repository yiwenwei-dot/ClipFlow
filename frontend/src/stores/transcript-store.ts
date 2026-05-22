import { create } from "zustand";
import type { TranscriptSegment, Speaker } from "@/lib/types";
import { api } from "@/lib/api-client";

interface TranscriptStore {
  segments: TranscriptSegment[];
  speakers: Speaker[];
  loading: boolean;
  fetchTranscript: (projectId: string) => Promise<void>;
  toggleSegmentCut: (segmentId: string) => void;
  updateSegment: (segmentId: string, cutDecision: string) => Promise<void>;
  setSpeakers: (speakers: Speaker[]) => void;
}

export const useTranscriptStore = create<TranscriptStore>((set, get) => ({
  segments: [],
  speakers: [],
  loading: false,

  fetchTranscript: async (projectId: string) => {
    set({ loading: true });
    try {
      const segments = await api.getTranscript(projectId);
      set({ segments, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  toggleSegmentCut: (segmentId: string) => {
    const segments = get().segments.map((seg) => {
      if (seg.id !== segmentId) return seg;
      const newDecision =
        seg.cut_decision === "keep" || seg.cut_decision === "user_restored"
          ? "user_cut"
          : "user_restored";
      return { ...seg, cut_decision: newDecision as TranscriptSegment["cut_decision"] };
    });
    set({ segments });
    const segment = segments.find((s) => s.id === segmentId);
    if (segment) {
      api.updateSegment(segmentId, { cut_decision: segment.cut_decision });
    }
  },

  updateSegment: async (segmentId: string, cutDecision: string) => {
    set((state) => ({
      segments: state.segments.map((seg) =>
        seg.id === segmentId
          ? { ...seg, cut_decision: cutDecision as TranscriptSegment["cut_decision"] }
          : seg
      ),
    }));
    await api.updateSegment(segmentId, { cut_decision: cutDecision });
  },

  setSpeakers: (speakers) => set({ speakers }),
}));
