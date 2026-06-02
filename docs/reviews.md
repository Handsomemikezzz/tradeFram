# 交易复盘

交易复盘模块位于前端 `/reviews`，后端 API 位于 `/api/v1/reviews/*`。

## 代码入口

- Router: `backend/app/routers/reviews.py`
- Service: `backend/app/services/reviews.py`
- Models: `backend/app/models.py`
- Schemas: `backend/app/schemas.py`
- Serializers: `backend/app/serializers_reviews.py`
- 前端页面：`src/pages/Reviews.tsx`
- 前端组件：`src/components/reviews/*`
- API clients:
  - `src/services/api/reviewApi.ts`
  - `src/services/api/reviewCardApi.ts`

## 当前数据模型

主要对象：

- `StockReviewCard`：一只股票的一段观察或交易复盘周期。
- `StockReviewEvent`：卡片内的过程记录。
- `ReviewEntry`：旧的单次行为/观察记录，当前仍保留 API 和测试。
- `WeeklyReview`：周复盘工作台保存内容。
- `IronLaw`：交易铁律规则。

第一屏主工作流以 `StockReviewCard` 为中心；旧 `ReviewEntry` 没有删除。

## Card API

- `POST /reviews/cards`
- `GET /reviews/cards`
- `GET /reviews/cards/summary`
- `GET /reviews/cards/{card_id}`
- `PATCH /reviews/cards/{card_id}`
- `DELETE /reviews/cards/{card_id}`
- `POST /reviews/cards/{card_id}/events`
- `PATCH /reviews/cards/{card_id}/events/{event_id}`
- `DELETE /reviews/cards/{card_id}/events/{event_id}`
- `POST /reviews/cards/{card_id}/close`
- `POST /reviews/cards/{card_id}/reopen`

列表筛选支持：

- `status`
- `keyword`
- `startDate`
- `endDate`
- `planStatus`
- `followedPlan`
- `problemTags`
- `page`
- `pageSize`

## Entry / Weekly / Iron Law API

- `POST /reviews/entries`
- `GET /reviews/entries`
- `GET /reviews/entries/{entry_id}`
- `PATCH /reviews/entries/{entry_id}`
- `DELETE /reviews/entries/{entry_id}`
- `GET /reviews/stats`
- `GET /reviews/weeks/{week_start}`
- `PUT /reviews/weeks/{week_start}`
- `GET /reviews/iron-laws`
- `POST /reviews/iron-laws`
- `PATCH /reviews/iron-laws/{law_id}`
- `DELETE /reviews/iron-laws/{law_id}`

`week_start` 必须是周一。

## 测试依据

- `tests/test_reviews.py`
