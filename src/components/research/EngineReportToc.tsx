import { cn } from '@/lib/utils';

export function engineSectionId(key: string) {
  return `engine-section-${key}`;
}

type EngineSection = {
  key: string;
  label: string;
};

type EngineReportTocProps = {
  sections: EngineSection[];
  activeKey: string | null;
  onJump: (key: string) => void;
  className?: string;
};

/** Desktop sticky outline — floats beside engine report content */
export function EngineReportToc({ sections, activeKey, onJump, className }: EngineReportTocProps) {
  if (sections.length === 0) return null;

  return (
    <aside className={cn('hidden lg:block w-52 shrink-0', className)}>
      <nav
        aria-label="引擎全文章节目录"
        className="sticky top-20 rounded-lg border border-gray-200 bg-white/95 p-3 shadow-sm backdrop-blur-sm"
      >
        <div className="mb-2 text-[9px] font-bold uppercase tracking-widest text-gray-400">章节目录</div>
        <ul className="max-h-[calc(100vh-8rem)] space-y-1 overflow-y-auto">
          {sections.map((section) => (
            <li key={section.key}>
              <button
                type="button"
                onClick={() => onJump(section.key)}
                className={cn(
                  'w-full rounded px-2 py-1.5 text-left text-[10px] leading-snug transition-colors',
                  activeKey === section.key
                    ? 'border-l-2 border-blue-500 bg-blue-50 font-bold text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                )}
              >
                {section.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}

/** Mobile horizontal chapter strip */
export function EngineReportTocMobile({ sections, activeKey, onJump }: EngineReportTocProps) {
  if (sections.length === 0) return null;

  return (
    <div className="lg:hidden sticky top-14 z-10 -mx-1 mb-1 rounded-lg border border-gray-200 bg-white/95 p-2 shadow-sm backdrop-blur-sm">
      <div className="mb-1.5 text-[9px] font-bold uppercase tracking-widest text-gray-400">章节目录</div>
      <div className="flex gap-1.5 overflow-x-auto pb-0.5">
        {sections.map((section) => (
          <button
            key={section.key}
            type="button"
            onClick={() => onJump(section.key)}
            className={cn(
              'shrink-0 rounded-full border px-2.5 py-1 text-[9px] font-bold whitespace-nowrap transition-colors',
              activeKey === section.key
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 bg-gray-50 text-gray-600',
            )}
          >
            {section.label}
          </button>
        ))}
      </div>
    </div>
  );
}
