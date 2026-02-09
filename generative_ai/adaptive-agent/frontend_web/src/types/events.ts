import { type CustomEvent } from '@ag-ui/core';
import { type ProgressStep } from './progress';
import { MessageResponse } from '@/api/chat/types.ts';

export type ChatStateEvent =
  | {
      type: 'step';
      value: ChatStepEvent;
    }
  | {
      type: 'message';
      value: ChatMessageEvent;
    }
  | {
      type: 'error';
      value: ChatErrorEvent;
    }
  | {
      type: 'thinking';
      value: ChatThinkingEvent;
    };

export type ChatStateEventByType<T extends ChatStateEvent['type']> = Extract<
  ChatStateEvent,
  { type: T }
>;

export type ChatStepEvent = {
  id: string;
  threadId: string;
  createdAt: Date;
  name: string;
  isRunning: boolean;
};

export type ChatErrorEvent = {
  id: string;
  threadId: string;
  createdAt: Date;
  error: string;
};

export type ChatThinkingEvent = {
  id: string;
  threadId: string;
  createdAt: Date;
};

export type ChatMessageEvent = MessageResponse;

export interface ProgressStartCustomEvent extends CustomEvent {
  name: 'progress-start';
  value: {
    id: string;
    steps: ProgressStep[];
  };
}

export interface ProgressDoneCustomEvent extends CustomEvent {
  name: 'progress-done';
  value: { id: string; step: number };
}

export interface ProgressErrorCustomEvent extends CustomEvent {
  name: 'progress-error';
  value: { id: string; step: number; message: string };
}

export function isStepStateEvent(event: ChatStateEvent): event is ChatStateEventByType<'step'> {
  return event.type === 'step';
}

export function isErrorStateEvent(event: ChatStateEvent): event is ChatStateEventByType<'error'> {
  return event.type === 'error';
}

export function isMessageStateEvent(
  event: ChatStateEvent
): event is ChatStateEventByType<'message'> {
  return event.type === 'message';
}

export function isProgressStart(event: CustomEvent): event is ProgressStartCustomEvent {
  return event.name === 'progress-start';
}

export function isProgressDone(event: CustomEvent): event is ProgressDoneCustomEvent {
  return event.name === 'progress-done';
}

export function isProgressError(event: CustomEvent): event is ProgressErrorCustomEvent {
  return event.name === 'progress-error';
}

export function isThinkingEvent(event: ChatStateEvent): event is ChatStateEventByType<'thinking'> {
  return event.type === 'thinking';
}
