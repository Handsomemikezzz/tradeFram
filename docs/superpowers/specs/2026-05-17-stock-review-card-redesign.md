# 标的复盘卡片改造设计

## 背景

当前「交易复盘」页面以单次交易行为或观察决策为主记录对象。这个模型能记录买入、卖出、想买未买等动作，但会把复盘拆得过碎。买入当天通常无法判断一笔交易的完整质量，卖出后才更适合总结买入理由、持有过程、卖出逻辑、盈亏、纪律和后续规则。

本次改造将现有交易复盘页面的主工作流从「新增单次复盘记录」调整为「建立某只股票的一张复盘卡片」。页面入口、路由和导航仍使用现有 `/reviews` 与「交易复盘」入口，不新增独立模块。

## 目标

- 在现有交易复盘页面内支持按股票建立复盘卡片。
- 一张卡片表示某只股票的一段完整观察或交易周期。
- 用户可以在买入或开始关注时建卡，后续按需追加过程记录。
- 用户手动结束卡片后填写卖出逻辑、最终盈亏、纪律和反思。
- 避免强制用户每天填写，也避免在买入当天要求写最终复盘结论。

## 非目标

- 不接真实券商或真实成交导入。
- 不自动判断一张卡片是否应该结束。
- 不在第一版重做周复盘统计。
- 不立刻删除旧的 `review_entry` 数据模型。
- 不提供交易建议或 AI 投资判断。

## 核心模型

### StockReviewCard

`StockReviewCard` 是新的主对象，表示某只股票的一段复盘周期。

字段：

- `id`
- `status`: `OPEN` 或 `CLOSED`
- `code`: 股票代码
- `name`: 股票名称
- `startDate`: 建卡或开始关注日期
- `endDate`: 结束日期，可为空
- `initialAction`: `BUY`、`WATCH` 或 `PLAN_BUY`
- `initialPositionContext`: 初始仓位语境
- `initialPlanStatus`: 初始计划状态，沿用计划内、计划外、临盘调整、观察未执行
- `initialReasonText`: 买入或关注理由
- `expectedMoveText`: 预期逻辑
- `originalPlanText`: 原计划，包括止损、止盈、卖出条件或观察条件
- `initialEmotionTags`: 建卡时的情绪标签
- `problemTags`: 结束后主要问题归因标签
- `sellReasonText`: 卖出或结束逻辑
- `pnlText`: 最终盈亏，第一版允许手填文本
- `followedPlan`: 是否按原计划执行，可为空
- `disciplineScore`: 纪律评分，1 到 5，可为空直到结束
- `didWellText`: 做对了什么
- `didWrongText`: 做错了什么
- `reflectionText`: 后续反思
- `ruleText`: 下次可执行规则
- `createdAt`
- `updatedAt`

### StockReviewEvent

`StockReviewEvent` 是卡片内的过程时间线。它用于记录持有、加仓、减仓、卖出、计划变化、情绪波动等中间节点。

字段：

- `id`
- `cardId`
- `eventDate`
- `eventType`: `HOLD`、`ADD`、`REDUCE`、`SELL`、`PLAN_CHANGE`、`EMOTION`、`OBSERVATION`
- `title`: 事件标题
- `reasonText`: 当时决策理由或观察
- `deviatedFromPlan`: 是否偏离原计划
- `emotionTags`: 情绪标签
- `problemTags`: 问题归因标签
- `createdAt`
- `updatedAt`

过程事件是可选记录。用户持有期间没有值得记录的内容时，不需要每天补一条。

### WeeklyReview

现有 `WeeklyReview` 暂时保留。第一版不强制把周复盘改成基于卡片聚合，避免同时改动过大。后续可以扩展为同时聚合进行中卡片、已结束卡片和过程事件。

## 页面设计

现有 `src/pages/Reviews.tsx` 继续作为交易复盘页面，但主内容改为标的复盘卡片工作流。

### 顶部概览

顶部标题仍为「交易复盘」，说明文案调整为围绕股票周期复盘，例如：

`为每只股票建立一张复盘卡片，记录买入逻辑、持有过程、卖出结果和纪律反思。`

顶部统计第一版展示轻量指标：

- 进行中卡片数
- 本周新建卡片数
- 本周结束卡片数
- 低纪律结束卡片数

### 卡片列表

默认展示 `OPEN` 进行中卡片。支持筛选：

- 进行中、已结束、全部
- 股票代码或名称
- 开始日期范围
- 问题标签
- 计划状态

每张卡片展示：

- 股票代码和名称
- 状态
- 开始日期
- 持续天数
- 初始动作
- 初始仓位
- 买入或关注理由摘要
- 最近一条过程事件
- 结束后展示盈亏和纪律评分

### 新建卡片

现有「新增复盘记录」区域改为「新建标的复盘」。

建卡表单只收集初始阶段信息：

- 股票代码
- 股票名称
- 开始日期
- 初始动作
- 初始仓位
- 初始计划状态
- 买入或关注理由
- 预期逻辑
- 原计划
- 情绪标签

建卡时不要求填写盘后反思、一句话结论、下次动作和结果验证。

### 卡片详情

点击卡片后在当前页面内打开详情区域或抽屉。第一版优先使用页面内详情，减少路由和导航复杂度。

详情分三段：

- 初始计划：展示并允许编辑买入理由、预期逻辑、原计划、初始情绪和计划状态。
- 过程时间线：展示事件列表，并提供「追加记录」。
- 结束复盘：提供「结束复盘」表单，填写卖出逻辑、盈亏、是否按计划、纪律评分、做对、做错、反思和下次规则。

卡片动作：

- `追加记录`
- `记录卖出`
- `结束复盘`
- `重新打开`

`记录卖出` 可以创建一条 `SELL` 事件，但不强制立即结束卡片。`结束复盘` 才将卡片状态改为 `CLOSED`。

## 后端接口

新增 review card 相关 API，仍挂在现有 `/api/v1/reviews` 命名空间。

- `POST /api/v1/reviews/cards`: 创建标的复盘卡片
- `GET /api/v1/reviews/cards`: 查询卡片列表
- `GET /api/v1/reviews/cards/{cardId}`: 获取卡片详情
- `PATCH /api/v1/reviews/cards/{cardId}`: 更新卡片
- `POST /api/v1/reviews/cards/{cardId}/events`: 追加过程事件
- `PATCH /api/v1/reviews/cards/{cardId}/events/{eventId}`: 更新过程事件
- `DELETE /api/v1/reviews/cards/{cardId}/events/{eventId}`: 删除过程事件
- `POST /api/v1/reviews/cards/{cardId}/close`: 结束复盘
- `POST /api/v1/reviews/cards/{cardId}/reopen`: 重新打开卡片
- `GET /api/v1/reviews/cards/stats`: 获取卡片概览统计

旧的 `/reviews/entries` API 第一版保留，避免破坏已有代码和测试。前端页面切换到新 API 后，旧 API 可暂时作为兼容层存在。

## 数据迁移

新增表：

- `stock_review_cards`
- `stock_review_events`

不删除旧表：

- `review_entry`
- `weekly_review`

第一版不做自动迁移。原因是旧 `review_entry` 表示单次行为，无法可靠推断哪些行为属于同一张股票卡片。后续如需迁移，可提供人工选择或按股票代码和日期粗分组的辅助迁移工具。

## 前端改动范围

保留：

- `src/pages/Reviews.tsx`
- 侧边栏「交易复盘」入口
- `/reviews` 路由

新增或重写：

- `src/components/reviews/CardForm.tsx`
- `src/components/reviews/CardList.tsx`
- `src/components/reviews/CardDetail.tsx`
- `src/components/reviews/EventForm.tsx`
- `src/components/reviews/EventTimeline.tsx`
- `src/services/api/reviewCardApi.ts`
- `src/services/api/types.ts` 中新增 card/event 类型

暂时保留但页面第一版不再作为主工作流使用：

- `EntryForm.tsx`
- `EntryList.tsx`
- 旧 `reviewApi` entry 方法
- `WeeklyWorkbench.tsx`

## 测试策略

后端测试：

- 创建卡片。
- 列出进行中和已结束卡片。
- 更新卡片初始计划。
- 追加过程事件。
- 记录卖出事件。
- 结束复盘并写入纪律、盈亏和反思。
- 重新打开卡片。
- 未来日期校验。
- 纪律评分范围校验。

前端验证：

- 进入现有交易复盘页面后看到卡片工作流。
- 可以新建股票卡片。
- 可以打开卡片详情。
- 可以追加持有或计划变化记录。
- 可以结束复盘。
- 进行中和已结束筛选正确。

## 验收标准

- 用户仍从现有侧边栏「交易复盘」进入 `/reviews` 页面。
- 页面主入口从「新增复盘记录」变为「新建标的复盘」。
- 用户今天买入一只股票后，可以为该股票建立卡片并填写买入理由、预期逻辑和原计划。
- 持有期间可以不写，也可以追加过程记录。
- 用户卖出后可以填写卖出逻辑、盈亏、纪律评分、做对做错、反思和下次规则，并手动结束卡片。
- 已结束卡片可以重新打开。
- 旧的单次复盘接口和数据不被删除。
