import { v4 as uuid } from 'uuid';
import type {
  TextMessageChunkEvent,
  TextMessageContentEvent,
  TextMessageEndEvent,
  TextMessageStartEvent,
  ToolCallEndEvent,
} from '@ag-ui/core';
import { EventType } from '@ag-ui/core';
import type { ChatStateEventByType } from '@/types/events';
import { MessageResponse } from '@/api/chat/types.ts';

type AgUiTextEvent =
  | TextMessageStartEvent
  | TextMessageContentEvent
  | TextMessageEndEvent
  | TextMessageChunkEvent;

type AgUiToolEvent = ToolCallEndEvent;

export function createTextMessageFromAgUiEvent(
  event: AgUiTextEvent,
  textMessageBuffer?: string
): MessageResponse {
  const baseMessage: MessageResponse = {
    id: event.messageId || '',
    content: {
      format: 2,
      parts: [],
      content: '',
    },
    role: 'assistant',
    createdAt: event.timestamp ? new Date(event.timestamp) : new Date(),
    threadId: '',
    resourceId: '',
  };

  // Map role, converting 'developer' to 'system' for compatibility
  const mapRole = (
    role?: 'user' | 'assistant' | 'system' | 'developer'
  ): 'user' | 'assistant' | 'system' => {
    if (!role || role === 'developer') return 'system';
    return role;
  };

  switch (event.type) {
    case EventType.TEXT_MESSAGE_START:
      return {
        ...baseMessage,
        role: mapRole(event.role),
        id: event.messageId,
      };

    case EventType.TEXT_MESSAGE_CONTENT:
      return {
        ...baseMessage,
        id: event.messageId,
        content: {
          format: 2,
          parts: [
            {
              type: 'text',
              text: textMessageBuffer + event.delta,
            },
          ],
          content: textMessageBuffer + event.delta,
        },
      };

    case EventType.TEXT_MESSAGE_END:
      return {
        ...baseMessage,
        id: event.messageId,
      };

    case EventType.TEXT_MESSAGE_CHUNK:
      return {
        ...baseMessage,
        id: event.messageId || '',
        role: mapRole(event.role),
        content: {
          format: 2,
          parts: event.delta
            ? [
                {
                  type: 'text',
                  text: event.delta,
                },
              ]
            : [],
          content: event.delta || '',
        },
      };

    default:
      return baseMessage;
  }
}

export function createToolMessageFromAgUiEvent(
  event: AgUiToolEvent,
  toolCallName: string,
  toolCallArgs: Record<string, any>
): MessageResponse {
  const baseMessage: MessageResponse = {
    id: uuid(),
    content: {
      format: 2,
      parts: [
        {
          type: 'tool-invocation',
          toolInvocation: {
            state: 'call',
            args: toolCallArgs || event.rawEvent?.args || {},
            toolCallId: event.toolCallId,
            toolName: toolCallName,
          } as any,
        },
      ],
    },
    role: 'assistant',
    createdAt: event.timestamp ? new Date(event.timestamp) : new Date(),
    threadId: '',
    resourceId: uuid(),
  };

  return baseMessage;
}

export function createTextMessageFromUserInput({
  message,
  chatId,
  messageId,
}: {
  message: string;
  chatId: string;
  messageId: string;
}): MessageResponse {
  const baseMessage: MessageResponse = {
    id: messageId,
    content: {
      format: 2,
      parts: [
        {
          type: 'text',
          text: message,
        },
      ],
      content: message,
    },
    role: 'user',
    createdAt: new Date(),
    threadId: chatId,
    resourceId: uuid(),
  };

  return baseMessage;
}

export function createCustomMessageWidget({
  toolCallName,
  toolCallArgs,
  threadId,
}: {
  toolCallName: string;
  toolCallArgs: Record<string, any>;
  threadId: string;
}): MessageResponse {
  const toolInvocation = {
    state: 'call',
    toolCallId: `call_${uuid()}`,
    toolName: toolCallName,
    args: toolCallArgs,
  };
  return {
    id: uuid(),
    content: {
      format: 2,
      parts: [
        {
          type: 'tool-invocation',
          toolInvocation,
        },
      ],
    },
    role: 'assistant',
    createdAt: new Date(),
    threadId: threadId,
    resourceId: uuid(),
  };
}

export function messageToStateEvent(message: MessageResponse): ChatStateEventByType<'message'> {
  return {
    type: 'message',
    value: message,
  };
}
