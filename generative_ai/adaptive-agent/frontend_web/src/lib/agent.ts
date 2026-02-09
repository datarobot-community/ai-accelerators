import { HttpAgent } from '@ag-ui/client';
import type { Message } from '@ag-ui/core';
import { AG_UI_ENDPOINT } from '@/constants/endpoints.ts';

export function createAgent({
  url = AG_UI_ENDPOINT,
  threadId,
  initialMessages = [],
  initialState = {},
}: {
  url?: string;
  threadId: string;
  initialMessages?: Message[];
  initialState?: any;
}) {
  return new HttpAgent({
    url,
    threadId,
    agentId: threadId,
    initialMessages,
    initialState,
  });
}
