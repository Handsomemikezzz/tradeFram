import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';
import { RiskSystemRuleResponse, tradingApi } from '@/services/api';

interface RiskStatusCardProps {
  refreshKey?: number;
}

export const RiskStatusCard = ({ refreshKey = 0 }: RiskStatusCardProps) => {
  const [rules, setRules] = useState<RiskSystemRuleResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    tradingApi.getRiskSystemStatus()
      .then((status) => {
        if (cancelled) return;
        setRules(status.rules);
        setError(null);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <Card className="bg-white border border-gray-200 shadow-sm rounded-lg">
      <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100">
        <CardTitle className="text-[10px] font-bold flex items-center gap-2 uppercase tracking-wider italic font-serif text-gray-700">
          <ShieldCheck className="w-3.5 h-3.5 text-green-600" />
          系统级风控状态
        </CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-4">
        {loading && <div className="text-[11px] text-gray-400">正在加载风控状态...</div>}
        {!loading && error && <div className="text-[11px] text-red-500">{error}</div>}
        {!loading && !error && rules.length === 0 && <div className="text-[11px] text-gray-400">暂无风控状态</div>}
        {!loading && !error && rules.map((risk) => (
          <div key={risk.rule} className="flex items-start gap-3 border-b border-gray-50 pb-2 last:border-0 last:pb-0">
            {risk.passed ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500 mt-0.5" /> : <XCircle className="w-3.5 h-3.5 text-red-500 mt-0.5" />}
            <div className="flex flex-col">
              <span className="text-[11px] font-bold text-gray-900 leading-none">{risk.label}</span>
              <span className="text-[10px] text-gray-400 font-medium mt-1 uppercase tracking-tighter">{risk.description}</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
