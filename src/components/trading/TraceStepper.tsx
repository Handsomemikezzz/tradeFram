
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Zap, CheckCircle2, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export const PROCESS_STEPS = [
    { name: 'Signal Engine', status: 'completed' },
    { name: 'Risk Engine', status: 'completed' },
    { name: 'Order Manager', status: 'active' },
    { name: 'Paper Broker', status: 'pending' },
    { name: 'Position Manager', status: 'pending' },
    { name: 'Trade Logger', status: 'pending' },
  ];

export const TraceStepper = () => {
    return (
        <Card className="bg-[#151619] border border-gray-800 shadow-sm rounded-lg text-white">
            <CardHeader className="px-4 py-3 border-b border-white/10">
              <CardTitle className="text-[10px] font-bold flex items-center gap-2 uppercase tracking-wider italic font-serif">
                <Zap className="w-3.5 h-3.5 text-blue-400" />
                最新链路执行追踪 (Trace)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4">
             <div className="flex items-center gap-1 overflow-x-auto pb-2">
               {PROCESS_STEPS.map((step, idx) => (
                 <React.Fragment key={step.name}>
                   <div className={cn(
                     "flex flex-col items-center gap-1 shrink-0",
                     step.status === 'pending' ? "opacity-30" : "opacity-100"
                   )}>
                     <div className={cn(
                       "w-5 h-5 rounded-full border flex items-center justify-center text-[8px]",
                       step.status === 'completed' ? "bg-blue-600 border-blue-600 text-white" :
                       step.status === 'active' ? "bg-white text-blue-600 border-blue-600 animate-pulse font-bold" :
                       "bg-transparent border-white/20 text-white/20"
                     )}>
                       {step.status === 'completed' ? <CheckCircle2 className="w-3 h-3" /> : (idx + 1)}
                     </div>
                     <span className={cn(
                       "text-[8px] font-bold uppercase tracking-tighter text-center w-16",
                       step.status === 'active' ? "text-blue-400" : "text-white/60"
                     )}>{step.name}</span>
                   </div>
                   {idx < PROCESS_STEPS.length - 1 && (
                     <ArrowRight className="w-3 h-3 text-white/30 shrink-0 mb-4" />
                   )}
                 </React.Fragment>
               ))}
             </div>
            </CardContent>
          </Card>
    )
}
