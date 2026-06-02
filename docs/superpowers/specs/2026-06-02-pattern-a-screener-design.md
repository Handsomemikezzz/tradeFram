# 走势 A 选股设计

日期：2026-06-02  
状态：已确认设计，待实现  
范围：新增“选股”页面和走势 A 策略，保留现有断板能力

## 背景

当前系统已有“连板断板监控”页面和全市场 warehouse 日 K 数据。warehouse 的 `daily_bars` 已包含 `open/high/low/close/volume/amount`，但前端断板页目前只通过 `post-break-bars` 展示断板后收盘价折线，不能直接展示蜡烛图，也没有全市场形态扫描。

用户目标是把一种价格行为形态“走势 A”做成每日选股结果，避免人工扫描主板所有股票。第一版重点是盘后日 K 选股：系统筛出候选，用户在页面里用 K 线验证。

## 目标

- 将侧边栏入口从“连板断板”升级为“选股”。
- 新页面默认展示“走势 A”，并保留现有“断板”功能作为同页 Tab。
- 生成并保存走势 A 每日快照，支持查看当日已确认和待确认候选。
- 对每只候选展示近 30 个交易日蜡烛图、MA5/MA10/MA20、关键阴线、企稳区间和确认阳线。
- 支持将走势 A 候选加入观察池，已在观察池的股票显示“已观察”。
- 保持断板现有数据层、接口和行为不迁移。

## 非目标

- 不做盘中实时信号。
- 不接入真实交易、真实券商或 monitoring 自动交易链路。
- 不迁移断板到通用 screener 表。
- 不暴露走势 A 规则参数给前端。
- 不做异步任务框架。
- 不做前复权全市场同步。
- 不做分页、虚拟列表或自动历史清理。
- 不在 MVP 中为全市场扫描引入前复权数据同步；原始日 K 的除权风险通过异常跳空过滤降低。

## 页面与路由

正式入口为 `/screeners`。旧 `/limit-up-breaks` 保留并重定向到 `/screeners`，避免旧链接失效。

侧边栏将“连板断板”改为“选股”。页面外层包含：

- 页面标题“选股”。
- 共享 `tradeDate` 控件，表示查看哪个交易日的策略结果。
- Tab：`走势 A`、`断板`，默认打开 `走势 A`。

断板 Tab：

- 保留现有断板页面行为。
- 连板门槛、查询、生成快照仍放在断板 Tab 内。
- 断板数据表、断板后走势展开方式不改变。

走势 A Tab：

- 顶部统计显示全量快照统计：扫描股票数、过滤后股票数、已确认数、待确认数、数据覆盖率、更新时间。
- 状态筛选默认“已确认”，可切换“全部 / 待确认”。
- 排序为已确认优先，然后按综合评分降序。
- 主体使用左侧候选列表 + 右侧固定 K 线验证区。
- 小屏基础响应式：列表在上，详情图表在下。
- 查询无快照时显示“暂无快照，可点击生成”，不自动生成。
- 生成快照时 loading 文案说明“正在扫描主板非 ST 股票，可能需要几十秒”。
- 生成失败时直接显示错误和数据健康提示，不将数据问题伪装成空结果。

候选列表字段：

- 股票名称。
- `code · industry` 小字。
- 状态：`已确认` 或 `待确认`。
- 信号/观察日期。
- 突破涨幅。
- 综合评分。
- 2-3 个原因标签，如“突破关键阴线”“MA5拐头”“放量突破”。
- 观察池按钮或“已观察”徽标。

右侧详情：

- 默认选中当前筛选下评分最高的候选。
- 切换状态筛选后自动选中新列表第一只。
- 详情加载失败只影响右侧，显示错误和重试按钮。
- 图上只标核心价格行为：关键阴线、企稳区间、确认阳线。
- 图下展示总分和价格行为/均线/量能分项、规则命中解释、量能/均线标签。
- 折叠规则摘要默认收起，内含非投资建议提示。

## K 线图库

前端新增 `lightweight-charts` 依赖。

选择理由：

- TradingView 维护，开源，Apache 2.0 许可。
- 官方文档支持 `CandlestickSeries`，数据格式直接包含 `open/high/low/close/time`。
- 足够专业，但不把页面变成重型行情终端。
- 与当前 React/Vite 项目集成成本低。

实现要求：

- 使用后端返回的 OHLCV 和 MA 值，前端只负责展示。
- A 股上涨使用红系，下跌使用绿系，保持现有项目视觉习惯。
- 注意包的 attribution 要求，按 npm 包说明在图表或页面中保留 TradingView 归属链接。

参考：

- https://www.tradingview.com/lightweight-charts/
- https://tradingview.github.io/lightweight-charts/docs/5.0
- https://tradingview.github.io/lightweight-charts/docs/series-types
- https://www.npmjs.com/package/lightweight-charts

## 走势 A 规则

第一版只做盘后日 K 选股，使用 warehouse 的未复权/原始日 K，快照记录 `priceAdjustment = raw`。

除权/异常跳空过滤：

- 第一版不直接引入全市场前复权同步，也不在扫描时逐只调用外部前复权接口。
- 扫描服务在信号窗口内检测疑似除权或异常跳空日，避免把原始日 K 的除权缺口识别成关键阴线、下跌段或确认结构。
- 若某股票在近 30 个交易日信号窗口内出现疑似除权/异常跳空，则该股票不进入走势 A 候选，并在扫描统计中计入异常过滤数量。
- 初始判定使用后端常量：相邻交易日开盘相对前收的绝对跳空超过主板正常涨跌停边界缓冲，同时日内实体/振幅较小，或收盘涨跌幅与日 K 实体方向明显背离。
- 该规则只作为 MVP 的防假信号机制；后续若需要更干净的形态识别，再新增前复权全市场同步和 `strategyVersion`。

默认日期口径：

- 使用最近一个已完整同步的交易日。
- 如果当天 18:00 后数据完整，则筛当天；否则筛上一交易日。
- 前端仍支持手动选择日期。

股票池：

- 主板非 ST、active。
- 沪市代码：`600/601/603/605`。
- 深市代码：`000/001/002/003`。
- 排除 `*ST/ST/S*ST`。
- 这套逻辑抽为共享工具，供断板、数据健康、走势 A 复用。

基础过滤：

- 上市满 60 个交易日。
- 最近 30 个交易日至少 25 根有效 K 线。
- 近 20 日平均成交额不低于 1 亿。
- 全局主板非 ST 覆盖率沿用断板的 99.5% 阈值。

关键阴线：

- 在最近 10 个交易日的左侧下跌段里，选择实体最大的一根阴线。
- 阴线要求 `close < open`。
- 实体上沿为 `max(open, close)`，实体下沿为 `min(open, close)`。
- 左侧下跌用方向型判断：关键阴线之前 5-10 个交易日收盘价整体走低，MA5 斜率向下，不要求固定跌幅。

已确认：

- 目标交易日必须就是确认日。
- 关键阴线后 1-5 个交易日内出现确认阳线。
- 当日收盘相对上一交易日收盘涨幅不低于 3%。
- 阳线实体占全天振幅不低于 50%。
- 收盘位于全天振幅上半区。
- 收盘高于关键阴线实体上沿。
- 若 `high == low`，该 K 线不能作为确认阳线。

待确认：

- 截至目标日仍有效，不要求目标日当天新出现某种 K 线。
- 关键阴线后 3-5 个交易日处于企稳区间。
- 企稳期不明显创新低。
- MA5 走平或拐头：最近 MA5 大于等于前一日 MA5，或最近两日 MA5 下跌幅度不超过 0.3%。
- 企稳区间至少出现一种止跌 K 线：小阳、十字星、缩量阴。
- 若企稳期间跌破关键阴线低点，或 MA5 继续明显下行，则失效。

止跌 K 线定义：

- 小阳：`close > open` 且涨跌幅在 0-2%。
- 十字星：实体/振幅不高于 20%。
- 缩量阴：阴线且成交量低于近 5 日均量。

均线标签：

- 不使用泛化“金叉”标签。
- 使用更具体标签：`MA5拐头`、`MA5站上MA10`、`MA多头排列`。

量能标签：

- `放量突破`：确认日成交量高于近 5 日均量。
- `量能改善`：近 3 日均量高于近 5 日均量。

评分：

- 100 分整数制，后端四舍五入。
- 价格行为 60 分。
- 均线 20 分。
- 量能 20 分。
- 价格行为决定入池，均线和量能只作为加分与标签。
- 详情展示总分和三项分数，列表只展示总分。

## 数据模型

新增 `ScreenerSnapshot`：

- `id`
- `trade_date`
- `strategy_type`
- `strategy_name`
- `strategy_version`
- `provider`
- `price_adjustment`
- `criteria` JSON
- `scan_count`
- `eligible_count`
- `confirmed_count`
- `pending_count`
- `coverage`
- `generated_at`
- `updated_at`

唯一约束：

`trade_date + strategy_type + strategy_version + provider`

新增 `ScreenerItem`：

- `id`
- `snapshot_id`
- `trade_date`
- `code`
- `name`
- `industry`
- `status`
- `signal_date`
- `score`
- `price_action_score`
- `moving_average_score`
- `volume_score`
- `change_percent`
- `tags` JSON
- `reason` JSON
- `created_at`

状态枚举：

- `CONFIRMED`
- `PENDING_CONFIRMATION`

`reason` JSON 保存命中时的完整解释，包括：

- 关键阴线日期、开高低收、实体上下沿。
- 企稳区间开始/结束日期。
- 确认阳线日期和阈值命中情况。
- 价格行为、均线、量能分项解释。
- 规则版本和关键阈值引用。

快照价值在于复现当时为什么入选，因此历史条目的解释不重新计算。

## API

路径统一使用 `/screeners`。

`POST /screeners/snapshots`

- 生成走势 A 快照。
- 第一版只支持 `strategyType = pattern_a`。
- 请求只接受 `tradeDate`、`provider`、`strategyType`。
- 规则参数固定在后端常量。
- 同一交易日、同一策略版本、同一 provider 重新生成时覆盖旧条目，保留同一个 snapshot id。

`GET /screeners/snapshots/default/latest?strategyType=pattern_a`

- 查询默认最近完整交易日的走势 A 快照。
- 不存在时返回未找到错误，由前端显示“暂无快照，可点击生成”。

`GET /screeners/snapshots/{tradeDate}?strategyType=pattern_a`

- 查询指定日期走势 A 快照。
- 不自动生成。
- 不自动回退到最近有快照的日期。

`GET /screeners/snapshots/{snapshotId}/items/{itemId}`

- 返回条目详情。
- 包含保存的 `reason`、近 30 个交易日 OHLCV、`amount`、`changePercent`、MA5/MA10/MA20、marker 信息。

`GET /screeners/stocks/{code}/daily-bars?endDate=&lookback=30`

- 通用日 K 接口。
- 只要 warehouse 有数据就允许查询任意股票。
- 默认 lookback 为 30，上限为 120。
- 返回 OHLCV、`amount`、`changePercent`、MA5/MA10/MA20。

错误码：

- 使用 `SCREENER_*` 命名。
- 示例：`SCREENER_NO_PRICE_DATA`、`SCREENER_DATA_COVERAGE_TOO_LOW`、`SCREENER_SNAPSHOT_NOT_FOUND`、`SCREENER_UNSUPPORTED_STRATEGY`。

生成执行方式：

- MVP 保持同步生成，`POST /screeners/snapshots` 在同一个请求内完成扫描并返回快照。
- 为避免 SQLite 长时间写锁，服务必须先用 warehouse 数据在内存中完成扫描和规则判定，再开启短事务写入 `ScreenerSnapshot` / `ScreenerItem`。
- 写事务只包含同日同版本快照 upsert、旧条目删除、新条目插入和统计更新。
- 前端 loading 明确提示全市场扫描可能耗时几十秒；如果实测耗时稳定超过 60-90 秒，或同步请求影响本地服务响应，再升级为“提交任务 -> 后台执行 -> 前端轮询”的异步架构。

响应字段：

- 返回 `strategyType: "pattern_a"` 和 `strategyName: "走势 A"`。
- 每个 item 返回 `inWatchlist`。
- item 保存并返回 `name` 和 `industry`。

## 观察池集成

走势 A 列表的“加入观察池”复用现有 `/watchlist/items` 接口：

- `source = pattern_a`
- `note` 可写入简短来源，如走势 A、策略版本、快照日期。

若股票已在观察池：

- 后端快照响应返回 `inWatchlist = true`。
- 前端显示“已观察”徽标，按钮禁用。
- 不修改已有观察池 note。

若股票不在 SQLite `stock` 表：

- 生成走势 A 快照时不写入 `stock` 表。
- 用户点击“加入观察池”时，后端按需从 warehouse instrument 和最新日 K 补齐最小 `Stock` 记录，再加入观察池。
- 最小记录包括 code、symbol、exchange、name、market、industry、最新价格、涨跌、成交量、成交额等可从最新日 K 得到的字段。

## 脚本

新增脚本：

```bash
python scripts/run_screener_snapshot.py --strategy pattern_a
```

支持参数：

- `--trade-date YYYY-MM-DD`
- `--provider AkShare`

第一版只支持 `pattern_a`，但脚本形态保留未来扩展空间。脚本不自动接入定时任务。

## 实现计划提示

开发切入点：先做后端数据库迁移、策略规则服务和单元测试，再做前端页面与 K 线展示。K 线视觉原型应建立在后端详情接口或固定 fixture 契约之上，不先于规则契约推进。

后续实现应按以下顺序拆分：

1. 抽出主板非 ST 股票池工具，并保证断板和数据健康行为不变。
2. 新增 screener 模型、SQLite 轻量迁移、schema、serializer、router。
3. 实现通用日 K 服务和 MA 计算。
4. 实现走势 A 规则服务、疑似除权/异常跳空过滤和快照生成。
5. 实现 watchlist 按需补齐 Stock。
6. 新增脚本入口。
7. 安装 `lightweight-charts`。
8. 新建 `/screeners` 页面和走势 A Tab。
9. 将现有断板页嵌入断板 Tab，并保留旧路由重定向。
10. 完成验证。

## 验证

后端单测为主：

- 主板非 ST 股票池过滤。
- 基础过滤：上市天数、K 线完整度、近 20 日均成交额。
- 覆盖率不足错误。
- 关键阴线识别。
- 疑似除权/异常跳空过滤。
- 左侧下跌方向判断。
- 已确认信号。
- 待确认信号。
- 待确认失效。
- `high == low` 不作为确认阳线。
- 小阳、十字、缩量阴识别。
- MA 标签和量能标签。
- 评分和排序。
- 快照覆盖同日同版本条目。
- item `inWatchlist` 合并。
- 详情接口返回 OHLCV、MA 和 marker。
- 通用 K 线接口默认 30、上限 120。
- 加入观察池时按需补齐 `Stock`。
- 脚本生成快照。

前端验证：

- `npm run lint`
- `npm run build`

不引入前端测试框架。

## 验收标准

- `/screeners` 可以默认打开走势 A。
- `/limit-up-breaks` 重定向到 `/screeners`。
- 走势 A 可以查询和手动生成快照。
- 无快照、空结果、数据覆盖不足、详情加载失败都有明确状态。
- 默认筛选已确认，列表按评分显示候选。
- 右侧显示选中股票近 30 日蜡烛图、MA 和核心标记。
- 已在观察池的股票显示“已观察”，未在观察池的股票可以加入观察池。
- 断板 Tab 行为与现有页面一致。
- 后端相关测试通过，前端 lint/build 通过。

## 风险与缓解

- 规则主观且可能过宽：保存 `strategyVersion` 和 `criteria`，通过分项评分与标签辅助校准。
- 同步生成可能耗时：前端显示明确 loading，后续再考虑异步任务。
- 原始日 K 可能受除权影响：第一版记录 `priceAdjustment=raw`，并加入疑似除权/异常跳空过滤；后续可升级到前复权版本。
- SQLite 写锁风险：扫描和规则判定不持有写事务，只有最终 upsert/insert 阶段短时间写库。
- `stock` 表和 warehouse 主数据可能不同步：加入观察池时按需补齐最小 `Stock`。
- `lightweight-charts` attribution 要求：实现时保留 TradingView 归属链接。
