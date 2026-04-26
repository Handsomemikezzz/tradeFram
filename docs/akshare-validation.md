# AkShare 真实环境验收

v0.1 Final 默认仍使用 `MockProvider`。AkShare 是可选真实 A 股基础数据源，只用于单只股票数据获取，不接真实券商、不接真实 AI、不做全市场扫描、不做回测。

## 运行方式

```bash
source .venv/bin/activate
pip install -r requirements.txt

MARKET_DATA_PROVIDER=akshare \
AKSHARE_ENABLED=true \
python scripts/smoke_real_data_rc.py akshare
```

## 固定验证股票

- `600519` 贵州茅台
- `000858` 五粮液
- `300750` 宁德时代
- `601318` 中国平安

## 输出字段

脚本会输出 JSON 数组，每只股票包含：

- 股票名称：`name`
- 日线数量：`priceBarCount`
- 最新交易日：`latestTradeDate`
- `MA5`
- `MA20`
- 信号结果：`signal`
- `dataCompleteness`
- fetch log 状态：`fetchLogStatus`
- 失败原因：`error` / `fetchLog.errorMessage`

## 验收记录模板

| code | name | priceBarCount | latestTradeDate | MA5 | MA20 | signal | dataCompleteness | fetchLogStatus | failure reason |
| --- | --- | ---: | --- | ---: | ---: | --- | ---: | --- | --- |
| 600519 |  |  |  |  |  |  |  |  |  |
| 000858 |  |  |  |  |  |  |  |  |  |
| 300750 |  |  |  |  |  |  |  |  |  |
| 601318 |  |  |  |  |  |  |  |  |  |

## 常见失败原因

- `AKSHARE_DISABLED`：未设置 `AKSHARE_ENABLED=true`。
- `akshare is not installed`：未安装 `requirements.txt` 中的依赖。
- 上游网络/API 失败：AkShare 或其上游接口不可用。
- `NO_DAILY_DATA`：上游未返回指定股票的日线数据。

## 通过标准

- 至少能成功返回固定股票的基础信息与日线数据。
- `priceBarCount >= 60` 时 MA5/MA20 策略输出可信。
- 失败场景必须写入 `data_fetch_log`，不能导致服务崩溃。
- 刷新失败时旧缓存不能被覆盖。
