# A 股研究与模拟交易系统

本仓库是本地运行的 A 股研究、复盘与模拟交易工具：

- 前端：React / Vite / TypeScript
- 后端：FastAPI / SQLAlchemy / SQLite
- 行情数据：AkShare provider + 本地 Parquet warehouse
- 交易边界：仅 `PAPER_TRADING_ONLY`，不接真实券商，不做真实下单

## 运行边界

- 不接真实 AI；研究报告只整理当前可取得的数据。
- 不提供投资建议。
- 不配置真实券商账号或真实交易凭据。
- 当前 provider 只支持 `akshare` / `ak`；其他值返回 `UNKNOWN_DATA_PROVIDER`。
- `POST /api/v1/paper-trading/runs` 是模拟交易执行入口。

## 目录结构

```text
backend/app/
  main.py                 # FastAPI app、CORS、异常处理、router 注册、上传目录挂载
  database.py             # SQLAlchemy engine/session；测试运行时保护 paper_trading_test.db
  models.py               # SQLite 业务模型
  routers/                # /api/v1 路由
  services/               # 研究、复盘、模拟交易、断板监控等业务逻辑
  providers/              # 单股票 AkShare provider，用于研究/刷新路径
  data_layer/             # 全市场同步、Parquet warehouse、质量校验
scripts/
  start-dev.sh
  init_history_data.py
  sync_daily_data.py
  reconcile_daily_data.py
  run_limit_up_break_snapshot.py
src/
  pages/
  components/
  services/api/
tests/
  akshare_fixture.py      # AkShare-shaped 本地 fixture；默认测试不访问外网
```

## 环境变量

复制 `.env.example`：

```bash
cp .env.example .env
```

常用变量：

- `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`
- `DATABASE_URL=sqlite:///./paper_trading.db`
- `MARKET_DATA_PROVIDER=akshare`
- `AKSHARE_ENABLED=true`
- `DATA_CACHE_TTL_MINUTES=1440`
- `DATA_ROOT=data`
- `AKSHARE_BYPASS_PROXY=true`
- `ALLOW_MANUAL_RUN_OUTSIDE_TRADING_TIME=true`
- `STRICT_TRADING_TIME_CHECK=false`

## 启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

npm install
npm run start:dev
```

`npm run start:dev` 会启动：

- 后端：<http://127.0.0.1:8000>
- 前端：<http://127.0.0.1:3000>

常用入口：

- Health check: <http://127.0.0.1:8000/health>
- OpenAPI: <http://127.0.0.1:8000/docs>

## 当前功能入口

- 首页概览：`/`
- 股票研究：`/research`
- 研究报告详情：`/research/:code`
- 连板断板：`/limit-up-breaks`
- 热门股票：`/hot-stocks`
- 交易复盘：`/reviews`
- 数据健康：`/data-health`
- 交易控制台：`/trading`
- 持仓与日志：`/history`

## 数据与任务

单股票刷新：

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/data/stocks/600519/refresh?provider=akshare'
```

研究任务：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/research/tasks \
  -H 'Content-Type: application/json' \
  -d '{"code":"600519"}'
```

全市场 warehouse 初始化和增量同步：

```bash
python scripts/init_history_data.py --provider akshare --start-date 2020-01-01
python scripts/sync_daily_data.py --provider akshare --lookback-days 20
```

更多数据层说明见 [docs/data-layer.md](docs/data-layer.md)。

## 验证

```bash
source .venv/bin/activate
pytest -q
npm run lint
npm run build
```

真实 AkShare smoke 依赖本机网络和上游接口：

```bash
python scripts/smoke_akshare_provider.py 600519
python scripts/smoke_real_data_rc.py akshare
```

## 专题文档

- [数据层](docs/data-layer.md)
- [连板断板监控](docs/limit-up-breaks.md)
- [交易复盘](docs/reviews.md)

API 细节以运行中的 FastAPI OpenAPI 页面为准：<http://127.0.0.1:8000/docs>。
