# 交易复盘工作台设计

## 背景

当前系统已经有股票研究、连板断板监控、数据健康和模拟交易控制台等模块。用户现有复盘主要写在 Obsidian Markdown 中，内容以个人交易行为、情绪、纪律反思为主，但容易变成流水账，难以沉淀重复错误、有效动作和交易规则。

长期目标是帮助用户学习金融市场并逐步形成个人交易逻辑。第一版不做 AI 投研、不做交易建议，也不接真实券商；先把交易行为和观察决策结构化，形成可统计、可周复盘的样本库。

## 目标

- 新增 Web 内的「交易复盘」模块。
- 支持手动创建复盘记录，不依赖真实成交或模拟订单导入。
- 记录分为「交易行为」和「观察决策」两类。
- 使用标准复杂度字段，选择项为主，并允许补充文本。
- 表单提供浅色提示文案，帮助用户填写原因、情绪、归因和下次动作。
- 提供错误统计，暴露重复问题、情绪触发器、计划外行为和纪律评分。
- 提供周复盘工作台，把一周记录聚合成可总结材料。

## 非目标

- 不接 AI 自动总结。
- 不接真实交易。
- 不从模拟交易订单自动导入。
- 不计算真实收益归因。
- 不提供交易建议。
- 不做复杂图表。
- 不做完整规则库生命周期；第一版只在周复盘中保留「本周可沉淀规则」文本区。
- 不做个股或板块时间线。

## 产品边界

新增模块命名为「交易复盘」。它服务于从交易行为和观察决策中提炼个人交易系统，而不是判断买卖对错。

第一版包含：

- 手动新增、编辑、删除复盘记录。
- 记录列表、详情和筛选。
- 本周/本月错误统计。
- 周复盘工作台。
- 周复盘总结保存和再次编辑。

第一版记录对象以行为为中心，而不是按交易日强制创建日报。这样可以覆盖真实成交行为，也可以覆盖想买未买、想卖未卖、撤单、忍住没动等未执行决策。

## 核心数据模型

### ReviewEntry

每条 `ReviewEntry` 表示一次交易行为或观察决策。

字段：

- `id`
- `entryType`: `TRADE_ACTION` 或 `OBSERVATION_DECISION`
- `actionType`: 行为类型
- `tradeDate`: 发生日期
- `code`: 股票代码，可为空
- `name`: 股票名称，可为空
- `sectorTags`: 板块/题材标签数组
- `positionContext`: 仓位语境
- `planStatus`: 计划状态
- `emotionTags`: 情绪标签数组
- `problemTags`: 问题归因标签数组
- `reasonText`: 当时为什么这么做
- `reflectionText`: 盘后怎么看这件事
- `conclusionText`: 一句话复盘结论，用于列表摘要和快速回看
- `nextActionText`: 下次遇到类似情况怎么做
- `disciplineScore`: 纪律评分，1 到 5
- `outcomeText`: 结果或后续验证
- `createdAt`
- `updatedAt`

行为类型按记录类型区分：

- 交易行为：买入、卖出、加仓、减仓、清仓、做 T。
- 观察决策：想买未买、想卖未卖、撤单、忍住没动、计划观察。

常用选择项：

- 仓位语境：空仓、轻仓、半仓、重仓、满仓、持有中。
- 计划状态：计划内、计划外、临盘调整、观察未执行。
- 情绪标签：怕踏空、急躁、犹豫、贪便宜、想回本、冷静、防守。
- 问题归因：策略问题、判断问题、执行问题、情绪问题、仓位问题、无明显问题。

文本字段必须保留自由表达空间。选择项用于统计，文本用于保留真实语境。

`code` 和 `name` 的关系：

- `code` 允许为空，用于记录板块或市场层面的观察。
- `code` 非空时，前端可以尝试从已有股票数据中带出 `name`，但第一版不强制校验股票必须存在于本地 stock 表。
- `name` 允许用户手动修正，避免本地股票缓存缺失时无法记录复盘。

### WeeklyReview

每条 `WeeklyReview` 表示一周的结构化总结，可以由系统聚合记录后手动保存。

字段：

- `id`
- `weekStart`
- `weekEnd`
- `summaryText`: 本周总评
- `repeatedMistakesText`: 本周重复错误
- `effectiveActionsText`: 本周做对的动作
- `emotionPatternText`: 本周情绪模式
- `nextWeekFocusText`: 下周重点
- `ruleCandidatesText`: 本周可沉淀规则
- `linkedEntryIds`: 关联的复盘记录 ID 数组
- `createdAt`
- `updatedAt`

## 页面设计

侧边栏新增「交易复盘」入口。

页面由三个区域组成。

### 顶部概览

展示本周关键指标：

- 统计起止日期
- 本周记录数
- 交易行为数
- 观察决策数
- 计划外次数
- 最高频问题归因
- 最高频情绪标签
- 平均纪律评分

这些指标用于快速定位本周主要问题，不评价交易好坏。后端统计响应应返回实际 `startDate` 和 `endDate`，前端展示该范围，避免节假日或空周时用户误解统计边界。

### 复盘记录区

筛选项：

- 时间范围
- 记录类型
- 行为类型
- 股票代码
- 板块标签
- 情绪标签
- 问题归因
- 计划状态

列表展示：

- 日期
- 类型/行为
- 股票或板块
- 计划状态
- 情绪标签
- 问题归因
- 纪律评分
- 一句话复盘结论，即 `conclusionText`

新增/编辑表单分组：

- 发生了什么：类型、行为、日期、股票/板块、仓位语境
- 为什么这么做：计划状态、理由文本
- 当时状态：情绪标签、纪律评分
- 复盘归因：问题标签、反思文本
- 下次动作：结果验证、下一次规则化动作

文本框使用启发式 placeholder：

- 理由文本：`例：看到神剑封板后，担心航天后排补涨，临盘追入航发中。`
- 计划状态说明：`盘前/昨日是否已经想好？还是盘中临时决定？`
- 情绪状态：`例：怕踏空、急躁、犹豫、想回本，或冷静执行。`
- 复盘归因：`这次主要是策略问题、判断问题、执行问题，还是情绪问题？`
- 下次动作：`写成一句未来可执行的话，例如：缩量反弹不加仓。`

### 周复盘工作台

用户选择一周后，系统展示：

- 该周记录清单
- 问题归因统计
- 情绪标签统计
- 计划外行为列表
- 低纪律评分记录
- 高频股票/板块

周复盘工作台与主列表通过 Tab 区分。主列表用于创建、筛选、编辑和删除记录；周复盘工作台用于只读聚合和填写周总结。工作台中的记录清单可以复用同一个详情抽屉查看记录，但不承担批量管理职责。

下方提供手动填写区域：

- 本周重复错误
- 本周做对的动作
- 本周情绪模式
- 下周重点
- 本周可沉淀规则

提示示例：

- 本周重复错误：`例：无操作日后更容易急于出手；看到龙头涨停后追后排。`
- 本周做对动作：`例：大盘不明朗时减仓；忍住没有接飞刀。`
- 本周情绪模式：`例：怕踏空主要出现在板块龙头封板后。`
- 下周重点：`例：只做计划内交易；后排不放量不加仓。`
- 可沉淀规则：`例：缩量反弹不视为板块启动；高开回落不追后排。`

## 统计逻辑

统计只做确定性聚合，不做 AI 推理。

按所选时间范围返回：

- 记录总数
- 交易行为数
- 观察决策数
- 各计划状态数量
- 各问题归因出现次数
- 各情绪标签出现次数
- 平均纪律评分
- 低纪律评分记录数量，默认 `disciplineScore <= 2`
- 计划外行为占比

纪律评分阈值第一版由后端常量控制，默认 `LOW_DISCIPLINE_SCORE_THRESHOLD = 2`。统计响应应返回该阈值，前端展示时标注「低纪律 <= 2」。

统计空值处理：

- 高频股票统计跳过空 `code`。
- 高频板块统计跳过空 `sectorTags`。
- 情绪和问题标签为空数组时不计入频次统计。
- 平均纪律评分只统计已填写 `disciplineScore` 的记录；第一版创建记录时该字段必填。

周复盘工作台额外聚合：

- `计划外记录`: `planStatus` 为计划外或临盘调整的记录
- `低纪律记录`: 纪律评分低于阈值的记录
- `重复问题`: 本周出现次数最多的问题归因
- `情绪触发器`: 本周出现次数最多的情绪标签
- `高频标的/板块`: 本周反复出现的代码和板块标签
- `可复盘样本`: 本周所有记录按日期倒序展示

## 后端设计

新增 router：`backend/app/routers/reviews.py`。

沿用当前项目约定：

- Review 相关 Pydantic 请求/响应模型先写入 `backend/app/schemas.py`，保持与现有 router 一致。
- Review SQLAlchemy 模型写入 `backend/app/models.py`。
- Router 在 `backend/app/main.py` 中显式 import 并加入 `include_router` 列表。
- ID 使用 `utils.new_id(prefix)`，建议 `review_entries` 使用 `rv` 前缀，`weekly_reviews` 使用 `wr` 前缀。
- 响应继续使用 `utils.ok()` 封装，错误继续使用 `utils.api_error()`。

新增接口：

- `POST /api/v1/reviews/entries`: 创建复盘记录
- `GET /api/v1/reviews/entries`: 列表查询，支持日期、类型、标签、股票代码筛选
- `GET /api/v1/reviews/entries/{id}`: 获取详情
- `PATCH /api/v1/reviews/entries/{id}`: 更新记录
- `DELETE /api/v1/reviews/entries/{id}`: 删除记录
- `GET /api/v1/reviews/stats`: 按时间范围返回错误统计
- `GET /api/v1/reviews/weeks/{weekStart}`: 获取某周工作台数据
- `PUT /api/v1/reviews/weeks/{weekStart}`: 保存或更新周复盘

接口参数约定：

- `weekStart` 使用 ISO 日期字符串 `YYYY-MM-DD`，并表示该周周一。
- 前端用本地工具函数计算周一日期，不引入 date-fns 或 dayjs。
- 标签筛选使用多值 query 参数，例如 `?emotionTags=怕踏空&emotionTags=急躁`。现有 `apiClient.buildUrl` 已支持数组 append，后端使用 list 参数接收。
- 日期筛选使用 `startDate` 和 `endDate`，格式为 `YYYY-MM-DD`。

新增数据库表：

- `review_entries`
- `weekly_reviews`

JSON 数组字段用于存储标签和关联 ID。SQLite 中可先沿用项目现有 JSON 存储方式，接口层负责返回数组。

数据库变更必须提交 Alembic migration。新增 Model 后执行 autogenerate，检查迁移文件只包含 `review_entries` 和 `weekly_reviews` 相关表结构，再提交迁移文件。`init_db()` 的 `Base.metadata.create_all()` 只作为本地初始化兜底，不能替代迁移文件。

## 前端设计

新增文件：

- `src/pages/Reviews.tsx`
- `src/services/api/reviewApi.ts`
- `src/components/reviews/StatsOverview.tsx`
- `src/components/reviews/EntryForm.tsx`
- `src/components/reviews/EntryList.tsx`
- `src/components/reviews/WeeklyWorkbench.tsx`
- `src/components/reviews/MultiTagInput.tsx`

更新文件：

- `src/App.tsx`: 注册 `/reviews` 路由
- `src/components/layout/Sidebar.tsx`: 增加「交易复盘」入口
- `src/services/api/types.ts`: 增加 review 类型
- `src/services/api/index.ts`: 导出 review API
- `src/services/api/client.ts`: 增加 `put` 方法，以支持 `PUT /reviews/weeks/{weekStart}`

第一版 UI 使用当前项目已有的 card、table、button、input、badge、tabs、switch 等组件风格。统计展示先用数字卡、标签频次列表和简单条形，不引入新图表依赖。

选择控件约定：

- 第一版不新增外部依赖。
- 单选字段可以使用项目风格封装的原生 `select` 或按钮组。
- 多选标签使用自定义 `MultiTagInput`，支持预设标签点击、自由输入、删除标签。
- 情绪标签、问题归因和板块标签都使用 `MultiTagInput`，避免原生多选控件体验差。

## 错误处理

- 必填字段缺失时，前端提示具体字段。
- `tradeDate` 不能为空，默认今天。
- `tradeDate` 不能晚于今天。
- `entryType` 决定可选 `actionType`。
- `disciplineScore` 只能是 1 到 5。
- `weekStart` 必须是周一的 `YYYY-MM-DD` 日期。
- 股票代码允许为空。
- 删除记录需要二次确认。
- 后端使用统一错误结构，前端 toast 展示错误信息。

## 测试计划

后端测试：

- 创建交易行为记录。
- 创建观察决策记录。
- 更新记录。
- 删除记录。
- 按日期、类型、股票代码筛选。
- 统计问题归因和情绪标签。
- 统计计划外行为和平均纪律评分。
- 周复盘工作台聚合。
- 保存和更新周复盘。
- JSON 标签字段覆盖空数组、多标签和筛选。
- `disciplineScore` 为 0 或 6 时返回 422。
- `tradeDate` 为未来日期时返回 422。
- 标签筛选支持多值 query 参数。
- 高频股票和高频板块统计跳过空值。
- `weekStart` 不是周一时返回明确校验错误。
- `linkedEntryIds` 包含不存在记录 ID 时返回明确校验错误。
- `sectorTags` 超过上限时返回校验错误；第一版建议单条记录最多 10 个板块标签。

前端验证：

- `npm run build` 通过。
- 可以从侧边栏进入交易复盘页。
- 可以新增交易行为。
- 可以新增观察决策。
- 表单 placeholder 能引导填写。
- 列表能按时间、类型、股票代码筛选。
- 统计随记录变化。
- 周复盘能聚合记录并保存总结。

## 验收标准

- 侧边栏出现「交易复盘」入口。
- 用户可以手动创建一条交易行为复盘。
- 用户可以手动创建一条观察决策复盘。
- 表单包含浅色提示文案。
- 列表能按时间、类型、股票代码筛选。
- 页面能看到本周/本月错误统计，包括问题归因、情绪标签、计划外次数、平均纪律评分。
- 周复盘工作台能选择一周，看到该周记录和聚合提示。
- 周复盘总结能保存和再次编辑。
- 后端测试通过。
- 前端构建通过。

## 后续扩展

第一版稳定后，可以考虑：

- 将周复盘中的规则候选独立成规则库。
- 支持 AI 辅助周/月总结，但只做归纳，不做买卖建议。
- 支持从模拟交易订单导入成交行为。
- 支持个股/板块时间线。
- 支持导出 Markdown 到 Obsidian。
