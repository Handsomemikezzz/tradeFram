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

export const emotionPresets = ['怕踏空', '急躁', '犹豫', '贪便宜', '想回本', '冷静', '防守'];
export const problemPresets = ['策略问题', '判断问题', '执行问题', '情绪问题', '仓位问题', '无明显问题'];
export const sectorPresets = ['商业航天', '半导体', '有色', '风电', '电力', '白酒', '银行'];
