export const reportStatusLabel = (status: string) => ({
  COMPLETED: '已完成',
  PROCESSING: '生成中',
  PENDING: '待处理',
  FAILED: '失败',
}[status] || status);

export const signalLabel = (signal?: string | null) => ({
  BUY: '买入',
  SELL: '卖出',
  HOLD: '观望',
}[signal || ''] || signal || '暂无');

export const orderStatusLabel = (status: string) => ({
  PENDING: '委托中',
  FILLED: '已成交',
  CANCELLED: '已取消',
  REJECTED: '已拒绝',
}[status] || status);

export const orderSideLabel = (side: string) => ({
  BUY: '买入',
  SELL: '卖出',
}[side] || side);

export const orderTypeLabel = (type: string) => ({
  LIMIT: '限价',
  MARKET: '市价',
}[type] || type);

export const logLevelLabel = (level: string) => ({
  INFO: '信息',
  WARN: '警告',
  ERROR: '错误',
  SUCCESS: '成功',
}[level] || level);

export const riskStatusLabel = (status?: string | null, passed?: boolean) => {
  if (status === 'PASSED' || passed) return '通过';
  if (status === 'BLOCKED' || passed === false) return '拦截';
  return '暂无';
};

export const systemStatusLabel = (status: string) => ({
  NORMAL: '正常',
  API_ERROR: '数据源异常',
  RISK_PAUSED: '风控暂停',
}[status] || status);

export const dataSourceStatusLabel = (status: string) => ({
  HEALTHY: '已连接',
  WARNING: '警告',
  ERROR: '异常',
}[status] || status);

export const newsTypeLabel = (type: string) => ({
  ANNOUNCEMENT: '公告',
  NEWS: '动态',
  FINANCIAL: '财务',
}[type] || type);

export const researchStepIndex = (step: string) => {
  const steps = ['IDENTIFY_STOCK', 'FETCH_MARKET_DATA', 'RUN_TRADING_AGENTS', 'NORMALIZE_REPORT', 'DONE'];
  const idx = steps.indexOf(step);
  return idx >= 0 ? idx : 0;
};

export const formatDateTime = (value?: string | null) => {
  if (!value) return '-';
  return value.replace('T', ' ').replace(/\+.*$/, '').replace(/Z$/, '').slice(0, 19);
};

export const formatTime = (value?: string | null) => {
  const full = formatDateTime(value);
  return full.includes(' ') ? full.split(' ')[1] : full;
};

export const formatCurrency = (value: number) => `¥${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
