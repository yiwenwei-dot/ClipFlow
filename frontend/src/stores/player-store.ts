import { create } from "zustand";

interface PlayerStore {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  activeSegmentId: string | null;
  activeClipId: string | null;
  volume: number;
  previewMode: boolean;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  setActiveSegment: (id: string | null) => void;
  setActiveClip: (id: string | null) => void;
  setVolume: (volume: number) => void;
  togglePreviewMode: () => void;
}

export const usePlayerStore = create<PlayerStore>((set) => ({
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  activeSegmentId: null,
  activeClipId: null,
  volume: 1,
  previewMode: false,

  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),
  seek: (time) => set({ currentTime: time }),
  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setActiveSegment: (id) => set({ activeSegmentId: id }),
  setActiveClip: (id) => set({ activeClipId: id }),
  setVolume: (volume) => set({ volume }),
  togglePreviewMode: () => set((state) => ({ previewMode: !state.previewMode })),
}));
