export const reviewEntryTypeLabel: Record<string, string> = {
  TRADE_ACTION: '交易行为',
  OBSERVATION_DECISION: '观察决策',
};

export const reviewActionLabel: Record<string, string> = {
  BUY: '买入',
  SELL: '卖出',
  ADD: '加仓',
  REDUCE: '减仓',
  CLEAR: '清仓',
  DO_T: '做 T',
  WANTED_BUY: '想买未买',
  WANTED_SELL: '想卖未卖',
  CANCELLED_ORDER: '撤单',
  HELD_BACK: '忍住没动',
  PLAN_OBSERVE: '计划观察',
};

export const reviewPlanStatusLabel: Record<string, string> = {
  PLANNED: '计划内',
  UNPLANNED: '计划外',
  INTRADAY_ADJUSTMENT: '临盘调整',
  OBSERVED_ONLY: '观察未执行',
};

export const positionContextLabel: Record<string, string> = {
  EMPTY: '空仓',
  LIGHT: '轻仓',
  HALF: '半仓',
  HEAVY: '重仓',
  FULL: '满仓',
  HOLDING: '持有中',
};

export const emotionPresets = ['怕踏空', '急躁追高', '犹豫不决', '幻想扛单', '冷静执行', '防守空仓', '模式内低吸', '分时冲动'];
export const problemPresets = ['忽视监管红线', '大盘退潮期强做', '无板块效应硬顶', '吃T+1闷棍', '炸板无纪律死扛', '执行偏差/意念操盘', '仓位失控/满仓赌博', '无明显问题'];
export const sectorPresets = ['新质生产力', '商业航天', '半导体龙头', '人形机器人', '有色资源', '低空经济', 'AI算力', '高股息红利'];

export const stockReviewStatusLabel: Record<string, string> = {
  OPEN: '进行中',
  CLOSED: '已结束',
};

export const stockReviewInitialActionLabel: Record<string, string> = {
  BUY: '买入建仓',
  WATCH: '开始关注',
  PLAN_BUY: '计划买入',
};

export const stockReviewEventTypeLabel: Record<string, string> = {
  HOLD: '继续持有',
  ADD: '加仓',
  REDUCE: '减仓',
  SELL: '卖出',
  DO_T: '做 T',
  PLAN_CHANGE: '计划变化',
  EMOTION: '情绪波动',
  OBSERVATION: '观察记录',
};

export const followedPlanLabel: Record<string, string> = {
  true: '按计划执行',
  false: '偏离计划',
};
