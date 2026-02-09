import type { Message } from '@ag-ui/core';
import { ContentPart, ToolInvocation } from '@/types/message.ts';

export interface ChatListItem {
  id: string;
  userId: string;
  name?: string;
  createdAt: Date;
  updatedAt: Date | null;
  metadata?: Record<string, unknown>;
  initialised?: boolean;
}

type JSONValue =
  | null
  | string
  | number
  | boolean
  | {
      [value: string]: JSONValue;
    }
  | Array<JSONValue>;

export type MessageResponse = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  createdAt: Date;
  threadId?: string;
  resourceId?: string;
  type?: string;
  content: MessageContent;
};

export type MessageContent = {
  format: number;
  parts: ContentPart[];
  content?: string;
  toolInvocations?: ToolInvocation[];
  reasoning?: string;
  annotations?: JSONValue[] | undefined;
  metadata?: Record<string, unknown>;
};

export type APIChat = {
  name: string;
  thread_id: string;
  user_id: string;
  created_at: string;
  update_time: string;
  metadata?: Record<string, unknown>;
};

export type MessageHistoryResponse = {
  inProgress: boolean;
  error?: string;
  timestamp?: number;
} & Message;

export type APIChatWithMessages = APIChat & {
  messages: MessageHistoryResponse[];
};
