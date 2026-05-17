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
      <div className="flex flex-wrap gap-1.5 min-h-6">
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="gap-1 bg-blue-50 text-blue-700 border border-blue-100">
            {tag}
            <button type="button" aria-label={`移除 ${tag}`} onClick={() => removeTag(tag)}>
              <X className="w-3 h-3" />
            </button>
          </Badge>
        ))}
      </div>
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
          className="h-8 text-[11px]"
        />
        <Button type="button" variant="outline" size="sm" className="h-8 text-[10px]" onClick={() => addTag(draft)}>
          添加
        </Button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((tag) => (
          <button
            key={tag}
            type="button"
            className="text-[10px] px-2 py-1 rounded border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40"
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
