
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';

export const RiskStatusCard = () => {
    return (
        <Card className="bg-white border border-gray-200 shadow-sm rounded-lg">
            <CardHeader className="px-4 py-3 bg-gray-50/50 border-b border-gray-100">
              <CardTitle className="text-[10px] font-bold flex items-center gap-2 uppercase tracking-wider italic font-serif text-gray-700">
                <ShieldCheck className="w-3.5 h-3.5 text-green-600" />
                系统级风控状态
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              {[
                { label: '是否交易时间', status: true, desc: '9:30-11:30 / 13:00-15:00' },
                { label: '数据完整性', status: true, desc: '行情源连接正常 (Tushare)' },
                { label: '重复订单保护', status: true, desc: '同一股票禁止高频挂单' },
                { label: '单股持仓限制', status: true, desc: '最高 50,000 RMB / 股' },
                { label: '总仓位警戒值', status: true, desc: '状态: 安全, 当前 12.5%' }
              ].map(risk => (
                <div key={risk.label} className="flex items-start gap-3 border-b border-gray-50 pb-2 last:border-0 last:pb-0">
                  {risk.status ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500 mt-0.5" /> : <XCircle className="w-3.5 h-3.5 text-red-500 mt-0.5" />}
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold text-gray-900 leading-none">{risk.label}</span>
                    <span className="text-[10px] text-gray-400 font-medium mt-1 uppercase tracking-tighter">{risk.desc}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
    )
}
