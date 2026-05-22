import { create } from "zustand";
import type { Project } from "@/lib/types";
import { api } from "@/lib/api-client";

interface ProjectStore {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (data: { name: string; description?: string }) => Promise<Project>;
  updateProject: (id: string, data: Partial<Project>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await api.getProjects();
      set({ projects, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchProject: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const project = await api.getProject(id);
      set({ currentProject: project, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  createProject: async (data) => {
    const project = await api.createProject(data);
    set((state) => ({ projects: [...state.projects, project] }));
    return project;
  },

  updateProject: async (id, data) => {
    const updated = await api.updateProject(id, data);
    set((state) => ({
      projects: state.projects.map((p) => (p.id === id ? updated : p)),
      currentProject: state.currentProject?.id === id ? updated : state.currentProject,
    }));
  },

  deleteProject: async (id) => {
    await api.deleteProject(id);
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== id),
      currentProject: state.currentProject?.id === id ? null : state.currentProject,
    }));
  },
}));
