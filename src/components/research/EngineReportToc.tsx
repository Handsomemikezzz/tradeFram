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

type TocNavProps = EngineReportTocProps & {
  className?: string;
};

function TocNav({ sections, activeKey, onJump, className }: TocNavProps) {
  return (
    <nav
      aria-label="引擎全文章节目录"
      className={cn(
        'rounded-lg border border-gray-200 bg-white/95 p-3 shadow-md backdrop-blur-sm',
        className,
      )}
    >
      <div className="mb-2 text-[9px] font-bold uppercase tracking-widest text-gray-400">章节目录</div>
      <ul className="max-h-[calc(100vh-7rem)] space-y-1 overflow-y-auto overscroll-contain">
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
  );
}

/**
 * Desktop floating TOC — fixed to viewport so it stays visible while scrolling.
 * (Sticky failed because the aside column was only as tall as the nav itself.)
 */
export function EngineReportToc({ sections, activeKey, onJump }: EngineReportTocProps) {
  if (sections.length === 0) return null;

  return (
    <TocNav
      sections={sections}
      activeKey={activeKey}
      onJump={onJump}
      className="hidden lg:block fixed right-6 top-[4.5rem] z-30 w-52"
    />
  );
}

/** Sticks below top bar while scrolling on mobile */
export function EngineReportTocMobile({ sections, activeKey, onJump }: EngineReportTocProps) {
  if (sections.length === 0) return null;

  return (
    <div className="lg:hidden sticky top-14 z-20 -mx-1 mb-2 rounded-lg border border-gray-200 bg-white/95 p-2 shadow-sm backdrop-blur-sm">
      <div className="mb-1.5 text-[9px] font-bold uppercase tracking-widest text-gray-400">章节目录</div>
      <div className="flex gap-1.5 overflow-x-auto pb-0.5 overscroll-x-contain">
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
