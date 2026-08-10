"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import { Asset, Template, api } from "@/lib/api";
import { ImageUploader } from "@/components/upload/ImageUploader";

export default function CreateVideoPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [templateName, setTemplateName] = useState("");

  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState(20);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [language, setLanguage] = useState("English");
  const [style, setStyle] = useState("Cinematic");
  // Must match the backend Literal: "male" | "female" | "none"
  const [voice, setVoice] = useState("female");
  const [assets, setAssets] = useState<Asset[]>([]);

  // Prefill from a chosen template (?template=ID).
  useEffect(() => {
    const tid = params.get("template");
    if (!tid) return;
    (async () => {
      try {
        const t: Template = await api.templates.list().then((ts) => ts.find((x) => String(x.id) === tid) as Template);
        if (!t) return;
        setTemplateId(t.id);
        setTemplateName(t.name);
        setDuration(t.default_duration);
        setAspectRatio(t.default_aspect_ratio);
        setStyle(t.default_style);
        setVoice(t.default_voice as any);
        setLanguage(t.default_language);
        if (t.description) setPrompt((p) => p || t.description || "");
      } catch { /* ignore */ }
    })();
  }, [params]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) {
      setError("Please enter a prompt.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Images are uploaded by <ImageUploader/> as the user picks them, so by
      // this point we only need to attach their ids in the chosen order.
      const assetIds = assets.map((a) => a.id);

      const video = await api.videos.create({
        prompt,
        duration,
        aspect_ratio: aspectRatio,
        language,
        style,
        voice,
        asset_ids: assetIds,
        ...(templateId ? { template_id: templateId } : {}),
      });

      await api.videos.generate(video.id, {
        prompt,
        duration,
        aspect_ratio: aspectRatio,
        language,
        style,
        voice,
        asset_ids: assetIds,
      });

      toast.success("Generation started");
      router.push("/dashboard");
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || "Failed to create video.";
      setError(String(detail));
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div>
        <h1 className="text-3xl font-bold">Create New Video</h1>
        <p className="text-ink-400 mt-1">Describe what you want to create and our AI will do the rest.</p>
      </div>

      {templateName && (
        <div className="chip chip-active w-fit">Template: {templateName}</div>
      )}

      {error && (
        <div className="rounded-md bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400 font-medium">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="card glass p-6">
            <label className="label mb-3 block">Video Prompt</label>
            <textarea
              className="textarea min-h-[200px] resize-y text-base"
              placeholder="E.g. Create a 20-second promotional video for Oberoi Knitwears kids wear. Show attractive kids clothing, highlight sizes 18 to 26, and end with a call to order now."
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
            />
            <div className="text-right mt-2 text-xs text-ink-400">
              {prompt.length} characters
            </div>
          </div>

          <div className="card glass p-6">
            <h3 className="text-lg font-bold mb-4">Product Images</h3>
            <p className="text-sm text-ink-400 mb-4">
              Upload your own images to use them directly in the video instead of AI-generated
              visuals. The order below is the order the scenes will use them in.
            </p>
            <ImageUploader onChange={setAssets} />
          </div>
        </div>

        <div className="space-y-6">
          <div className="card glass p-6 space-y-5">
            <h3 className="text-lg font-bold border-b border-ink-800 pb-3">Settings</h3>
            
            <div>
              <label className="label mb-2 block">Duration</label>
              <select className="select" value={duration} onChange={e => setDuration(Number(e.target.value))}>
                <option value={10}>10 Seconds</option>
                <option value={15}>15 Seconds</option>
                <option value={20}>20 Seconds</option>
                <option value={30}>30 Seconds</option>
                <option value={60}>60 Seconds</option>
              </select>
            </div>

            <div>
              <label className="label mb-2 block">Aspect Ratio</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "16:9", icon: "📺", label: "16:9" },
                  { id: "9:16", icon: "📱", label: "9:16" },
                  { id: "1:1", icon: "🔲", label: "1:1" }
                ].map(ar => (
                  <button
                    key={ar.id}
                    type="button"
                    onClick={() => setAspectRatio(ar.id)}
                    className={`flex flex-col items-center justify-center p-3 rounded-lg border transition ${
                      aspectRatio === ar.id 
                        ? "bg-brand-500/20 border-brand-500/50 text-brand-400" 
                        : "bg-ink-800/50 border-ink-700 hover:bg-ink-700"
                    }`}
                  >
                    <span className="text-xl mb-1">{ar.icon}</span>
                    <span className="text-xs font-medium">{ar.label}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="label mb-2 block">Language</label>
              <select className="select" value={language} onChange={e => setLanguage(e.target.value)}>
                <option>English</option>
                <option>Hindi</option>
                <option>Hinglish</option>
                <option>Punjabi</option>
              </select>
            </div>

            <div>
              <label className="label mb-2 block">Video Style</label>
              <select className="select" value={style} onChange={e => setStyle(e.target.value)}>
                <option>Cinematic</option>
                <option>Product Advertisement</option>
                <option>Social Media Reel</option>
                <option>Corporate</option>
                <option>Minimal</option>
                <option>Luxury</option>
                <option>Fashion</option>
              </select>
            </div>

            <div>
              <label className="label mb-2 block">Voice</label>
              <select className="select" value={voice} onChange={e => setVoice(e.target.value)}>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="none">No Voice</option>
              </select>
            </div>
            
          </div>
          
          <button 
            className="btn-primary w-full py-4 text-base shadow-lg shadow-brand-500/20"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? "Initializing Magic..." : "✨ Generate Video"}
          </button>
        </div>
      </div>
    </div>
  );
}
