"use client";

import { useCallback, useState } from "react";
import { Asset } from "@/lib/api";
import { ImageUploader } from "@/components/upload/ImageUploader";

/**
 * Standalone asset library — manage images that are not yet bound to a project.
 */
export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const handleChange = useCallback((next: Asset[]) => setAssets(next), []);

  const totalBytes = assets.reduce((sum, a) => sum + a.file_size_bytes, 0);

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-12">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Assets</h1>
          <p className="text-ink-400 mt-1">
            Your uploaded images. Reorder them to control how scenes use them.
          </p>
        </div>
        <div className="text-right text-sm text-ink-400 shrink-0">
          <div className="font-medium text-ink-200">{assets.length} images</div>
          <div>{(totalBytes / 1024 / 1024).toFixed(1)} MB stored</div>
        </div>
      </div>

      <div className="card glass p-6">
        <ImageUploader onChange={handleChange} />
      </div>
    </div>
  );
}
