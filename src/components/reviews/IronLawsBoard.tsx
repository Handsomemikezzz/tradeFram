import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Award, AlertTriangle, XCircle, Plus, Trash2, CheckCircle2, ChevronRight, Hash, ShieldAlert } from 'lucide-react';
import { ReviewEntryResponse } from '@/services/api/types';

interface IronLaw {
  id: string;
  text: string;
  tag: string; // The problemTag or emotionTag to auto-count from reflections
  status: 'COMPLIANT' | 'CHALLENGED' | 'VIOLATED';
  createdAt: string;
}

const DEFAULT_LAWS: IronLaw[] = [
  {
    id: 'law-1',
    text: '绝对不在上午 10:00 前情绪化急躁满仓',
    tag: '急躁',
    status: 'COMPLIANT',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'law-2',
    text: '严格执行止损计划，绝不因为亏损产生幻想而抗单',
    tag: '抗单',
    status: 'COMPLIANT',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'law-3',
    text: '绝不追高非主流板块的跟风股，只做核心龙头',
    tag: '追高',
    status: 'CHALLENGED',
    createdAt: new Date().toISOString(),
  },
  {
    id: 'law-4',
    text: '买入逻辑不充分、市场环境不明朗时，绝不随意交易',
    tag: '随意交易',
    status: 'COMPLIANT',
    createdAt: new Date().toISOString(),
  },
];

interface IronLawsBoardProps {
  reflections: ReviewEntryResponse[];
}

export const IronLawsBoard = ({ reflections }: IronLawsBoardProps) => {
  const [laws, setLaws] = useState<IronLaw[]>([]);
  const [newRuleText, setNewRuleText] = useState('');
  const [newRuleTag, setNewRuleTag] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  // Load laws from LocalStorage or initialize with defaults
  useEffect(() => {
    const saved = localStorage.getItem('waytofree_dojo_iron_laws');
    if (saved) {
      try {
        setLaws(JSON.parse(saved));
      } catch (err) {
        setLaws(DEFAULT_LAWS);
      }
    } else {
      setLaws(DEFAULT_LAWS);
      localStorage.setItem('waytofree_dojo_iron_laws', JSON.stringify(DEFAULT_LAWS));
    }
  }, []);

  const saveLaws = (updatedLaws: IronLaw[]) => {
    setLaws(updatedLaws);
    localStorage.setItem('waytofree_dojo_iron_laws', JSON.stringify(updatedLaws));
  };

  const handleAddRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRuleText.trim()) {
      toast.error('规则内容不能为空');
      return;
    }

    const newRule: IronLaw = {
      id: `law-${Date.now()}`,
      text: newRuleText.trim(),
      tag: newRuleTag.trim() || '通用',
      status: 'COMPLIANT',
      createdAt: new Date().toISOString(),
    };

    const updated = [newRule, ...laws];
    saveLaws(updated);
    toast.success('铁律新增成功，开始严格遵守！');
    setNewRuleText('');
    setNewRuleTag('');
    setIsAdding(false);
  };

  const handleDeleteRule = (id: string) => {
    const updated = laws.filter((law) => law.id !== id);
    saveLaws(updated);
    toast.success('规则已移除');
  };

  const handleToggleStatus = (id: string, currentStatus: IronLaw['status']) => {
    const nextStatusMap: Record<IronLaw['status'], IronLaw['status']> = {
      COMPLIANT: 'CHALLENGED',
      CHALLENGED: 'VIOLATED',
      VIOLATED: 'COMPLIANT',
    };
    const nextStatus = nextStatusMap[currentStatus];

    const updated = laws.map((law) =>
      law.id === id ? { ...law, status: nextStatus } : law
    );
    saveLaws(updated);
    toast.success('纪律执行状态已更新');
  };

  // Helper to count historical violations based on tag matching reflections
  const getViolationCount = (tag: string) => {
    if (!tag || tag === '通用') return 0;
    return reflections.filter((ref) =>
      ref.emotionTags.includes(tag) || ref.problemTags.includes(tag)
    ).length;
  };

  // Metrics
  const compliantCount = laws.filter((l) => l.status === 'COMPLIANT').length;
  const challengedCount = laws.filter((l) => l.status === 'CHALLENGED').length;
  const violatedCount = laws.filter((l) => l.status === 'VIOLATED').length;
  const totalCount = laws.length;
  const complianceRate = totalCount > 0 ? Math.round((compliantCount / totalCount) * 100) : 0;

  return (
    <div className="space-y-4">
      {/* Metrics Card */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
          <span>防守率 / 纪律健康度</span>
          <span className="font-mono text-blue-600 normal-case">{complianceRate}% 达标</span>
        </h4>
        
        {/* Compliance Progress Bar */}
        <div className="mt-2.5 h-2 w-full rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-blue-500 transition-all duration-500"
            style={{ width: `${complianceRate}%` }}
          />
        </div>

        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-emerald-50/50 p-2">
            <div className="font-mono text-base font-bold text-emerald-700">{compliantCount}</div>
            <div className="text-[10px] text-slate-500">正常坚守</div>
          </div>
          <div className="rounded-lg bg-amber-50/50 p-2">
            <div className="font-mono text-base font-bold text-amber-700">{challengedCount}</div>
            <div className="text-[10px] text-slate-500">面临考验</div>
          </div>
          <div className="rounded-lg bg-rose-50/50 p-2">
            <div className="font-mono text-base font-bold text-rose-700">{violatedCount}</div>
            <div className="text-[10px] text-slate-500">近期破戒</div>
          </div>
        </div>
      </div>

      {/* Rules list Header */}
      <div className="flex items-center justify-between px-1">
        <h3 className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
          <ShieldAlert className="h-4 w-4 text-blue-600" />
          避坑铁律与心法卡 ({totalCount})
        </h3>
        <button
          onClick={() => setIsAdding(!isAdding)}
          className="inline-flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-[10px] font-bold text-white shadow-xs hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-3 w-3" />
          {isAdding ? '收起' : '新建铁律'}
        </button>
      </div>

      {/* Inline Adding Form */}
      {isAdding && (
        <form
          onSubmit={handleAddRule}
          className="rounded-xl border border-blue-100 bg-blue-50/30 p-3.5 shadow-xs space-y-3 animate-in slide-in-from-top-2 duration-200"
        >
          <div>
            <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
              铁律核心内容 (否定句，即“绝对不/绝不...”)
            </label>
            <textarea
              required
              rows={2}
              value={newRuleText}
              onChange={(e) => setNewRuleText(e.target.value)}
              placeholder="例如：绝不追高非核心龙头的跟风弱势股"
              className="w-full rounded border border-slate-200 bg-white px-2.5 py-1.5 text-xs outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
              关联反思标签 (可与心路历程中记录的标签自动统计)
            </label>
            <input
              type="text"
              value={newRuleTag}
              onChange={(e) => setNewRuleTag(e.target.value)}
              placeholder="例如：追高 / 抗单 / 急躁 / 随意交易"
              className="w-full rounded border border-slate-200 bg-white px-2.5 py-1 text-xs outline-none focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setIsAdding(false)}
              className="rounded px-2.5 py-1 text-[10px] font-bold text-slate-500 hover:bg-slate-100"
            >
              取消
            </button>
            <button
              type="submit"
              className="rounded bg-blue-600 px-3 py-1 text-[10px] font-bold text-white hover:bg-blue-700 transition-colors"
            >
              保存铁律
            </button>
          </div>
        </form>
      )}

      {/* Rules list */}
      <div className="space-y-2.5">
        {laws.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-xs text-slate-400">
            暂无自定义交易铁律，点击上方“新建铁律”开始铸造你的防线。
          </div>
        ) : (
          laws.map((law) => {
            const histViolations = getViolationCount(law.tag);
            return (
              <div
                key={law.id}
                className="group relative rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs transition-all hover:shadow-md hover:border-slate-300"
              >
                {/* Header Action Row */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-1.5">
                    {/* Compliance Indicator Badge */}
                    <button
                      onClick={() => handleToggleStatus(law.id, law.status)}
                      className="transition-transform active:scale-90"
                      title="点击切换遵守状态"
                    >
                      {law.status === 'COMPLIANT' && (
                        <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
                      )}
                      {law.status === 'CHALLENGED' && (
                        <AlertTriangle className="h-4.5 w-4.5 text-amber-500" />
                      )}
                      {law.status === 'VIOLATED' && (
                        <XCircle className="h-4.5 w-4.5 text-rose-500" />
                      )}
                    </button>
                    <span className="font-mono text-[9px] font-semibold text-slate-400 uppercase">
                      ID: {law.id.split('-')[1] || 'custom'}
                    </span>
                  </div>
                  
                  {/* Delete Button */}
                  <button
                    onClick={() => handleDeleteRule(law.id)}
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 transition-all p-0.5 rounded"
                    title="删除规则"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Content */}
                <p className="mt-2 text-xs font-bold text-slate-800 leading-relaxed pr-2">
                  {law.text}
                </p>

                {/* Foot Indicators */}
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-50 pt-2.5 text-[10px]">
                  <div className="flex items-center gap-1.5">
                    <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-0.5 font-medium text-slate-600 ring-1 ring-inset ring-slate-500/10">
                      <Hash className="mr-0.5 h-2.5 w-2.5 text-slate-400" />
                      {law.tag}
                    </span>
                    {histViolations > 0 ? (
                      <span className="inline-flex items-center rounded-full bg-rose-50 px-2 py-0.5 font-bold text-rose-700 ring-1 ring-inset ring-rose-600/10">
                        近30天触犯 {histViolations} 次
                      </span>
                    ) : (
                      law.tag !== '通用' && (
                        <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/10">
                          30天零触犯 🟢
                        </span>
                      )
                    )}
                  </div>

                  {/* Quick toggle hint */}
                  <button
                    onClick={() => handleToggleStatus(law.id, law.status)}
                    className="text-slate-400 hover:text-blue-600 font-medium transition-colors flex items-center"
                  >
                    {law.status === 'COMPLIANT' && '完美遵守中'}
                    {law.status === 'CHALLENGED' && '面临挑战'}
                    {law.status === 'VIOLATED' && '亮黄牌⚠️'}
                    <ChevronRight className="h-3 w-3 ml-0.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
