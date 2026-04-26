# A 股研究与模拟交易系统

React/Vite/TypeScript 前端 + FastAPI/SQLAlchemy/SQLite 后端。当前版本采用 **AkShare-only** 数据层：股票基础信息、日线行情、财务摘要和交易日历只通过 AkShare 按单只股票拉取并写入本地缓存。

## 后端边界

- 仅支持 `PAPER_TRADING_ONLY`，不接真实券商，不做真实下单。
- 不接真实 AI；研究报告只整理 AkShare 返回的公开数据，不构成投资建议。
- 不做全市场扫描、不做回测、不抓取新闻公告。
- AkShare 是唯一行情数据提供器。
- `POST /api/v1/paper-trading/runs` 是唯一交易执行入口。
- 交易执行内部固定顺序：`Signal Engine -> Risk Engine -> Order Manager -> Paper Broker -> Position Manager -> Trade Logger`。

## 项目结构

```text
backend/app/
  main.py                 # FastAPI app、CORS、统一错误处理、router 注册
  seed.py                 # 仅初始化账户、引擎、健康项等系统状态
  providers/
    base.py               # MarketDataProvider 抽象
    akshare_provider.py   # AkShare 单股票 provider
  services/
    data_service.py       # AkShare 调用、缓存表、data_fetch_log
    research.py           # 基于真实可得数据生成研究报告
    paper_trading.py      # MA 信号 + 风控 + 模拟交易闭环
tests/
  akshare_fixture.py      # AkShare-shaped 本地测试 fixture，不访问外网
```

## 环境变量

复制 `.env.example` 后按需调整：

```bash
cp .env.example .env
```

关键变量：

- `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`
- `DATABASE_URL=sqlite:///./paper_trading.db`
- `MARKET_DATA_PROVIDER=akshare`
- `AKSHARE_ENABLED=true`
- `DATA_CACHE_TTL_MINUTES=1440`

Provider 参数：

- 空值：使用 AkShare。
- `akshare` / `AkShare`：使用 AkShare。
- 其他值：返回 `UNKNOWN_DATA_PROVIDER`。

## 启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000

npm install
npm run dev
```

后端启动会建表并 seed 系统状态，但不会写入任何股票、K 线或财务快照。股票数据会在研究或刷新具体代码时由 AkShare 按需写入。

访问：

- Health check: <http://127.0.0.1:8000/health>
- OpenAPI: <http://127.0.0.1:8000/docs>

## 数据刷新与研究

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/data/stocks/600519/refresh?provider=akshare'

curl -s -X POST http://127.0.0.1:8000/api/v1/research/tasks \
  -H 'Content-Type: application/json' \
  -d '{"code":"600519"}'
```

AkShare 或其上游不可用时，接口会返回真实错误并写入 `data_fetch_log`。如果已有本地缓存，刷新失败会保留旧缓存并标记 `dataStale=true`。

## Smoke 测试

默认测试不访问外网，使用 `tests/akshare_fixture.py` 模拟 AkShare 返回结构。

真实 AkShare smoke 需要后端运行且外部接口可用：

```bash
source .venv/bin/activate
python scripts/smoke_akshare_provider.py 600519
python scripts/smoke_real_data_rc.py akshare
```

## 测试与构建

```bash
source .venv/bin/activate
pytest -q
npm run lint
npm run build
```

## 已知限制

- SQLite 仅适合本地演示。
- AkShare 真实可用性取决于本机网络、代理和其上游接口。
- 未返回财务、新闻、主营构成或 AI 置信度时，API 会显式返回 `null` 或空数组。
- 费用和成交模型为模拟规则，不等同真实券商。
