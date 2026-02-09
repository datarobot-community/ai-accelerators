import { isAxiosError } from 'axios';

/**
 * Extract a user-friendly error message from Axios / API errors.
 */
export function getApiErrorMessage(error: unknown, fallbackMessage = 'Request failed'): string {
  if (!error) {
    return fallbackMessage;
  }

  if (isAxiosError(error)) {
    const responseData = error.response?.data as
      | { detail?: unknown; message?: string }
      | string
      | undefined;

    if (typeof responseData === 'string' && responseData.trim().length > 0) {
      return responseData;
    }

    if (responseData && typeof responseData === 'object') {
      const message = typeof responseData.message === 'string' ? responseData.message : undefined;
      if (message) {
        return message;
      }

      const detail = (responseData as { detail?: unknown }).detail;
      if (typeof detail === 'string' && detail.trim().length > 0) {
        return detail;
      }
      if (detail && typeof detail === 'object') {
        const detailMessage = (detail as { message?: string }).message;
        if (detailMessage) {
          return detailMessage;
        }
      }
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  if (typeof error === 'string' && error.trim().length > 0) {
    return error;
  }

  return fallbackMessage;
}
