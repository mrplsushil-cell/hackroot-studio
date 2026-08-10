"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, DashboardStats, VideoSummary } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [videos, setVideos] = useState<VideoSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [s, v] = await Promise.all([
          api.videos.getStats(),
          api.videos.listVideos(12),
        ]);
        setStats(s);
        setVideos(v);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return <div className="text-ink-400">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-ink-400 mt-1">Overview of your video generation activity.</p>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard title="Total Videos" value={stats.total_videos} icon="🎬" />
          <StatCard title="Completed" value={stats.videos_generated} icon="✅" />
          <StatCard title="Processing" value={stats.processing} icon="⏳" />
          <StatCard title="Failed" value={stats.failed_jobs} icon="❌" />
          <StatCard title="Credits Used" value={`${stats.credits_used} / ${stats.credits_total}`} icon="🪙" />
        </div>
      )}

      <div className="flex justify-between items-center mt-12">
        <h2 className="text-xl font-bold">Recent Videos</h2>
        <Link href="/library" className="text-sm font-medium text-brand-400 hover:text-brand-300">
          View all &rarr;
        </Link>
      </div>

      {videos.length === 0 ? (
        <div className="card glass text-center py-12">
          <div className="text-4xl mb-4">🎥</div>
          <h3 className="text-lg font-bold mb-2">No videos yet</h3>
          <p className="text-ink-400 mb-6 max-w-md mx-auto">
            You haven't generated any videos yet. Create your first AI video to see it here.
          </p>
          <Link href="/create" className="btn-primary">
            Create Video
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {videos.map(video => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value, icon }: { title: string, value: number | string, icon: string }) {
  return (
    <div className="card glass flex items-center p-5 gap-4">
      <div className="w-12 h-12 rounded-lg bg-ink-800/80 flex items-center justify-center text-2xl border border-ink-700/50">
        {icon}
      </div>
      <div>
        <div className="text-sm font-medium text-ink-400">{title}</div>
        <div className="text-2xl font-bold text-ink-50 mt-1">{value}</div>
      </div>
    </div>
  );
}

function VideoCard({ video }: { video: VideoSummary }) {
  const isReady = video.status === "completed";
  return (
    <div className="card glass p-0 overflow-hidden flex flex-col group">
      <div className="aspect-video bg-ink-800 relative">
        {video.thumbnail_path ? (
          <img 
            src={`/api/v1/videos/${video.id}/thumbnail`} 
            alt={video.title} 
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-ink-600">
            {video.status === "processing" || video.status === "queued" ? "⏳ Processing..." : "🎬"}
          </div>
        )}
        <div className="absolute top-2 right-2">
          <span className={`text-[10px] font-bold px-2 py-1 rounded border uppercase tracking-wider
            ${video.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/20' : ''}
            ${video.status === 'failed' ? 'bg-red-500/20 text-red-400 border-red-500/20' : ''}
            ${video.status === 'processing' || video.status === 'queued' ? 'bg-brand-500/20 text-brand-400 border-brand-500/20' : ''}
            ${video.status === 'draft' ? 'bg-ink-500/20 text-ink-300 border-ink-500/20' : ''}
          `}>
            {video.status}
          </span>
        </div>
      </div>
      <div className="p-4 flex-1 flex flex-col">
        <h3 className="font-semibold text-ink-100 line-clamp-1 mb-1" title={video.title}>
          {video.title || "Untitled"}
        </h3>
        <div className="text-xs text-ink-400 flex justify-between items-center mt-auto">
          <span>{video.duration}s • {video.aspect_ratio}</span>
          <span>{new Date(video.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </div>
  );
}
