import axios, { AxiosError, AxiosInstance } from "axios";
import toast from "react-hot-toast";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { "Content-Type": "application/json" },
  withCredentials: false,
  timeout: 60_000,
});

apiClient.interceptors.request.use((cfg) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("hackroot_token");
    if (token) cfg.headers.Authorization = `Bearer ${token}`;
  }
  return cfg;
});

apiClient.interceptors.response.use(
  (r) => r,
  (err: AxiosError<any>) => {
    const status = err.response?.status;
    const detail =
      err.response?.data?.detail || err.message || "Request failed";
    if (status === 401 && typeof window !== "undefined") {
      window.localStorage.removeItem("hackroot_token");
      if (!window.location.pathname.startsWith("/login") &&
          !window.location.pathname.startsWith("/register")) {
        window.location.href = "/login";
      }
    } else if (status && status >= 500) {
      toast.error(`Server error: ${String(detail).slice(0, 120)}`);
    } else if (status && status >= 400 && status !== 401) {
      toast.error(String(detail).slice(0, 200));
    }
    return Promise.reject(err);
  }
);

export type User = { id: number; email: string; full_name: string | null; is_active: boolean; is_superuser: boolean; credits_total: number; credits_used: number; created_at: string; };
export type Token = { access_token: string; token_type: string; user: User };
export type VideoSummary = { id: number; title: string; duration: number; aspect_ratio: string; status: string; thumbnail_path: string | null; created_at: string; };
export type Scene = { id: number; scene_number: number; duration: number; visual_prompt: string; voiceover: string | null; caption: string | null; camera_movement: string | null; transition: string | null; music_intensity: string | null; image_path: string | null; video_clip_path: string | null; };
export type Video = { id: number; owner_id: number; title: string; prompt: string; duration: number; aspect_ratio: string; language: string; style: string; voice: string; output_path: string | null; thumbnail_path: string | null; resolution: string | null; file_size_bytes: number | null; created_at: string; updated_at: string; scenes: Scene[]; };
export type JobStatus = { id: number; video_id: number; status: "draft" | "queued" | "processing" | "completed" | "failed" | "cancelled"; current_step: string | null; progress: number; error_message: string | null; started_at: string | null; completed_at: string | null; created_at: string; };
export type DashboardStats = { total_videos: number; videos_generated: number; processing: number; failed_jobs: number; credits_total: number; credits_used: number; credits_remaining: number; };
export type BrandKit = { id: number; name: string; brand_voice: string | null; description: string | null; primary_color: string | null; secondary_color: string | null; accent_color: string | null; font_family: string | null; logo_path: string | null; website: string | null; social_links: string | null; is_default: boolean; created_at: string; updated_at: string; };
export type Template = { id: number; slug: string; name: string; description: string | null; category: string; icon: string | null; preview_url: string | null; default_duration: number; default_aspect_ratio: string; default_style: string; default_voice: string; default_language: string; scene_count: number; scene_blueprint: string; cta_template: string | null; caption_style: string | null; is_active: boolean; is_system: boolean; };
export type Asset = { id: number; name: string; original_filename: string | null; kind: string; mime_type: string; path: string; url: string; file_size_bytes: number; width: number | null; height: number | null; duration: number | null; video_id: number | null; sort_order: number; description: string | null; created_at: string; };
export type UploadLimits = { max_file_size_bytes: number; max_file_size_mb: number; max_images_per_project: number; allowed_mime_types: string[]; allowed_extensions: string[]; compression: string; };
export type Agent = { id: string; name: string; role: string; status: string; description: string; };
export type ProviderInfo = { role: string; provider: string; model: string | null; available: boolean; requires_key: boolean; message: string | null; };

export const api = {
  auth: {
    login: async (data: any): Promise<Token> => (await apiClient.post("/auth/login", data)).data,
    register: async (data: any): Promise<Token> => (await apiClient.post("/auth/register", data)).data,
    me: async (): Promise<User> => (await apiClient.get("/auth/me")).data,
  },
  videos: {
    create: async (data: any): Promise<Video> => (await apiClient.post("/videos", data)).data,
    generate: async (id: number, data: any): Promise<JobStatus> =>
      (await apiClient.post(`/videos/${id}/generate`, data)).data,
    get: async (id: number): Promise<Video> => (await apiClient.get(`/videos/${id}`)).data,
    getStatus: async (id: number): Promise<JobStatus> => (await apiClient.get(`/videos/${id}/status`)).data,
    getStats: async (): Promise<DashboardStats> => (await apiClient.get("/videos/_stats")).data,
    listVideos: async (limit: number = 12, offset: number = 0): Promise<VideoSummary[]> =>
      (await apiClient.get(`/videos?limit=${limit}&offset=${offset}`)).data,
    rename: async (id: number, title: string) =>
      (await apiClient.patch(`/videos/${id}/rename`, { title })).data,
    duplicate: async (id: number): Promise<Video> => (await apiClient.post(`/videos/${id}/duplicate`)).data,
    remove: async (id: number): Promise<void> => { await apiClient.delete(`/videos/${id}`); },
    downloadUrl: (id: number) => `${API_BASE}/api/v1/videos/${id}/download`,
    thumbnailUrl: (id: number) => `${API_BASE}/api/v1/videos/${id}/thumbnail`,
  },
  assets: {
    limits: async (): Promise<UploadLimits> => (await apiClient.get("/assets/_limits")).data,
    list: async (params: { video_id?: number; kind?: string } = {}): Promise<Asset[]> => {
      const q = new URLSearchParams();
      if (params.video_id !== undefined) q.set("video_id", String(params.video_id));
      if (params.kind) q.set("kind", params.kind);
      const qs = q.toString();
      return (await apiClient.get(`/assets${qs ? `?${qs}` : ""}`)).data;
    },
    upload: async (
      file: File,
      opts: { videoId?: number; description?: string; kind?: string; onProgress?: (pct: number) => void } = {}
    ): Promise<Asset> => {
      const fd = new FormData();
      fd.append("file", file);
      if (opts.videoId !== undefined) fd.append("video_id", String(opts.videoId));
      if (opts.description) fd.append("description", opts.description);
      fd.append("kind", opts.kind ?? "image");
      const res = await apiClient.post("/assets/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
        onUploadProgress: (e) => {
          if (opts.onProgress && e.total) opts.onProgress(Math.round((e.loaded / e.total) * 100));
        },
      });
      return res.data;
    },
    reorder: async (assetIds: number[]): Promise<Asset[]> =>
      (await apiClient.post("/assets/reorder", { asset_ids: assetIds })).data,
    update: async (id: number, data: { description?: string | null; video_id?: number | null }): Promise<Asset> =>
      (await apiClient.patch(`/assets/${id}`, data)).data,
    remove: async (id: number): Promise<void> => { await apiClient.delete(`/assets/${id}`); },
    previewUrl: (id: number) => `${API_BASE}/api/v1/assets/${id}/preview`,
  },
  brandKits: {
    list: async (): Promise<BrandKit[]> => (await apiClient.get("/brand-kit")).data,
    create: async (data: any): Promise<BrandKit> => (await apiClient.post("/brand-kit", data)).data,
    update: async (id: number, data: any): Promise<BrandKit> => (await apiClient.put(`/brand-kit/${id}`, data)).data,
    remove: async (id: number): Promise<void> => { await apiClient.delete(`/brand-kit/${id}`); },
    uploadLogo: async (id: number, file: File): Promise<BrandKit> => {
      const fd = new FormData();
      fd.append("file", file);
      const res = await apiClient.post(`/brand-kit/${id}/logo`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
      });
      return res.data;
    },
  },
  templates: {
    list: async (): Promise<Template[]> => (await apiClient.get("/templates")).data,
    create: async (data: any): Promise<Template> => (await apiClient.post("/templates", data)).data,
  },
  providers: {
    list: async (): Promise<ProviderInfo[]> => (await apiClient.get("/providers")).data,
  },
  settings: {
    get: async (): Promise<any> => (await apiClient.get("/settings")).data,
  },
  agents: {
    list: async (): Promise<Agent[]> => (await apiClient.get("/agents")).data,
  },
  billing: {
    plans: async (): Promise<any[]> => (await apiClient.get("/billing/plans")).data,
    current: async (): Promise<any> => (await apiClient.get("/billing/current")).data,
    checkout: async (plan_slug: string, billing_cycle: string): Promise<any> =>
      (await apiClient.post("/billing/checkout", { plan_slug, billing_cycle })).data,
    verify: async (payload: any): Promise<any> => (await apiClient.post("/billing/verify", payload)).data,
    cancel: async (): Promise<any> => (await apiClient.post("/billing/cancel")).data,
    renew: async (): Promise<any> => (await apiClient.post("/billing/renew")).data,
    change: async (plan_slug: string, billing_cycle = "monthly"): Promise<any> =>
      (await apiClient.post(`/billing/change?plan_slug=${plan_slug}&billing_cycle=${billing_cycle}`)).data,
    invoices: async (): Promise<any[]> => (await apiClient.get("/billing/invoices")).data,
    creditHistory: async (): Promise<any[]> => (await apiClient.get("/billing/credits/history")).data,
    notifications: async (): Promise<any[]> => (await apiClient.get("/billing/notifications")).data,
    unreadCount: async (): Promise<number> =>
      (await apiClient.get("/billing/notifications/unread-count")).data.unread,
    markRead: async (id: number): Promise<void> => { await apiClient.post(`/billing/notifications/${id}/read`); },
    markAllRead: async (): Promise<void> => { await apiClient.post("/billing/notifications/read-all"); },
  },
  admin: {
    stats: async (): Promise<any> => (await apiClient.get("/admin/stats")).data,
    users: async (q?: string): Promise<any[]> =>
      (await apiClient.get("/admin/users" + (q ? `?q=${encodeURIComponent(q)}` : ""))).data,
    adjustCredits: async (uid: number, amount: number, note?: string): Promise<any> =>
      (await apiClient.post(`/admin/users/${uid}/credits?amount=${amount}` + (note ? `&note=${encodeURIComponent(note)}` : ""))).data,
    subscriptions: async (): Promise<any[]> => (await apiClient.get("/admin/subscriptions")).data,
    plans: async (): Promise<any[]> => (await apiClient.get("/admin/plans")).data,
    togglePlan: async (pid: number, is_active: boolean): Promise<any> =>
      (await apiClient.patch(`/admin/plans/${pid}`, { is_active })).data,
    invoices: async (): Promise<any[]> => (await apiClient.get("/admin/invoices")).data,
    templates: async (): Promise<any[]> => (await apiClient.get("/admin/templates")).data,
    brandKits: async (): Promise<any[]> => (await apiClient.get("/admin/brand-kits")).data,
    videos: async (): Promise<any[]> => (await apiClient.get("/admin/videos")).data,
    requestLogs: async (): Promise<any[]> => (await apiClient.get("/admin/logs/requests")).data,
    auditLogs: async (): Promise<any[]> => (await apiClient.get("/admin/audit-logs")).data,
    analytics: async (): Promise<any> => (await apiClient.get("/admin/analytics")).data,
  },
  apiKeys: {
    list: async (): Promise<any[]> => (await apiClient.get("/api-keys")).data,
    create: async (data: any): Promise<any> => (await apiClient.post("/api-keys", data)).data,
  },
  team: {
    members: async (): Promise<any[]> => (await apiClient.get("/team/members")).data,
    invite: async (email: string, role: string): Promise<any> =>
      (await apiClient.post("/team/invite", null, { params: { email, role } })).data,
    remove: async (id: number): Promise<void> => { await apiClient.delete(`/team/members/${id}`); },
  },
};

export const mediaUrl = (path: string | null | undefined): string | null => {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  const fname = path.split(/[\\/]/).slice(-2).join("/");
  return `${API_BASE}/media/${fname}`;
};

export const formatBytes = (bytes: number | null | undefined): string => {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};
