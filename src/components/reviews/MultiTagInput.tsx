import React, { useState } from 'react';
import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface MultiTagInputProps {
  value: string[];
  presets: string[];
  placeholder: string;
  onChange: (value: string[]) => void;
}

export const MultiTagInput = ({ value, presets, placeholder, onChange }: MultiTagInputProps) => {
  const [draft, setDraft] = useState('');

  const addTag = (tag: string) => {
    const normalized = tag.trim();
    if (!normalized || value.includes(normalized) || value.length >= 10) return;
    onChange([...value, normalized]);
    setDraft('');
  };

  const removeTag = (tag: string) => onChange(value.filter((item) => item !== tag));

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1 border border-sky-100 bg-sky-50 px-2 py-1 text-[11px] font-medium text-sky-700">
              {tag}
              <button type="button" aria-label={`移除 ${tag}`} onClick={() => removeTag(tag)} className="rounded-full p-0.5 hover:bg-sky-100">
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              addTag(draft);
            }
          }}
          className="h-10 rounded-md border-slate-200 bg-white text-[13px] shadow-sm placeholder:text-slate-400 focus-visible:border-sky-300 focus-visible:ring-sky-100"
        />
        <Button type="button" variant="outline" size="sm" className="h-10 rounded-md border-slate-200 bg-white px-4 text-[12px] font-semibold text-slate-700 shadow-sm hover:bg-slate-50" onClick={() => addTag(draft)}>
          添加
        </Button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((tag) => (
          <button
            key={tag}
            type="button"
            className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-500 transition hover:border-slate-300 hover:bg-slate-50 disabled:opacity-40"
            disabled={value.includes(tag)}
            onClick={() => addTag(tag)}
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  );
};
