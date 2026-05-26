export interface ApiEnvelope<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  requestId: string;
  serverTime: string;
}

export class ApiClientError extends Error {
  code: string;
  status: number;
  details?: unknown;
  requestId?: string;
  serverTime?: string;

  constructor(message: string, options: { code: string; status: number; details?: unknown; requestId?: string; serverTime?: string }) {
    super(message);
    this.name = 'ApiClientError';
    this.code = options.code;
    this.status = options.status;
    this.details = options.details;
    this.requestId = options.requestId;
    this.serverTime = options.serverTime;
  }
}

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || DEFAULT_BASE_URL;

type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | QueryValue[]>;

function buildUrl(path: string, query?: QueryParams): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);

  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item !== undefined && item !== null && item !== '') url.searchParams.append(key, String(item));
        });
        return;
      }
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value));
    });
  }

  return url.toString();
}

async function request<T>(method: string, path: string, options: { query?: QueryParams; body?: unknown } = {}): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(buildUrl(path, options.query), {
    method,
    headers: options.body === undefined
      ? undefined
      : isFormData
        ? undefined
        : { 'Content-Type': 'application/json' },
    body: options.body === undefined
      ? undefined
      : isFormData
        ? (options.body as FormData)
        : JSON.stringify(options.body),
  });

  let envelope: ApiEnvelope<T> | undefined;
  try {
    envelope = (await response.json()) as ApiEnvelope<T>;
  } catch {
    throw new ApiClientError(`HTTP ${response.status}: 后端响应不是有效 JSON`, {
      code: 'INVALID_JSON_RESPONSE',
      status: response.status,
    });
  }

  if (!response.ok || !envelope.success) {
    throw new ApiClientError(envelope.error?.message || `HTTP ${response.status}`, {
      code: envelope.error?.code || 'API_ERROR',
      status: response.status,
      details: envelope.error?.details,
      requestId: envelope.requestId,
      serverTime: envelope.serverTime,
    });
  }

  return envelope.data as T;
}

export const apiClient = {
  get: <T>(path: string, query?: QueryParams) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown, query?: QueryParams) => request<T>('POST', path, { body, query }),
  put: <T>(path: string, body?: unknown, query?: QueryParams) => request<T>('PUT', path, { body, query }),
  patch: <T>(path: string, body?: unknown, query?: QueryParams) => request<T>('PATCH', path, { body, query }),
  delete: <T>(path: string, query?: QueryParams) => request<T>('DELETE', path, { query }),
};
