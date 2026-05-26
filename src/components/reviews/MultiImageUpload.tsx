import React, { useRef, useState } from 'react';
import { Image, Loader2, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { reviewCardApi } from '@/services/api';
import { API_BASE_URL } from '@/services/api/client';

export function resolveImageUrl(url: string | null | undefined): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const apiHost = API_BASE_URL.replace('/api/v1', '');
  return `${apiHost}${url}`;
}

interface MultiImageUploadProps {
  images: string[];
  onChange: (images: string[]) => void;
  maxCount?: number;
  label?: string;
}

export function MultiImageUpload({ images, onChange, maxCount = 9, label = '上传走势图表' }: MultiImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    if (images.length + files.length > maxCount) {
      toast.error(`最多只能上传 ${maxCount} 张图片`);
      return;
    }

    setUploading(true);
    const newUrls: string[] = [...images];

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (!file.type.startsWith('image/')) {
          toast.error(`${file.name} 不是有效的图片文件`);
          continue;
        }
        const res = await reviewCardApi.uploadImage(file);
        newUrls.push(res.url);
      }
      onChange(newUrls);
      toast.success('图表上传成功');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '图片上传失败');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemove = (indexToRemove: number) => {
    const updated = images.filter((_, idx) => idx !== indexToRemove);
    onChange(updated);
  };

  return (
    <div className="space-y-2">
      <span className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      
      <div className="flex flex-wrap gap-3">
        {images.map((url, idx) => (
          <div key={idx} className="group relative h-20 w-20 overflow-hidden rounded-md border border-slate-200 bg-slate-50 shadow-sm transition hover:border-slate-300">
            <img 
              src={resolveImageUrl(url)} 
              alt={`Review chart ${idx + 1}`} 
              className="h-full w-full object-cover" 
            />
            <button
              type="button"
              onClick={() => handleRemove(idx)}
              className="absolute right-1 top-1 rounded-full bg-slate-900/60 p-1 text-white opacity-0 transition group-hover:opacity-100 hover:bg-slate-900/80"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}

        {images.length < maxCount && (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex h-20 w-20 flex-col items-center justify-center rounded-md border-2 border-dashed border-slate-200 bg-slate-50 text-slate-400 transition hover:border-slate-300 hover:bg-slate-100/50 hover:text-slate-600 disabled:opacity-50"
          >
            {uploading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <Plus className="h-4 w-4" />
                <span className="mt-1 text-[10px] font-medium">添加图表</span>
              </>
            )}
          </button>
        )}
      </div>

      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => handleUpload(e.target.files)}
        multiple
        accept="image/*"
        className="hidden"
      />
    </div>
  );
}
