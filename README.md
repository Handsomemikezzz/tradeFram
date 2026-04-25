# A 股研究与模拟交易系统

本仓库包含 React 前端与第一阶段 FastAPI 后端。后端只实现 API Contract v0.1 的 P0-A 最小闭环：研究任务、mock 研究报告、观察池、交易监控池、模拟交易巡检、订单/持仓/风控/日志查询。

## 后端边界

- 仅支持 `PAPER_TRADING_ONLY`。
- 不接真实券商，不实现真实自动交易。
- 不接 Tushare、AkShare 或真实 AI；第一阶段使用 seed mock 数据。
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
    seed.py                 # SQLite seed mock 数据
    utils.py                # 响应包络、错误包络、ID/time helper
    routers/
      system.py             # system/status, data-sources/health
      research.py           # research tasks/reports/records
      monitoring.py         # watchlist, monitoring pool
      trading.py            # paper trading engine/runs
      portfolio.py          # account summary/positions
      audit.py              # orders/risk-checks/logs
    services/
      research.py           # mock 研究任务与报告生成
      monitoring.py         # 观察池/监控池业务
      paper_trading.py      # Signal→Risk→Order→Execution→Position→Log 闭环
tests/
  test_paper_trading_run.py # 最小闭环测试
requirements.txt            # Python 后端依赖
```

## 启动后端

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

启动后访问：

- Health check: <http://127.0.0.1:8000/health>
- OpenAPI: <http://127.0.0.1:8000/docs>

默认 SQLite 数据库文件：`paper_trading.db`。如需自定义：

```bash
DATABASE_URL=sqlite:///./local.db uvicorn backend.app.main:app --reload --port 8000
```

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

## 最小闭环手动验证

```bash
# 1. 创建研究任务并生成 mock 报告
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

## 测试

```bash
source .venv/bin/activate
pytest tests/test_paper_trading_run.py -q
```

当前测试覆盖：

1. 输入股票代码创建研究任务。
2. 生成并查询 mock 研究报告。
3. 加入观察池。
4. 加入交易监控池。
5. 运行一次模拟交易检查。
6. 校验后端创建订单、成交、持仓、风控审计与系统日志。
