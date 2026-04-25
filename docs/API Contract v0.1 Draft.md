# A 股研究与模拟交易系统 API Contract（从当前前端代码反推）

生成日期：2026-04-25  
范围：仅基于当前前端源码梳理，不基于截图猜测。第一版只做 **Paper Trading / 模拟交易**，不接真实券商。AI 只生成研究报告，不直接决定交易。交易闭环必须落库并可审计：

`Signal → Risk Check → Order → Execution → Position → Log`

## 0. 前端证据来源

- 路由：`src/App.tsx`
- 类型：`src/types.ts`
- Mock：`src/services/mockData.ts`、`src/services/mockService.ts`
- 页面：`src/pages/Dashboard.tsx`、`src/pages/Research.tsx`、`src/pages/ReportDetail.tsx`、`src/pages/TradingConsole.tsx`、`src/pages/History.tsx`
- 组件：`src/components/dashboard/*`、`src/components/research/*`、`src/components/trading/*`、`src/components/history/*`、`src/components/layout/*`

---

## 1. 全局约定

### 1.1 Base URL

```text
/api/v1
```

### 1.2 通用响应包络

```json
{
  "success": true,
  "data": {},
  "requestId": "req_20260425_000001",
  "serverTime": "2026-04-25T23:46:20+08:00"
}
```

错误响应：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请输入有效的 6 位 A 股代码",
    "details": { "field": "code" }
  },
  "requestId": "req_20260425_000002",
  "serverTime": "2026-04-25T23:46:20+08:00"
}
```

### 1.3 分页响应

```json
{
  "items": [],
  "page": 1,
  "pageSize": 20,
  "total": 142,
  "hasMore": true
}
```

### 1.4 A 股代码约定

前端输入为 6 位代码；后端建议同时返回 `code` 与 `symbol`：

```json
{
  "code": "600519",
  "symbol": "600519.SH",
  "exchange": "SH"
}
```

---

## 2. 当前 TypeScript 类型与推荐 API 枚举

前端当前中文枚举来自 `src/types.ts`。API 建议使用稳定英文枚举，前端再映射中文展示。

| 前端类型 | 当前值 | API 建议值 | 说明 |
|---|---|---|---|
| `SystemStatus` | `正常` / `数据源异常` / `风控暂停` | `NORMAL` / `API_ERROR` / `RISK_PAUSED` | 系统状态 |
| `ReportStatus` | `已完成` / `生成中` / `失败` | `COMPLETED` / `PROCESSING` / `FAILED` | AI 研究任务/报告状态 |
| `SignalType` | `买入` / `卖出` / `观望` | `BUY` / `SELL` / `HOLD` | 策略信号，不等于交易决策 |
| `OrderStatus` | `委托中` / `已成交` / `已取消` / `已拒绝` | `PENDING` / `FILLED` / `CANCELLED` / `REJECTED` | 模拟订单状态 |
| `LogLevel` | `信息` / `警告` / `错误` / `成功` | `INFO` / `WARN` / `ERROR` / `SUCCESS` | 日志级别 |
| `DataSource.status` | `Healthy` / `Warning` / `Error` | `HEALTHY` / `WARNING` / `ERROR` | 数据源健康度 |
| `RiskRecord.passed` | `true` / `false` | `PASSED` / `BLOCKED` | 风控结果 |
| 交易链路步骤 | 前端写死 | `SIGNAL` / `RISK_CHECK` / `ORDER` / `EXECUTION` / `POSITION` / `LOG` | 必须按顺序审计 |
| 链路步骤状态 | `completed` / `active` / `pending` | `COMPLETED` / `ACTIVE` / `PENDING` / `FAILED` | 执行追踪 |
| 订单方向 | `买入` / `卖出` | `BUY` / `SELL` | 模拟交易方向 |
| 订单类型 | `限价` / `市价` | `LIMIT` / `MARKET` | 模拟订单类型 |

---

## 3. 页面路由结构

| 页面名称 | Route | 用途 | 优先级 |
|---|---|---|---|
| 首页概览 Dashboard | `/` | 总览 KPI、今日事项、监控池、系统日志、快速研究入口 | P0 |
| 股票研究 Research | `/research` | 发起 AI 研究任务、查看研究记录、加入观察池/监控池 | P0 |
| 研究报告详情 ReportDetail | `/research/:code` | 展示个股行情、走势、AI 报告 Tabs、加入观察池/监控池 | P0 |
| 交易控制台 TradingConsole | `/trading` | 模拟交易系统开关、手动巡检、监控池、风控状态、链路追踪 | P0 |
| 持仓与日志 History | `/history` | 模拟账户、持仓、订单、风控审计、系统日志 | P0 |
| 未匹配路由 | `*` | 重定向到 `/` | P2 |

---

# 4. 页面级 API Contract

## 4.1 首页概览 Dashboard

### 页面用途

展示模拟交易系统总览：风险提示、KPI、今日待处理事项、交易监控池摘要、系统运行日志、快速股票研究入口。

### 需要的数据

- Dashboard KPI：观察池监控数、今日信号数、风控拦截数、模拟账户净值/月收益。
- 今日待处理事项：风控拦截、数据过期、报告失败、暂停股票数。
- 交易监控池摘要表：当前前端误用 `MOCK_RESEARCH_RECORDS` 展示，应改为真实监控池/研究摘要。
- 系统日志：`SystemLog[]`。
- 快速研究统计：已完成研究数、待处理任务数。
- 顶栏/侧栏系统状态：系统状态、数据源连接、AI 服务状态、交易日时间、数据延迟。

### 表格字段

#### 交易监控池摘要表（当前 Dashboard 组件）

| UI 字段 | 当前来源 | API 字段建议 |
|---|---|---|
| 代码 | `ResearchRecord.code + '.SH'` | `symbol` |
| 名称 | `ResearchRecord.name` | `name` |
| 时间 | `researchTime` 的 HH:mm | `lastUpdateTime` |
| 状态 | `ResearchRecord.status` | `status` |
| 操作 | Detail | `detailUrl` 或由前端路由生成 |

#### 系统运行日志

| UI 字段 | 当前来源 | API 字段建议 |
|---|---|---|
| 时间 | `SystemLog.time` | `time` |
| 级别 | `SystemLog.level` | `level` |
| 事件 | `SystemLog.event` | `event` |
| 详情 | `SystemLog.detail` | `detail` |
| 模块 | 隐含/History 展示 | `module` |
| 股票代码 | 可选 | `code` |
| 关联 ID | 可选 | `relId` |

### 用户动作

| 动作 | 当前前端行为 | 推荐 API |
|---|---|---|
| 点击「查看拦截详情」KPI trend | 仅样式，无事件 | 跳转 `/history?tab=risk` 或 `GET /risk-checks` |
| 点击「配置策略」 | 无事件 | 打开策略配置页/抽屉；`GET /strategies`、`PATCH /monitoring-pool/{id}` |
| 点击「Detail」 | 无事件 | 跳转研究详情 `/research/{code}` |
| 点击「进入交易日志控制台」 | 无事件 | 跳转 `/history?tab=logs` |
| 快速股票研究输入 +「开始 AI 研究分析」 | 当前无状态/无事件 | `POST /research/tasks` |
| 顶栏「导出日报」 | 无事件 | `POST /exports/daily-report` |
| 侧栏「系统设置」 | 无事件 | P2，后续设置页 |

### 推荐 API endpoints

#### P0 - 获取首页总览

```http
GET /api/v1/dashboard/overview?date=2026-04-25
```

Query params：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | 否 | 默认当天 |

Response JSON 示例：

```json
{
  "success": true,
  "data": {
    "riskDisclaimer": "本系统仅用于研究学习和模拟交易，不构成投资建议。所有交易结果均为模拟数据。",
    "kpis": {
      "watchlistCount": 24,
      "watchlistTrendText": "+3 今日新增",
      "todaySignalCount": 8,
      "todayBuySignalCount": 5,
      "todaySellSignalCount": 3,
      "todayRiskBlockedCount": 2,
      "paperAccountNetAsset": 1024530.0,
      "monthReturnPct": 2.45
    },
    "tasks": {
      "riskBlockedToReview": 2,
      "staleDataOver24h": 0,
      "failedResearchReports": 1,
      "pausedMonitoringStocks": 3
    },
    "quickResearchStats": {
      "completedResearchCount": 124,
      "pendingTaskCount": 0
    },
    "system": {
      "status": "NORMAL",
      "tradeDay": true,
      "market": "SH_SZ",
      "currentTime": "2026-04-25T23:46:20+08:00"
    }
  }
}
```

#### P0 - 获取 Dashboard 监控摘要

```http
GET /api/v1/dashboard/monitoring-summary?limit=4
```

Response：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "mon_001",
        "code": "600519",
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "strategy": "均线回归",
        "enabled": true,
        "lastUpdateTime": "2026-04-25T15:00:00+08:00",
        "status": "ACTIVE",
        "latestSignal": "HOLD",
        "riskStatus": "PASSED"
      }
    ]
  }
}
```

#### P0 - 获取系统日志摘要

```http
GET /api/v1/logs?limit=20&module=&level=&code=
```

Response：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "L1",
        "time": "2026-04-25T15:00:05+08:00",
        "level": "INFO",
        "module": "DataSync",
        "code": null,
        "event": "行情更新成功",
        "detail": "成功从 Tushare 同步 1500 只股票日线数据",
        "relId": null
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 1,
    "hasMore": false
  }
}
```

#### P1 - 导出日报

```http
POST /api/v1/exports/daily-report
```

Request body：

```json
{
  "date": "2026-04-25",
  "format": "PDF",
  "includeSections": ["DASHBOARD", "SIGNALS", "RISK", "ORDERS", "POSITIONS", "LOGS"]
}
```

Response：

```json
{
  "success": true,
  "data": {
    "exportId": "exp_001",
    "status": "PROCESSING",
    "downloadUrl": null
  }
}
```

### 状态枚举

- `SystemStatus`: `NORMAL` / `API_ERROR` / `RISK_PAUSED`
- `TaskSeverity`: `INFO` / `WARN` / `ERROR`
- `ExportStatus`: `PROCESSING` / `COMPLETED` / `FAILED`

### 错误状态

- `DATA_SOURCE_UNAVAILABLE`
- `DASHBOARD_AGGREGATION_FAILED`
- `EXPORT_LIMIT_EXCEEDED`

### 对应数据库实体

- `account_snapshot`
- `watchlist_item`
- `monitoring_item`
- `signal`
- `risk_check`
- `paper_order`
- `system_log`
- `data_source_health`
- `daily_export`

### 优先级

P0：`GET /dashboard/overview`、`GET /dashboard/monitoring-summary`、`GET /logs`  
P1：`POST /exports/daily-report`、策略配置入口  
P2：系统设置页

---

## 4.2 股票研究 Research

### 页面用途

输入 A 股代码发起 AI 研究任务，展示研究进度、研究统计、全库研究记录，并允许把股票加入观察池或交易监控池。

### 需要的数据

- 研究输入状态：`stockCode`、`isResearching`、`step`。
- 研究步骤：`识别股票`、`获取行情`、`获取财务`、`获取新闻公告`、`AI 生成报告`、`完成`。
- 研究统计：本月研究总数、成功转化观察池、常用板块。
- 研究记录：`ResearchRecord[]`。

### 表格字段：全库研究记录

| UI 字段 | 当前来源 | API 字段建议 |
|---|---|---|
| 股票代码 | `code` | `code` / `symbol` |
| 股票名称 | `name` | `name` |
| 研究时间 | `researchTime` | `researchTime` |
| 状态 | `status` | `status` |
| 操作 | 查看报告 / 加入观察池 / 加入交易监控池 | actions |

### 用户动作

| 动作 | 当前前端行为 | 推荐 API |
|---|---|---|
| 输入股票代码 | 前端本地 state，限制 6 位 | 仅前端校验；可接 `GET /stocks/{code}` 自动补全 |
| 点击「开始 AI 研究」 | 校验长度；本地 setInterval 模拟步骤；完成后跳 `/research/600519` | `POST /research/tasks`，再轮询/SSE `GET /research/tasks/{taskId}` |
| 代码不足 6 位 | toast error | 后端返回 `VALIDATION_ERROR` |
| 点击「查看报告」 | 跳 `/research/{code}` | 前端路由；详情页 `GET /research/reports/{code}` |
| 点击「加入观察池」 | toast | `POST /watchlist/items` |
| 点击「加入交易监控池」 | toast | `POST /monitoring-pool/items`，需要策略参数或默认策略 |
| 点击「Export CSV」 | 无事件 | `GET /research/records/export?format=CSV` |
| 点击「Clean Logs」 | 无事件；语义不清 | P2：清理研究任务日志，需二次确认；`POST /research/logs/cleanup` |

### 推荐 API endpoints

#### P0 - 创建 AI 研究任务

```http
POST /api/v1/research/tasks
```

Request body：

```json
{
  "code": "600519",
  "market": "A_SHARE",
  "source": "USER_INPUT",
  "options": {
    "includeMarketQuote": true,
    "includeFinancials": true,
    "includeNews": true,
    "includeAnnouncements": true,
    "aiReportOnly": true
  }
}
```

Response：

```json
{
  "success": true,
  "data": {
    "taskId": "rt_20260425_0001",
    "code": "600519",
    "symbol": "600519.SH",
    "status": "PROCESSING",
    "currentStep": "IDENTIFY_STOCK",
    "progressPct": 5,
    "createdAt": "2026-04-25T23:46:20+08:00"
  }
}
```

#### P0 - 查询研究任务进度

```http
GET /api/v1/research/tasks/{taskId}
```

Response：

```json
{
  "success": true,
  "data": {
    "taskId": "rt_20260425_0001",
    "code": "600519",
    "symbol": "600519.SH",
    "status": "PROCESSING",
    "currentStep": "FETCH_FINANCIALS",
    "progressPct": 50,
    "steps": [
      { "step": "IDENTIFY_STOCK", "label": "识别股票", "status": "COMPLETED", "message": null },
      { "step": "FETCH_MARKET", "label": "获取行情", "status": "COMPLETED", "message": null },
      { "step": "FETCH_FINANCIALS", "label": "获取财务", "status": "ACTIVE", "message": null },
      { "step": "FETCH_NEWS", "label": "获取新闻公告", "status": "PENDING", "message": null },
      { "step": "GENERATE_AI_REPORT", "label": "AI 生成报告", "status": "PENDING", "message": null },
      { "step": "DONE", "label": "完成", "status": "PENDING", "message": null }
    ],
    "reportId": null
  }
}
```

任务完成：

```json
{
  "success": true,
  "data": {
    "taskId": "rt_20260425_0001",
    "status": "COMPLETED",
    "progressPct": 100,
    "reportId": "rr_600519_20260425",
    "redirectTo": "/research/600519"
  }
}
```

#### P0 - 获取研究列表

```http
GET /api/v1/research/records?status=&keyword=&code=&page=1&pageSize=20&sort=-researchTime
```

Response：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "1",
        "code": "600519",
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "researchTime": "2026-04-25T10:30:00+08:00",
        "status": "COMPLETED",
        "updateTime": "2026-04-25T15:00:00+08:00",
        "reportId": "rr_600519_20260425"
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 142,
    "hasMore": true
  }
}
```

#### P0 - 获取研究统计

```http
GET /api/v1/research/stats?period=month
```

Response：

```json
{
  "success": true,
  "data": {
    "period": "MONTH",
    "researchCount": 142,
    "watchlistConvertedCount": 38,
    "popularIndustries": ["白酒", "新能源", "医疗器械", "半导体", "互联网"]
  }
}
```

#### P1 - 导出研究记录 CSV

```http
GET /api/v1/research/records/export?format=CSV&status=&keyword=
```

Response：

```json
{
  "success": true,
  "data": {
    "exportId": "exp_research_001",
    "status": "COMPLETED",
    "downloadUrl": "/api/v1/exports/exp_research_001/download"
  }
}
```

### 状态枚举

- `ResearchTaskStep`: `IDENTIFY_STOCK` / `FETCH_MARKET` / `FETCH_FINANCIALS` / `FETCH_NEWS` / `GENERATE_AI_REPORT` / `DONE`
- `ResearchTaskStatus`: `PENDING` / `PROCESSING` / `COMPLETED` / `FAILED`
- `ReportStatus`: `COMPLETED` / `PROCESSING` / `FAILED`

### 错误状态

- `VALIDATION_ERROR`: 非 6 位代码或非法市场。
- `STOCK_NOT_FOUND`: 股票不存在或退市。
- `DATA_SOURCE_UNAVAILABLE`: 行情/财务/新闻源不可用。
- `AI_REPORT_FAILED`: AI 生成失败。
- `RESEARCH_TASK_DUPLICATED`: 同一股票同一天任务重复，可返回现有 `taskId`。

### 对应数据库实体

- `stock`
- `market_quote`
- `financial_snapshot`
- `news_item`
- `announcement`
- `research_task`
- `research_report`
- `watchlist_item`
- `monitoring_item`

### 优先级

P0：创建任务、查询任务、研究列表、研究统计、加入观察池/监控池  
P1：CSV 导出  
P2：Clean Logs

---

## 4.3 研究报告详情 ReportDetail

### 页面用途

展示个股研究报告详情：实时行情、近 7 日走势、AI 结论摘要、风险提示、主营业务、财务概览、新闻公告，并支持加入观察池/监控池。

### 需要的数据

- 股票基础与行情：`Stock`。
- 7 日走势图：当前 `CHART_DATA` 写死。
- AI 报告内容：当前多数文本写死，只插入股票名/行业/PE 等。
- Tabs 隐藏内容：`overview` / `business` / `financial` / `news`。
- 数据页脚：数据源、更新频率、研究基期。

### Tabs / 隐藏交互

| Tab | 内容 | API 字段建议 |
|---|---|---|
| `overview` 结论摘要 | AI 核心结论、Key Insights、值得继续研究、AI 置信度、数据完整度、AI 局限性说明、风险提示 | `report.overview` / `report.risks` |
| `business` 主营业务 | 主营构成占比 | `report.businessSegments` |
| `financial` 财务概览 | 营收、净利润、毛利率、净利率、ROE、PE | `financialSnapshot` |
| `news` 新闻公告 | 近期公告/动态/财务新闻 | `newsItems` |

### 用户动作

| 动作 | 当前前端行为 | 推荐 API |
|---|---|---|
| 进入 `/research/:code` | 从 `MOCK_STOCKS[code]` 取值，找不到 fallback 到 600519 | `GET /research/reports/by-code/{code}`；找不到应 404，不应静默 fallback |
| 点击「加入观察池」 | toast | `POST /watchlist/items` |
| 点击「监控此股」 | toast | `POST /monitoring-pool/items` |
| 切换 Tabs | 前端 Base UI Tabs | 无需 API；也可按需懒加载章节 |
| 新闻项点击 | 仅 hover | P1：打开新闻详情/外链 |

### 推荐 API endpoints

#### P0 - 获取报告详情

```http
GET /api/v1/research/reports/by-code/{code}
```

Path params：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `code` | string | 是 | 6 位 A 股代码，如 `600519` |

Response：

```json
{
  "success": true,
  "data": {
    "reportId": "rr_600519_20260425",
    "code": "600519",
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "market": "上证主板",
    "industry": "白酒",
    "generatedAt": "2026-04-25T15:00:00+08:00",
    "researchBasePeriod": "2026-Q1",
    "dataSources": ["Tushare", "AkShare"],
    "updateFrequency": "10min",
    "quote": {
      "price": 1650.5,
      "change": 12.3,
      "changePercent": 0.75,
      "volume": 12500,
      "amount": 2063000000,
      "updateTime": "2026-04-25T15:00:00+08:00"
    },
    "trend": [
      { "date": "2026-04-19", "price": 1610 },
      { "date": "2026-04-20", "price": 1620 }
    ],
    "financialSnapshot": {
      "revenue": "1500.20 亿",
      "profit": "740.10 亿",
      "grossMargin": 91.5,
      "netMargin": 49.3,
      "roe": 31.2,
      "pe": 28.5
    },
    "report": {
      "overview": "贵州茅台作为白酒板块龙头企业，展现了较强定价权和市场地位……",
      "keyInsights": [
        "品牌护城河：深厚历史底蕴，社交属性带来的消费粘性。",
        "直销占比提升：渠道改革成效显著，利润率进一步优化。"
      ],
      "worthFurtherResearch": true,
      "aiConfidence": 0.92,
      "dataCompleteness": 0.98,
      "aiDisclaimer": "本报告由算法模型生成，仅供参考，不构成投资建议。",
      "risks": [
        { "title": "政策风险", "description": "行业监管政策收紧可能影响估值水平。", "severity": "MEDIUM" }
      ],
      "businessSegments": [
        { "name": "茅台酒", "percent": 88.0 },
        { "name": "系列酒", "percent": 11.5 },
        { "name": "其他业务", "percent": 0.5 }
      ],
      "newsItems": [
        {
          "id": "news_001",
          "title": "贵州茅台：关于分红派息的公告",
          "date": "2026-04-18",
          "type": "ANNOUNCEMENT",
          "url": null
        }
      ]
    }
  }
}
```

#### P0 - 加入观察池

```http
POST /api/v1/watchlist/items
```

Request：

```json
{
  "code": "600519",
  "source": "RESEARCH_REPORT",
  "reportId": "rr_600519_20260425",
  "note": "来自 AI 研究报告详情页"
}
```

Response：

```json
{
  "success": true,
  "data": {
    "id": "wl_001",
    "code": "600519",
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "createdAt": "2026-04-25T23:46:20+08:00"
  }
}
```

#### P0 - 加入交易监控池

```http
POST /api/v1/monitoring-pool/items
```

Request：

```json
{
  "code": "600519",
  "strategyId": "strategy_default_ma_reversion",
  "enabled": true,
  "source": "RESEARCH_REPORT",
  "reportId": "rr_600519_20260425"
}
```

Response：

```json
{
  "success": true,
  "data": {
    "id": "mon_001",
    "code": "600519",
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "strategy": "均线回归",
    "enabled": true,
    "createdAt": "2026-04-25T23:46:20+08:00"
  }
}
```

### 状态枚举

- `NewsType`: `ANNOUNCEMENT` / `NEWS` / `FINANCIAL`
- `RiskSeverity`: `LOW` / `MEDIUM` / `HIGH`

### 错误状态

- `REPORT_NOT_FOUND`
- `STOCK_NOT_FOUND`
- `WATCHLIST_ALREADY_EXISTS`
- `MONITORING_ITEM_ALREADY_EXISTS`
- `STRATEGY_NOT_FOUND`

### 对应数据库实体

- `stock`
- `market_quote`
- `price_bar`
- `financial_snapshot`
- `research_report`
- `research_report_section`
- `news_item`
- `watchlist_item`
- `monitoring_item`
- `strategy`

### 优先级

P0：报告详情、加入观察池、加入监控池  
P1：新闻详情/外链、章节懒加载  
P2：重新生成报告、刷新行情按钮（当前有 `RefreshCw` import 但 UI 未使用）

---

## 4.4 交易控制台 TradingConsole

### 页面用途

模拟交易审计与执行界面：控制模拟交易引擎开关、手动巡检一次、查看系统级风控状态、查看最新交易链路追踪、管理交易监控池。

### 需要的数据

- 交易引擎状态：当前本地 `isBotActive`。
- 手动巡检状态：当前本地 `isRunningCheck`。
- 系统级风控状态：当前 `RiskStatusCard` 写死。
- 最新链路追踪：当前 `TraceStepper` 写死。
- 交易监控池：`MonitoringStock[]`。

### 表格字段：交易监控池

| UI 字段 | 当前来源 | API 字段建议 |
|---|---|---|
| 启用开关 | `enabled` | `enabled` |
| 股票代码 | `name` + `code` | `name` / `code` / `symbol` |
| 策略名称 | `strategy` | `strategyName` / `strategyId` |
| 最新信号 | `lastSignal` | `latestSignal.type` |
| 信号原因 tooltip | `signalReason` | `latestSignal.reason` |
| 风控检测 | `riskStatus` | `latestRiskCheck.status` |
| 最近订单 | `lastOrder` | `latestOrder.createTime` / `latestOrder.id` |
| 操作 | Activity / History icon | 查看执行链路、查看历史 |

### 用户动作

| 动作 | 当前前端行为 | 推荐 API |
|---|---|---|
| 模拟交易系统开关 | 本地 state + toast | `PATCH /paper-trading/engine` |
| 手动巡检一次 | 本地 setTimeout 2s + toast 汇总 | `POST /paper-trading/runs`，严格创建 Signal→Risk→Order→Execution→Position→Log 链路 |
| 批量启用 | 无事件 | `PATCH /monitoring-pool/items/batch` |
| 单行启用 Switch | 仅 checked，无事件 | `PATCH /monitoring-pool/items/{id}` |
| Activity 图标 | 无事件 | `GET /execution-traces?monitoringItemId=...` |
| History 图标 | 无事件 | 跳 `/history?code=...` 或 `GET /orders`/`GET /logs` |
| 最新信号 Tooltip | 展示 `signalReason` | 字段来自 API |

### 推荐 API endpoints

#### P0 - 获取模拟交易引擎状态

```http
GET /api/v1/paper-trading/engine
```

Response：

```json
{
  "success": true,
  "data": {
    "active": false,
    "mode": "PAPER_TRADING_ONLY",
    "pollingEnabled": false,
    "pollingIntervalSec": 5,
    "lastRunId": "run_20260425_001",
    "updatedAt": "2026-04-25T15:00:00+08:00"
  }
}
```

#### P0 - 启停模拟交易引擎

```http
PATCH /api/v1/paper-trading/engine
```

Request：

```json
{
  "active": true,
  "reason": "用户从交易控制台启动"
}
```

Response：

```json
{
  "success": true,
  "data": {
    "active": true,
    "mode": "PAPER_TRADING_ONLY",
    "message": "交易引擎已进入自动轮询状态"
  }
}
```

#### P0 - 手动巡检一次

```http
POST /api/v1/paper-trading/runs
```

Request：

```json
{
  "trigger": "MANUAL",
  "scope": {
    "monitoringItemIds": [],
    "enabledOnly": true
  },
  "dryRun": false
}
```

Response：

```json
{
  "success": true,
  "data": {
    "runId": "run_20260425_002",
    "status": "COMPLETED",
    "summary": {
      "scannedStockCount": 120,
      "generatedSignalCount": 3,
      "riskPassedCount": 2,
      "riskBlockedCount": 1,
      "createdPaperOrderCount": 2,
      "simulatedExecutionCount": 1,
      "durationMs": 1200
    },
    "traceIds": ["trace_001", "trace_002"]
  }
}
```

#### P0 - 获取系统级风控状态

```http
GET /api/v1/risk/system-status
```

Response：

```json
{
  "success": true,
  "data": {
    "overallStatus": "PASSED",
    "rules": [
      {
        "rule": "TRADING_TIME",
        "label": "是否交易时间",
        "passed": true,
        "description": "9:30-11:30 / 13:00-15:00"
      },
      {
        "rule": "DATA_INTEGRITY",
        "label": "数据完整性",
        "passed": true,
        "description": "行情源连接正常 (Tushare)"
      },
      {
        "rule": "DUPLICATE_ORDER_PROTECTION",
        "label": "重复订单保护",
        "passed": true,
        "description": "同一股票禁止高频挂单"
      },
      {
        "rule": "MAX_SINGLE_STOCK_POS",
        "label": "单股持仓限制",
        "passed": true,
        "description": "最高 50,000 RMB / 股"
      },
      {
        "rule": "TOTAL_POSITION_LIMIT",
        "label": "总仓位警戒值",
        "passed": true,
        "description": "状态: 安全, 当前 12.5%"
      }
    ]
  }
}
```

#### P0 - 获取交易监控池

```http
GET /api/v1/monitoring-pool/items?enabled=&keyword=&strategyId=&page=1&pageSize=20
```

Response：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "mon_001",
        "code": "600519",
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "enabled": true,
        "strategyId": "strategy_ma_reversion",
        "strategyName": "均线回归",
        "latestSignal": {
          "id": "sig_001",
          "type": "HOLD",
          "reason": "价格处于中位线，无明显趋势",
          "generatedAt": "2026-04-25T14:59:00+08:00"
        },
        "latestRiskCheck": {
          "id": "risk_001",
          "status": "PASSED",
          "reason": "各项指标符合风控规则"
        },
        "latestOrder": {
          "id": "ORD20260425001",
          "createTime": "2026-04-25T09:35:00+08:00",
          "status": "FILLED"
        },
        "lastTradeTime": "2026-04-25T09:35:10+08:00"
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 3,
    "hasMore": false
  }
}
```

#### P0 - 更新监控项启用状态

```http
PATCH /api/v1/monitoring-pool/items/{id}
```

Request：

```json
{
  "enabled": false,
  "reason": "用户手动暂停"
}
```

Response：

```json
{
  "success": true,
  "data": {
    "id": "mon_001",
    "enabled": false,
    "updatedAt": "2026-04-25T23:46:20+08:00"
  }
}
```

#### P1 - 批量启用监控项

```http
PATCH /api/v1/monitoring-pool/items/batch
```

Request：

```json
{
  "ids": ["mon_001", "mon_002"],
  "enabled": true,
  "reason": "批量启用"
}
```

#### P0 - 获取最新链路执行追踪

```http
GET /api/v1/execution-traces/latest
```

Response：

```json
{
  "success": true,
  "data": {
    "traceId": "trace_001",
    "runId": "run_20260425_002",
    "code": "300750",
    "symbol": "300750.SZ",
    "currentStep": "ORDER",
    "steps": [
      { "step": "SIGNAL", "label": "Signal Engine", "status": "COMPLETED", "relId": "sig_001" },
      { "step": "RISK_CHECK", "label": "Risk Engine", "status": "COMPLETED", "relId": "risk_001" },
      { "step": "ORDER", "label": "Order Manager", "status": "ACTIVE", "relId": "ORD20260425001" },
      { "step": "EXECUTION", "label": "Paper Broker", "status": "PENDING", "relId": null },
      { "step": "POSITION", "label": "Position Manager", "status": "PENDING", "relId": null },
      { "step": "LOG", "label": "Trade Logger", "status": "PENDING", "relId": null }
    ]
  }
}
```

### 状态枚举

- `PaperTradingMode`: `PAPER_TRADING_ONLY`
- `RunStatus`: `PENDING` / `RUNNING` / `COMPLETED` / `FAILED`
- `TraceStep`: `SIGNAL` / `RISK_CHECK` / `ORDER` / `EXECUTION` / `POSITION` / `LOG`
- `TraceStepStatus`: `PENDING` / `ACTIVE` / `COMPLETED` / `FAILED`
- `RiskRule`: `TRADING_TIME` / `DATA_INTEGRITY` / `DUPLICATE_ORDER_PROTECTION` / `MAX_SINGLE_STOCK_POS` / `TOTAL_POSITION_LIMIT`

### 错误状态

- `ENGINE_STATE_CONFLICT`: 启停状态冲突。
- `RUN_ALREADY_IN_PROGRESS`: 巡检正在执行。
- `RISK_CHECK_FAILED`: 风控拦截，不应创建订单。
- `PAPER_ORDER_REJECTED`: 模拟订单被拒绝。
- `MONITORING_ITEM_NOT_FOUND`

### 对应数据库实体

- `paper_trading_engine_state`
- `monitoring_item`
- `strategy`
- `signal`
- `risk_check`
- `paper_order`
- `paper_execution`
- `position`
- `execution_trace`
- `system_log`

### 优先级

P0：引擎状态、启停、手动巡检、监控池、单项启停、系统风控、链路追踪  
P1：批量启用、按行查看链路/历史  
P2：策略配置高级参数

---

## 4.5 持仓与日志 History

### 页面用途

展示模拟账户资产状态与审计记录，包括模拟持仓、订单记录、风控审计、系统日志。顶部提供搜索框和筛选按钮。

### 需要的数据

- 账户摘要：当前 `AccountSummary` 写死。
- 持仓：`Holding[]`。
- 订单：`Order[]`。
- 风控记录：`RiskRecord[]`。
- 系统日志：`SystemLog[]`，当前日志 Tab 使用 `MOCK_LOGS.concat(MOCK_LOGS)` 人为重复。
- 搜索/筛选：当前 UI 存在但无状态、无 API。

### Tabs / 隐藏交互

| Tab | 内容 | API |
|---|---|---|
| `holdings` 模拟持仓 | 持仓表 | `GET /portfolio/positions` |
| `orders` 订单记录 | 模拟订单表 | `GET /orders` |
| `risk` 风控审计 | 风控检查记录 | `GET /risk-checks` |
| `logs` 系统日志 | 日志流 | `GET /logs` |

### 表格字段

#### 模拟持仓

| UI 字段 | API 字段建议 |
|---|---|
| 股票信息 | `name` / `code` / `symbol` |
| 持仓/可卖 | `quantity` / `available` |
| 成本/现价 | `costPrice` / `currentPrice` |
| 总市值 | `marketValue` |
| 浮动盈亏 | `profitProgress`，建议补充 `unrealizedPnl` |
| 更新时间 | `updateTime` |

#### 订单记录

| UI 字段 | API 字段建议 |
|---|---|
| 订单 ID / 时间 | `id` / `createTime` |
| 股票 | `name` / `code` / `symbol` |
| 方向/类型 | `side` / `orderType` |
| 委托价/量 | `price` / `quantity` |
| 成交价/量 | `avgPrice` / `filledQuantity` |
| 状态 | `status` / `rejectReason` |

> 前端当前订单方向列硬编码显示「买入」，应改为 `o.type` / `side`。

#### 风控审计

| UI 字段 | API 字段建议 |
|---|---|
| 检查时间 | `time` |
| 标的 | `code` / `symbol` |
| 信号 | `signal` |
| 检查规则 | `rule` |
| 结果 | `passed` / `status` |
| 详细说明 | `reason` |

#### 系统日志

| UI 字段 | API 字段建议 |
|---|---|
| 时间 | `time` |
| 级别 | `level` |
| 模块 | `module` |
| 事件 | `event` |
| 股票代码 | `code` |
| 详情 | `detail` |
| 关联 ID | `relId` |

### 用户动作

| 动作 | 当前前端行为 | 推荐 API |
|---|---|---|
| 顶部搜索股票代码或订单 ID | 仅输入框，无 state | 对当前 Tab 调对应列表 API 的 `keyword` / `code` / `orderId` |
| 筛选按钮 | 无事件 | 打开筛选 Drawer/Dialog；当前未实现组件 |
| Tabs 切换 | 前端 Base UI Tabs | 切换后拉取对应数据 |
| 查看订单/风控/日志详情 | 当前无行点击 | P1：详情抽屉/页 |
| 导出审计数据 | 当前无按钮 | P1：`GET /orders/export` / `GET /risk-checks/export` / `GET /logs/export` |

### 推荐 API endpoints

#### P0 - 获取账户摘要

```http
GET /api/v1/portfolio/account-summary
```

Response：

```json
{
  "success": true,
  "data": {
    "accountId": "paper_default",
    "currency": "CNY",
    "totalAssets": 1250300.0,
    "availableCash": 350000.0,
    "positionMarketValue": 900300.0,
    "todayPnl": 12400.0,
    "todayPnlPct": 1.0,
    "positionRatio": 72.0,
    "updateTime": "2026-04-25T15:00:00+08:00"
  }
}
```

#### P0 - 获取模拟持仓

```http
GET /api/v1/portfolio/positions?keyword=&code=&page=1&pageSize=20
```

Response：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "code": "600519",
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "quantity": 100,
        "available": 100,
        "costPrice": 1600.0,
        "currentPrice": 1650.5,
        "marketValue": 165050.0,
        "unrealizedPnl": 5050.0,
        "profitProgress": 3.15,
        "updateTime": "2026-04-25T15:00:00+08:00"
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 2,
    "hasMore": false
  }
}
```

#### P0 - 获取订单记录

```http
GET /api/v1/orders?keyword=&code=&status=&side=&from=&to=&page=1&pageSize=20&sort=-createTime
```

Response：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "ORD20260425001",
        "createTime": "2026-04-25T09:35:00+08:00",
        "code": "300750",
        "symbol": "300750.SZ",
        "name": "宁德时代",
        "side": "BUY",
        "orderType": "LIMIT",
        "quantity": 500,
        "price": 198.0,
        "filledQuantity": 500,
        "avgPrice": 198.0,
        "status": "FILLED",
        "rejectReason": null,
        "signalId": "sig_001",
        "riskCheckId": "risk_001",
        "executionId": "exec_001"
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 2,
    "hasMore": false
  }
}
```

#### P0 - 获取风控审计记录

```http
GET /api/v1/risk-checks?keyword=&code=&passed=&rule=&from=&to=&page=1&pageSize=20&sort=-time
```

Response：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "R1",
        "time": "2026-04-25T10:15:00+08:00",
        "code": "000858",
        "symbol": "000858.SZ",
        "signal": "BUY",
        "passed": false,
        "status": "BLOCKED",
        "reason": "订单金额 150,000 RMB 超过最大单股持仓限制 50,000 RMB",
        "rule": "MAX_SINGLE_STOCK_POS",
        "signalId": "sig_002",
        "orderId": null
      }
    ],
    "page": 1,
    "pageSize": 20,
    "total": 2,
    "hasMore": false
  }
}
```

#### P0 - 获取系统日志

同 Dashboard：

```http
GET /api/v1/logs?keyword=&module=&level=&code=&relId=&from=&to=&page=1&pageSize=50&sort=-time
```

### 状态枚举

- `PositionStatus`: `OPEN` / `CLOSED`
- `OrderStatus`: `PENDING` / `FILLED` / `CANCELLED` / `REJECTED`
- `RiskCheckStatus`: `PASSED` / `BLOCKED`
- `LogLevel`: `INFO` / `WARN` / `ERROR` / `SUCCESS`

### 错误状态

- `ACCOUNT_NOT_FOUND`
- `ORDER_NOT_FOUND`
- `INVALID_FILTER`
- `LOG_QUERY_TOO_BROAD`
- `EXPORT_FAILED`

### 对应数据库实体

- `paper_account`
- `account_snapshot`
- `position`
- `paper_order`
- `paper_execution`
- `signal`
- `risk_check`
- `system_log`

### 优先级

P0：账户摘要、持仓、订单、风控、日志列表与搜索筛选参数  
P1：导出、详情 Drawer/Dialog  
P2：高级筛选条件保存

---

# 5. Mock 数据结构与后端实体映射

## 5.1 `Stock`

当前字段：`code`、`name`、`price`、`change`、`changePercent`、`volume`、`amount`、`market`、`industry`、`pe`、`roe`、`revenue`、`profit`、`grossMargin`、`netMargin`、`updateTime`。

推荐拆分：

| 字段 | 实体 |
|---|---|
| `code` / `name` / `market` / `industry` | `stock` |
| `price` / `change` / `changePercent` / `volume` / `amount` / `updateTime` | `market_quote` |
| `pe` / `roe` / `revenue` / `profit` / `grossMargin` / `netMargin` | `financial_snapshot` |

## 5.2 `ResearchRecord`

实体：`research_task` + `research_report`。

字段：`id`、`code`、`name`、`researchTime`、`status`、`updateTime`。建议补充 `reportId`、`taskId`、`symbol`、`failedReason`。

## 5.3 `MonitoringStock`

实体：`monitoring_item` + `strategy` + `signal` + `risk_check` + `paper_order`。

字段：`code`、`name`、`enabled`、`strategy`、`lastSignal`、`signalReason`、`riskStatus`、`lastOrder`、`lastTrade`。建议补充 `id`、`strategyId`、`latestSignalId`、`latestRiskCheckId`、`latestOrderId`。

## 5.4 `Holding`

实体：`position`。

字段：`code`、`name`、`quantity`、`available`、`costPrice`、`currentPrice`、`marketValue`、`profitProgress`、`updateTime`。建议补充 `accountId`、`symbol`、`unrealizedPnl`、`realizedPnl`。

## 5.5 `Order`

实体：`paper_order`。

字段：`id`、`createTime`、`code`、`name`、`type`、`orderType`、`quantity`、`price`、`filledQuantity`、`avgPrice`、`status`、`rejectReason`。建议将 `type` 改为 `side`，并补充 `signalId`、`riskCheckId`、`executionId`、`accountId`。

## 5.6 `RiskRecord`

实体：`risk_check`。

字段：`id`、`time`、`code`、`signal`、`passed`、`reason`、`rule`。建议补充 `signalId`、`orderIntent`、`orderId`、`ruleResultDetails`。

## 5.7 `SystemLog`

实体：`system_log` / `trade_log`。

字段：`id`、`time`、`level`、`module`、`code?`、`event`、`detail`、`relId?`。交易链路日志必须能按 `traceId`、`runId`、`orderId`、`code` 查询。

## 5.8 `DataSource`

实体：`data_source_health`。

字段：`name`、`status`、`latency`。建议改为数值 `latencyMs`，并补充 `lastCheckedAt`、`lastError`。

---

# 6. 交易闭环 Contract（P0 核心）

模拟交易必须后端保证顺序与审计，不允许前端直接创建成交或持仓。

## 6.1 Signal

```http
POST /api/v1/signals/evaluate
```

Request：

```json
{
  "monitoringItemId": "mon_001",
  "code": "300750",
  "strategyId": "strategy_breakout",
  "runId": "run_20260425_002"
}
```

Response：

```json
{
  "success": true,
  "data": {
    "signalId": "sig_001",
    "type": "BUY",
    "reason": "放量突破20日均线",
    "confidence": 0.76,
    "generatedAt": "2026-04-25T09:35:00+08:00"
  }
}
```

## 6.2 Risk Check

```http
POST /api/v1/risk-checks
```

Request：

```json
{
  "signalId": "sig_001",
  "intendedOrder": {
    "side": "BUY",
    "orderType": "LIMIT",
    "quantity": 500,
    "price": 198.0
  }
}
```

Response：

```json
{
  "success": true,
  "data": {
    "riskCheckId": "risk_001",
    "status": "PASSED",
    "passed": true,
    "rules": [
      { "rule": "MAX_SINGLE_STOCK_POS", "passed": true, "message": "未超过单股持仓限制" }
    ]
  }
}
```

## 6.3 Order

仅当 `Risk Check` 通过后创建模拟订单。

```http
POST /api/v1/orders
```

Request：

```json
{
  "signalId": "sig_001",
  "riskCheckId": "risk_001",
  "code": "300750",
  "side": "BUY",
  "orderType": "LIMIT",
  "quantity": 500,
  "price": 198.0
}
```

Response：

```json
{
  "success": true,
  "data": {
    "orderId": "ORD20260425001",
    "status": "PENDING",
    "createTime": "2026-04-25T09:35:00+08:00"
  }
}
```

## 6.4 Execution

```http
POST /api/v1/orders/{orderId}/simulate-execution
```

Response：

```json
{
  "success": true,
  "data": {
    "executionId": "exec_001",
    "orderId": "ORD20260425001",
    "filledQuantity": 500,
    "avgPrice": 198.0,
    "status": "FILLED",
    "executedAt": "2026-04-25T09:35:02+08:00"
  }
}
```

## 6.5 Position

```http
POST /api/v1/portfolio/positions/apply-execution
```

Request：

```json
{
  "executionId": "exec_001"
}
```

Response：

```json
{
  "success": true,
  "data": {
    "positionId": "pos_300750",
    "code": "300750",
    "quantity": 500,
    "available": 500,
    "costPrice": 198.0,
    "updatedAt": "2026-04-25T09:35:03+08:00"
  }
}
```

## 6.6 Log

```http
POST /api/v1/trade-logs
```

Request：

```json
{
  "traceId": "trace_001",
  "runId": "run_20260425_002",
  "level": "SUCCESS",
  "module": "PaperBroker",
  "code": "300750",
  "event": "模拟成交",
  "detail": "订单 ORD20260425001 已按 198.00 模拟成交 500 股",
  "relId": "exec_001"
}
```

Response：

```json
{
  "success": true,
  "data": {
    "logId": "L1001"
  }
}
```

---

# 7. Loading / Error / Empty 状态要求

当前前端真实实现较少：

| 场景 | 当前前端 | API/前端建议 |
|---|---|---|
| 研究任务 loading | `isResearching` + Stepper + Spinner | 使用任务状态轮询/SSE 驱动，不用 setInterval 假进度 |
| 手动巡检 loading | `isRunningCheck` + Spinner | `POST /paper-trading/runs` 返回 `RUNNING` 后轮询 |
| 页面数据 loading | 无 | 所有列表和详情页应有 loading skeleton |
| API error | 仅研究输入校验 toast | 全局错误包络 + toast/inline alert |
| Empty 研究记录 | 无 | 显示“暂无研究记录”，提供发起研究 CTA |
| Empty 监控池 | 无 | 显示“暂无监控股票”，提供加入监控池 CTA |
| Empty 持仓 | 无 | 显示“暂无模拟持仓” |
| Empty 订单 | 无 | 显示“暂无订单记录” |
| Empty 风控 | 无 | 显示“暂无风控审计记录” |
| Empty 日志 | 无 | 显示“暂无系统日志” |
| 报告不存在 | fallback 到 600519 | 后端 404，前端展示 Not Found，不应静默展示错误股票 |

---

# 8. 搜索、筛选、分页、导出交互

| 位置 | 当前 UI | 当前行为 | 推荐 Contract |
|---|---|---|---|
| Research 研究记录 | 无搜索，有 Export CSV / Clean Logs | 按钮无事件 | `GET /research/records` 支持 `status/keyword/page/pageSize`；`GET /research/records/export` |
| History 顶部搜索 | 搜索股票代码或订单 ID | 无 state | 当前 Tab API 均支持 `keyword/code/orderId/page/pageSize` |
| History 筛选按钮 | Filter icon | 无事件 | P1 Filter Drawer，筛选 `status/side/rule/level/from/to` |
| Trading 监控池 | 批量启用 | 无事件 | `PATCH /monitoring-pool/items/batch` |
| Dashboard 顶栏 | 导出日报 | 无事件 | `POST /exports/daily-report` |
| 所有表格 | 无分页控件 | 全量 mock map | P0 API 必须返回分页结构，前端后续补分页控件 |

---

# 9. Dialog / Drawer / Tooltip / Tabs 隐藏交互

- Tabs：
  - ReportDetail：`overview` / `business` / `financial` / `news`。
  - History：`holdings` / `orders` / `risk` / `logs`。
- Tooltip：
  - TopBar 数据源延迟说明。
  - TradingConsole 最新信号原因。
- Dialog / Drawer：当前代码没有 Dialog/Drawer 组件；但以下交互建议后续补：
  - History 筛选 Drawer。
  - 订单详情 Drawer。
  - 风控记录详情 Drawer。
  - 策略配置 Dialog/Drawer。
  - Clean Logs 二次确认 Dialog。

---

# 10. 当前写死数据：应改为后端返回

| 位置 | 写死内容 | 应归属 API |
|---|---|---|
| Dashboard KPI | 24、8、2、¥1,024,530、+2.45% | `GET /dashboard/overview` |
| Dashboard 今日事项 | 2、0、1、3 | `GET /dashboard/overview.tasks` |
| Dashboard 快速研究统计 | 已完成 124、待处理 0 | `GET /dashboard/overview.quickResearchStats` |
| Dashboard 风险提示文案 | 固定文案 | 可后端配置或前端常量；建议后端返回版本化 disclaimer |
| Dashboard 监控池表 | 使用 `MOCK_RESEARCH_RECORDS` | `GET /dashboard/monitoring-summary` |
| TopBar 时间/状态/延迟/交易日 | `new Date()`、运行中、Tushare 35ms、SH/SZ 交易日 | `GET /system/status` + `GET /data-sources/health` |
| Sidebar 数据源/AI 服务 | 已连接/正常 | `GET /system/status` |
| Research 研究统计 | 142、38、常用板块 | `GET /research/stats` |
| Research 任务进度 | setInterval 模拟 | `GET /research/tasks/{taskId}` |
| Research 完成跳转 | 固定 `/research/600519` | 后端返回 `reportId/code/redirectTo` |
| ReportDetail 7 日走势 | `CHART_DATA` | `GET /stocks/{code}/price-bars?range=7d` 或报告详情内返回 |
| ReportDetail AI 结论/Key Insights/风险 | 写死模板 | `research_report` |
| ReportDetail 主营业务占比 | 茅台酒 88%、系列酒 11.5%、其他 0.5% | `research_report.businessSegments` |
| ReportDetail 新闻公告 | 写死 3 条 | `research_report.newsItems` 或 `GET /stocks/{code}/news` |
| ReportDetail 页脚 | 数据源、10min、2024-Q1 | 报告详情元数据 |
| Trading 风控状态 | 写死 5 条规则 | `GET /risk/system-status` |
| Trading 链路追踪 | 写死步骤与状态 | `GET /execution-traces/latest` |
| Trading 手动巡检 summary | setTimeout 后写死 120/3/2/1/2/1/1.2s | `POST /paper-trading/runs` 返回 summary |
| Trading refresh 时间 | `15:00:25` | 监控池 API `lastRefreshedAt` |
| History 账户摘要 | 1,250,300 等 | `GET /portfolio/account-summary` |
| History logs | `MOCK_LOGS.concat(MOCK_LOGS)` | `GET /logs` |

---

# 11. Endpoint 优先级总表

## P0：第一版必须

| Endpoint | Method | 用途 |
|---|---|---|
| `/dashboard/overview` | GET | 首页 KPI/事项/系统摘要 |
| `/dashboard/monitoring-summary` | GET | 首页监控池摘要 |
| `/system/status` | GET | 顶栏/侧栏系统状态 |
| `/data-sources/health` | GET | 数据源健康度 |
| `/research/tasks` | POST | 创建 AI 研究任务 |
| `/research/tasks/{taskId}` | GET | 查询研究进度 |
| `/research/records` | GET | 研究记录列表 |
| `/research/stats` | GET | 研究统计 |
| `/research/reports/by-code/{code}` | GET | 报告详情 |
| `/watchlist/items` | POST | 加入观察池 |
| `/monitoring-pool/items` | GET/POST | 查询/新增监控项 |
| `/monitoring-pool/items/{id}` | PATCH | 启停单个监控项 |
| `/paper-trading/engine` | GET/PATCH | 模拟交易引擎状态/启停 |
| `/paper-trading/runs` | POST | 手动/自动巡检一次 |
| `/risk/system-status` | GET | 系统级风控状态 |
| `/execution-traces/latest` | GET | 最新链路追踪 |
| `/portfolio/account-summary` | GET | 模拟账户摘要 |
| `/portfolio/positions` | GET | 模拟持仓 |
| `/orders` | GET/POST | 查询/创建模拟订单（创建必须由风控通过后执行） |
| `/risk-checks` | GET/POST | 风控审计/检查 |
| `/logs` | GET | 系统日志 |

## P1：增强体验

| Endpoint | Method | 用途 |
|---|---|---|
| `/research/records/export` | GET | 研究记录导出 |
| `/exports/daily-report` | POST | 导出日报 |
| `/monitoring-pool/items/batch` | PATCH | 批量启停 |
| `/execution-traces` | GET | 按监控项/订单/Run 查询链路 |
| `/stocks/{code}/price-bars` | GET | 图表走势独立接口 |
| `/stocks/{code}/news` | GET | 新闻公告独立接口 |
| `/orders/export` | GET | 订单导出 |
| `/risk-checks/export` | GET | 风控导出 |
| `/logs/export` | GET | 日志导出 |

## P2：后续

| Endpoint | Method | 用途 |
|---|---|---|
| `/settings` | GET/PATCH | 系统设置 |
| `/research/logs/cleanup` | POST | 清理研究日志，需二次确认 |
| `/strategies` | GET/POST/PATCH | 策略配置管理 |
| `/orders/{id}` | GET | 订单详情 |
| `/risk-checks/{id}` | GET | 风控详情 |

---

# 12. 数据库实体建议

```text
stock
market_quote
price_bar
financial_snapshot
news_item
announcement
research_task
research_report
research_report_section
watchlist_item
strategy
monitoring_item
paper_trading_engine_state
paper_trading_run
signal
risk_check
paper_order
paper_execution
paper_account
account_snapshot
position
execution_trace
system_log
trade_log
data_source_health
daily_export
```

关键关系：

```text
monitoring_item -> strategy
paper_trading_run -> execution_trace
execution_trace -> signal -> risk_check -> paper_order -> paper_execution -> position -> trade_log
research_task -> research_report -> stock
watchlist_item -> stock
position -> paper_account + stock
system_log.relId -> 任意业务实体 ID
```

---

# 13. 实现边界与安全要求

1. 第一版只允许 `PAPER_TRADING_ONLY`，任何订单/成交/持仓均为模拟数据。
2. AI 输出只进入 `research_report`，不得直接创建订单。
3. 策略只能生成 `signal`，交易动作必须经过后端风控。
4. `risk_check.status = BLOCKED` 时不得创建 `paper_order`。
5. 所有 `order`、`execution`、`position` 更新必须关联 `traceId` 或 `runId`，并写 `trade_log/system_log`。
6. 前端显示的红涨绿跌符合 A 股习惯；API 只返回数值，不返回颜色。
7. 后端时间统一 ISO-8601，包含时区；前端负责格式化。
