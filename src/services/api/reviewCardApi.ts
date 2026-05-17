import { apiClient, QueryParams } from './client';
import {
  PageResponse,
  StockReviewCardCloseRequest,
  StockReviewCardRequest,
  StockReviewCardResponse,
  StockReviewCardSummaryResponse,
  StockReviewEventRequest,
  StockReviewEventResponse,
} from './types';

export const reviewCardApi = {
  createCard: (body: StockReviewCardRequest) => apiClient.post<StockReviewCardResponse>('/reviews/cards', body),
  getCards: (query?: QueryParams) => apiClient.get<PageResponse<StockReviewCardResponse>>('/reviews/cards', query),
  getSummary: (query: { startDate: string; endDate: string }) => apiClient.get<StockReviewCardSummaryResponse>('/reviews/cards/summary', query),
  getCard: (id: string) => apiClient.get<StockReviewCardResponse>(`/reviews/cards/${id}`),
  updateCard: (id: string, body: Partial<StockReviewCardRequest>) => apiClient.patch<StockReviewCardResponse>(`/reviews/cards/${id}`, body),
  deleteCard: (id: string) => apiClient.delete<{ deleted: boolean }>(`/reviews/cards/${id}`),
  addEvent: (id: string, body: StockReviewEventRequest) => apiClient.post<StockReviewEventResponse>(`/reviews/cards/${id}/events`, body),
  updateEvent: (cardId: string, eventId: string, body: Partial<StockReviewEventRequest>) => apiClient.patch<StockReviewEventResponse>(`/reviews/cards/${cardId}/events/${eventId}`, body),
  deleteEvent: (cardId: string, eventId: string) => apiClient.delete<{ deleted: boolean }>(`/reviews/cards/${cardId}/events/${eventId}`),
  closeCard: (id: string, body: StockReviewCardCloseRequest) => apiClient.post<StockReviewCardResponse>(`/reviews/cards/${id}/close`, body),
  reopenCard: (id: string) => apiClient.post<StockReviewCardResponse>(`/reviews/cards/${id}/reopen`, {}),
};
