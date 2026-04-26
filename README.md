# A 股研究与模拟交易系统

本仓库包含 React/Vite/TypeScript 前端与 FastAPI 后端。当前阶段为 **v0.1 Beta Data Layer**：在 v0.1 Alpha 的前后端真实 API 闭环和 Paper Trading 闭环基础上，新增统一 A 股基础数据层，让研究报告与策略信号可以基于单只股票日线数据运行。

## 后端边界

- 仅支持 `PAPER_TRADING_ONLY`。
- 不接真实券商，不实现真实自动交易。
- 不接真实 AI；AI 总结仍为 mock/template。
- v0.1 Beta 只接入基础数据层，不做全市场扫描，不做回测。
- 默认数据源为可复现 `MockProvider`；`AkShare` 适配器为可选单股票数据源，不作为测试默认依赖。
- AI 只生成研究报告，不直接下单。
- 前端不能直接创建成交或持仓。
- `POST /api/v1/paper-trading/runs` 是唯一交易执行入口。
- 交易执行内部固定顺序：`Signal Engine → Risk Engine → Order Manager → Paper Broker → Position Manager → Trade Logger`。
- `risk_check.status = BLOCKED` 时不会创建 `paper_order`。

## 项目结构

```text
backend/
  app/
    main.py                 # FastAPI app、CORS、统一错误处理、router 注册
    database.py             # SQLAlchemy engine/session/Base
    models.py               # 核心数据库表 ORM
    schemas.py              # Pydantic request/response schema
    serializers.py          # ORM -> API JSON 转换
    seed.py                 # SQLite seed/mock 数据初始化
    utils.py                # 响应包络、错误包络、ID/time helper
    providers/
      base.py               # MarketDataProvider 抽象
      mock_provider.py      # 默认可复现行情/财务 mock provider
      akshare_provider.py   # 可选 AkShare 单股票 provider
    routers/
      system.py             # system/status, data-sources/health
      research.py           # research tasks/reports/records
      monitoring.py         # watchlist, monitoring pool
      trading.py            # paper trading engine/runs
      portfolio.py          # account summary/positions
      audit.py              # orders/risk-checks/logs
      p0b.py                # Alpha P0-B dashboard/risk/trace/stats
    services/
      data_service.py       # 代码标准化、provider 调用、缓存表、data_fetch_log
      research.py           # 研究任务与模板化 mock AI 报告
      monitoring.py         # 观察池/监控池业务
      paper_trading.py      # MA 信号 + 风控 + 模拟交易闭环
scripts/
  smoke_v01_alpha.py        # v0.1 Alpha/Beta 最小闭环 smoke 测试
tests/
  test_paper_trading_run.py
  test_v01_alpha_boundaries.py
  test_beta_data_layer.py
requirements.txt
```

## 环境变量

复制 `.env.example` 后按需调整：

```bash
cp .env.example .env
```

关键变量：

- `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`
- `DATABASE_URL=sqlite:///./paper_trading.db`
- `MARKET_DATA_PROVIDER=mock`
- `AKSHARE_ENABLED=false`
- `DATA_CACHE_TTL_MINUTES=1440`

Provider 切换：

```bash
# 默认：稳定可复现 mock 数据
MARKET_DATA_PROVIDER=mock AKSHARE_ENABLED=false uvicorn backend.app.main:app --reload --port 8000

# 可选：单只股票 AkShare 真实数据层
# 仍然不接真实券商、不接真实 AI、不做全市场扫描、不做回测。
MARKET_DATA_PROVIDER=akshare AKSHARE_ENABLED=true uvicorn backend.app.main:app --reload --port 8000
```

也可以在单次请求中指定 provider：

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/data/stocks/600519/refresh?provider=akshare'
```

## 启动后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

启动时会自动执行：

```python
Base.metadata.create_all(bind=engine)
seed_database()
```

默认 SQLite 数据库文件：`paper_trading.db`。如果需要重置本地数据，可停止服务后删除该文件，再重新启动后端。

访问：

- Health check: <http://127.0.0.1:8000/health>
- OpenAPI: <http://127.0.0.1:8000/docs>

## 启动前端

```bash
npm install
npm run dev
```

前端默认 Vite 端口为 `3000`，后端 CORS 已允许：

- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:5173`
- `http://127.0.0.1:5173`

## Seed 初始化

后端启动会自动 seed：

- 股票基础信息：`600519`、`000858`、`300750`、`601318`
- 日线缓存：`price_bar`
- 财务快照：`financial_snapshot`
- 数据拉取日志：`data_fetch_log`
- 账户与 Paper Trading 引擎状态
- 数据源健康状态

手动初始化：

```bash
source .venv/bin/activate
python - <<'PY'
from backend.app.seed import init_db
init_db()
print("seed ready")
PY
```

## 数据库迁移（Alembic）

v0.1 Final 引入 Alembic baseline。SQLite 仍是默认开发/测试数据库。

```bash
source .venv/bin/activate

# 按当前 DATABASE_URL 执行迁移
alembic upgrade head

# 查看当前版本
alembic current

# 创建后续迁移（v0.2 起建议使用）
alembic revision --autogenerate -m "describe change"
```

说明：

- baseline migration 位于 `alembic/versions/20260426_0001_v01_final_baseline.py`。
- 本地 demo 启动仍会执行 `init_db()` 与 seed，保持无迁移经验用户也能直接运行。
- 生产化部署建议先执行 `alembic upgrade head`，再启动服务。

## Smoke 测试

先启动后端，再运行：

```bash
source .venv/bin/activate
python scripts/smoke_v01_alpha.py 300750
```

该脚本会验证：

1. 系统状态和数据源健康。
2. 创建研究任务并查询报告。
3. 加入观察池和交易监控池。
4. 手动运行一次模拟交易检查。
5. 查询订单、持仓、风控、日志。

AkShare 手动 smoke（不默认运行）：

```bash
# 先安装 requirements.txt，并以 AkShare enabled 模式启动后端
MARKET_DATA_PROVIDER=akshare AKSHARE_ENABLED=true uvicorn backend.app.main:app --reload --port 8000

# 另开终端
source .venv/bin/activate
python scripts/smoke_akshare_provider.py 600519
```

RC 真实数据诊断 smoke（不默认运行，默认检查 600519 / 000858 / 300750 / 601318）：

```bash
# mock 模式可离线验证输出格式
python scripts/smoke_real_data_rc.py mock

# AkShare 模式需要 AKSHARE_ENABLED=true 且外部接口可用
AKSHARE_ENABLED=true MARKET_DATA_PROVIDER=akshare python scripts/smoke_real_data_rc.py akshare
```

该脚本会调用：

- `POST /api/v1/data/stocks/{code}/refresh?provider=akshare`
- `GET /api/v1/data/stocks/{code}/status?provider=akshare`
- `POST /api/v1/research/tasks` with `options.provider=akshare`
- `GET /api/v1/data/fetch-logs`

AkShare 限制：

- 仅支持单只股票查询。
- 依赖外部 AkShare 包与其上游数据接口可用性。
- 字段缺失时允许降级，报告用 `dataCompleteness` 表示完整度。
- 刷新失败时保留旧缓存，并在报告中显示可能使用过期缓存。

## 最小闭环手动验证

```bash
# 1. 创建研究任务并生成模板化研究报告
curl -s -X POST http://127.0.0.1:8000/api/v1/research/tasks \
  -H 'Content-Type: application/json' \
  -d '{"code":"300750"}'

# 2. 查询报告
curl -s http://127.0.0.1:8000/api/v1/research/reports/by-code/300750

# 3. 加入观察池
curl -s -X POST http://127.0.0.1:8000/api/v1/watchlist/items \
  -H 'Content-Type: application/json' \
  -d '{"code":"300750","source":"README"}'

# 4. 加入交易监控池
curl -s -X POST http://127.0.0.1:8000/api/v1/monitoring-pool/items \
  -H 'Content-Type: application/json' \
  -d '{"code":"300750","enabled":true}'

# 5. 手动运行一次模拟交易检查
curl -s -X POST http://127.0.0.1:8000/api/v1/paper-trading/runs \
  -H 'Content-Type: application/json' \
  -d '{"trigger":"MANUAL","scope":{"enabledOnly":true}}'

# 6. 查询审计数据
curl -s http://127.0.0.1:8000/api/v1/orders
curl -s http://127.0.0.1:8000/api/v1/portfolio/positions
curl -s http://127.0.0.1:8000/api/v1/risk-checks
curl -s http://127.0.0.1:8000/api/v1/logs
```

## 测试与构建

```bash
npm run lint
npx tsc --noEmit
npm run build
.venv/bin/python -m pytest -q
```

当前测试覆盖：

1. 输入股票代码创建研究任务。
2. 生成并查询研究报告。
3. 加入观察池。
4. 加入交易监控池。
5. 运行一次模拟交易检查。
6. 校验后端创建订单、成交、持仓、风控审计与系统日志。
7. 非法股票代码、重复加入、报告不存在等错误边界。
8. 股票代码标准化、数据源失败日志、无日线数据降级/失败、MA 策略 BUY/SELL/HOLD。
