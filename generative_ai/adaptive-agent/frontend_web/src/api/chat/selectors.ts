import {
  APIChat,
  APIChatWithMessages,
  ChatListItem,
  MessageHistoryResponse,
  MessageResponse,
} from './types';
import { ContentPart, isToolInvocationPart, ToolInvocationUIPart } from '@/types/message.ts';

export function selectChats(res: { data: APIChat[] }): ChatListItem[] {
  return [...res.data]
    .map(chat => ({
      id: chat.thread_id,
      name: chat.name,
      userId: chat.user_id,
      createdAt: new Date(chat.created_at),
      updatedAt: chat.update_time ? new Date(chat.update_time) : null,
      metadata: chat.metadata,
      initialised: true,
    }))
    .sort((fChat, sChat) => (sChat.createdAt < fChat.createdAt ? -1 : 1));
}

export function selectMessages(res: { data: APIChatWithMessages }): MessageResponse[] {
  const uiMessages: MessageResponse[] = [];

  for (const historyMessage of res.data.messages) {
    if (addResultToToolInvocation(historyMessage, uiMessages)) {
      continue;
    }

    const parts = mapMessageToContentPart(historyMessage);
    const uiMessage: MessageResponse = {
      id: historyMessage.id,
      role:
        historyMessage.role == 'developer' || historyMessage.role == 'tool'
          ? 'system'
          : historyMessage.role,
      createdAt: historyMessage?.timestamp ? new Date(historyMessage.timestamp) : new Date(),
      content: {
        format: 2,
        parts,
        content: historyMessage.content,
      },
    };
    uiMessages.push(uiMessage);
  }

  return uiMessages;
}
// helper methods

function getToolPart(m: MessageResponse, toolCallId: string): ToolInvocationUIPart | undefined {
  return m.content.parts.find(p => {
    if (isToolInvocationPart(p)) {
      return p.toolInvocation?.toolCallId === toolCallId;
    }
  }) as ToolInvocationUIPart | undefined;
}

function tryParseArgs(args: string) {
  try {
    return JSON.parse(args);
  } catch (e) {
    return args;
  }
}

function mapMessageToContentPart(m: MessageHistoryResponse): ContentPart[] {
  if ('toolCalls' in m && !!m.toolCalls && m.toolCalls.length) {
    return m.toolCalls.map(
      t =>
        ({
          type: 'tool-invocation',
          toolInvocation: {
            state: 'call',
            toolCallId: t.id,
            toolName: t.function?.name,
            args: tryParseArgs(t.function?.arguments),
          },
        }) as ToolInvocationUIPart
    );
  }

  return [{ type: 'text', text: m.content || '' }];
}

/**
 * Populate tool invocations with result, do not render these history entries as a separate message
 * Mutation here is fine, uiMessages are created in selectMessages
 * @param historyMessage
 * @param uiMessages
 */
function addResultToToolInvocation(
  historyMessage: MessageHistoryResponse,
  uiMessages: MessageResponse[]
): boolean {
  if (
    historyMessage.role === 'tool' &&
    !historyMessage.toolCalls &&
    historyMessage.content &&
    historyMessage.id?.startsWith?.('call_')
  ) {
    return uiMessages.some((m: MessageResponse) => {
      const toolPart = getToolPart(m, historyMessage.id);
      if (toolPart) {
        toolPart.toolInvocation.result = historyMessage.content;
        toolPart.toolInvocation.state = 'result';
        return true;
      }
    });
  }
  return false;
}
