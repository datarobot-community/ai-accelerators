import { useEffect, useMemo, useRef, useState } from 'react';
import { v4 as uuid } from 'uuid';
import { isCancel } from 'axios';
import {
  type RunAgentInput,
  type RunErrorEvent,
  type StateSnapshotEvent,
  type TextMessageContentEvent,
  type TextMessageStartEvent,
  type ToolCallEndEvent,
  type CustomEvent,
  type StepStartedEvent,
  type StepFinishedEvent,
} from '@ag-ui/core';
import type { AgentSubscriberParams, ToolCallResultEvent } from '@ag-ui/client';

import {
  createCustomMessageWidget,
  createTextMessageFromAgUiEvent,
  createTextMessageFromUserInput,
  createToolMessageFromAgUiEvent,
  messageToStateEvent,
} from '@/lib/mappers';
import { MessageResponse } from '@/api/chat/types.ts';
import { useFetchHistory } from '@/api/chat';
import type { Tool, ToolSerialized } from '@/types/tools';
import {
  isProgressDone,
  isProgressError,
  isProgressStart,
  type ChatStateEvent,
} from '@/types/events';
import type { ChatProviderInput } from '@/components/ChatProvider';
import { useChat, useCurrentChatState } from '@/hooks/use-chats-state';

export type UseAgUiChatParams = ChatProviderInput;

export function useAgUiChat({
  chatId,
  isNewChat,
  runInBackground,
  refetchChats = () => Promise.resolve(),
}: UseAgUiChatParams) {
  const {
    agent,
    state,
    setState,
    events,
    setEvents,
    finishStepEvent,
    addEvent,
    addToolResult,
    message,
    setMessage,
    progress,
    setProgress,
    deleteProgress,
    userInput,
    setUserInput,
    initialState,
    setInitialState,
    isAgentRunning,
    setIsAgentRunning,
    isThinking,
    setIsThinking,
    setIsBackground,
  } = useChat(chatId);
  const getCurrenChatState = useCurrentChatState();
  const [tools, setTools] = useState<Record<string, ToolSerialized>>({});
  const [initialMessages, setInitialMessages] = useState<MessageResponse[]>([]);
  const toolHandlersRef = useRef<
    Record<string, Pick<Tool, 'handler' | 'render' | 'renderAndWait'>>
  >({});

  const {
    data,
    isLoading: isLoadingHistory,
    refetch: refetchHistory,
  } = useFetchHistory({ chatId, enabled: !isAgentRunning && !isNewChat });

  const history = isNewChat ? [] : data;

  const agentRef = useRef(agent);
  const toolsRef = useRef(tools);

  useEffect(() => {
    agentRef.current = agent;
    toolsRef.current = tools;
  });

  useEffect(() => {
    setIsBackground(false);
    return () => {
      if (runInBackground && getCurrenChatState(chatId)?.isAgentRunning) {
        setIsBackground(true);
        return;
      }
      agent.abortController.abort();
    };
  }, [chatId]);

  async function sendMessage(message: string) {
    const messageId = uuid();
    agent.messages = [{ id: messageId, role: 'user', content: message }];

    const historyMessage = createTextMessageFromUserInput({ message, chatId, messageId });
    addEvent({ type: 'message', value: historyMessage });
    setUserInput('');
    setIsAgentRunning(true);
    setIsThinking(true);

    const { unsubscribe } = agent.subscribe({
      onTextMessageStartEvent(params: { event: TextMessageStartEvent } & AgentSubscriberParams) {
        const message = createTextMessageFromAgUiEvent(params.event);
        setIsThinking(false);
        setMessage(message);
      },
      onTextMessageContentEvent(
        params: {
          event: TextMessageContentEvent;
          textMessageBuffer: string;
        } & AgentSubscriberParams
      ) {
        const { event, textMessageBuffer } = params;
        const message = createTextMessageFromAgUiEvent(event, textMessageBuffer);
        setIsThinking(false);
        setMessage(message);
      },
      onTextMessageEndEvent() {
        if (!getCurrenChatState(chatId)?.message) {
          return;
        }
        addEvent({ type: 'message', value: getCurrenChatState(chatId)?.message! });
        setMessage(null);
      },
      onToolCallStartEvent() {
        setIsThinking(false);
      },
      onToolCallEndEvent(
        params: {
          event: ToolCallEndEvent;
          toolCallName: string;
          toolCallArgs: Record<string, unknown>;
        } & AgentSubscriberParams
      ) {
        const tool = toolsRef.current[params.toolCallName];
        const toolHandler = toolHandlersRef.current[params.toolCallName];
        const isBackground = getCurrenChatState(chatId)?.isBackground;
        if (tool && toolHandler?.handler && params.toolCallArgs) {
          const canRun = !isBackground || (isBackground && tool.background);
          if (isBackground) {
            console.debug('Background tool invocation', params, tool);
          }

          if (canRun) {
            toolHandler.handler(params.toolCallArgs);
            addEvent({
              type: 'message',
              value: createToolMessageFromAgUiEvent(
                params.event,
                params.toolCallName,
                params.toolCallArgs
              ),
            });
          }
        } else if (tool && toolHandler?.render && params.toolCallArgs) {
          addEvent({
            type: 'message',
            value: createCustomMessageWidget({
              toolCallArgs: params.toolCallArgs,
              toolCallName: params.toolCallName,
              threadId: chatId,
            }),
          });
        } else {
          addEvent({
            type: 'message',
            value: createToolMessageFromAgUiEvent(
              params.event,
              params.toolCallName,
              params.toolCallArgs
            ),
          });
        }
      },
      onToolCallResultEvent(
        params: {
          event: ToolCallResultEvent;
        } & AgentSubscriberParams
      ) {
        addToolResult({ toolCallId: params.event.toolCallId, result: params.event.content });
      },
      onStateSnapshotEvent(params: { event: StateSnapshotEvent } & AgentSubscriberParams) {
        setState(params.state);
      },
      onStateChanged(params: Omit<AgentSubscriberParams, 'input'> & { input?: RunAgentInput }) {
        setIsThinking(false);
        setState(params.state);
      },
      onStepStartedEvent(params: { event: StepStartedEvent } & AgentSubscriberParams) {
        setIsThinking(false);
        addEvent({
          type: 'step',
          value: {
            id: uuid(),
            threadId: chatId,
            createdAt: new Date(),
            name: params.event.stepName,
            isRunning: true,
          },
        });
      },
      onStepFinishedEvent(params: { event: StepFinishedEvent } & AgentSubscriberParams) {
        finishStepEvent(params.event.stepName);
      },
      onRunFinishedEvent() {
        unsubscribe();
        setIsAgentRunning(false);
        setIsThinking(false);
        refetchChats();
      },
      onCustomEvent(params: { event: CustomEvent } & AgentSubscriberParams) {
        const event = params.event;
        if (event?.name !== 'Heartbeat') {
          setIsThinking(false);
        }
        console.debug('onCustomEvent', params);

        if (isProgressStart(event)) {
          setProgress(state => {
            state[event.value.id] = event.value.steps;
          });
        } else if (isProgressDone(event)) {
          setProgress(state => {
            state[event.value.id] = state[event.value.id].map((s, i) =>
              event.value.step === i ? { ...s, done: true } : s
            );
          });
        } else if (isProgressError(event)) {
          setProgress(state => {
            state[event.value.id] = state[event.value.id].map((s, i) =>
              event.value.step === i ? { ...s, error: event.value.message } : s
            );
          });
        }
      },
      onRunErrorEvent(params: { event: RunErrorEvent } & AgentSubscriberParams) {
        unsubscribe();
        setIsAgentRunning(false);
        setIsThinking(false);
        if (params.event.rawEvent?.name === 'AbortError') {
          return;
        }
        addEvent({
          type: 'error',
          value: {
            id: uuid(),
            threadId: chatId,
            createdAt: new Date(),
            error: params.event.message,
          },
        });
      },
    });

    try {
      const result = await agent.runAgent({
        tools: Object.values(tools)
          .filter(tool => tool.enabled !== false)
          .map(({ background, ...tool }) => tool),
      });
      console.debug('runAgent result', result);
    } catch (error: any) {
      if (isCancel(error) || error?.name === 'AbortError') {
        return;
      }
      console.error(error);
    }
  }

  const combinedEvents: ChatStateEvent[] = useMemo(() => {
    const result: ChatStateEvent[] =
      !isLoadingHistory && !history?.length && initialMessages
        ? [...initialMessages.map(messageToStateEvent)]
        : [];
    if (history?.length) {
      const uiEvents = new Set(events.map(({ value }) => value.id));
      const historyWithoutUiEvents = history
        .filter(message => !uiEvents.has(message.id))
        .map(messageToStateEvent);
      result.push(...historyWithoutUiEvents);
    }
    result.push(...events);
    if (message) {
      result.push(messageToStateEvent(message));
    }

    if (isThinking) {
      result.push({
        type: 'thinking',
        value: {
          id: 'thinking',
          threadId: chatId,
          createdAt: new Date(),
        },
      });
    }
    return result;
  }, [history, events, message, isLoadingHistory, isThinking, initialMessages]);

  function registerOrUpdateTool(id: string, tool: ToolSerialized) {
    setTools(state => ({
      ...state,
      [id]: tool,
    }));
  }

  function updateToolHandler(
    name: string,
    handler: Pick<Tool, 'handler' | 'render' | 'renderAndWait'>
  ) {
    toolHandlersRef.current[name] = handler;
  }

  function removeTool(name: string) {
    setTools(state => {
      const copy = { ...state };
      delete copy[name];
      return copy;
    });
    delete toolHandlersRef.current[name];
  }

  function getTool(
    name: string
  ): (ToolSerialized & Pick<Tool, 'handler' | 'render' | 'renderAndWait'>) | null {
    if (tools[name] && toolHandlersRef.current[name]) {
      return {
        ...tools[name],
        ...toolHandlersRef.current[name],
      };
    }

    return null;
  }

  return {
    agent,
    /*state*/
    state,
    setState,
    chatId,
    events,
    setEvents,
    message,
    combinedEvents,
    setMessage,
    userInput,
    setUserInput,
    initialMessages,
    setInitialMessages,
    initialState,
    setInitialState,
    progress,
    setProgress,
    deleteProgress,
    isAgentRunning,
    setIsAgentRunning,
    isThinking,
    setIsThinking,
    setIsBackground,
    /*methods*/
    sendMessage,
    registerOrUpdateTool,
    updateToolHandler,
    removeTool,
    getTool,
    /*resolver*/
    useFetchHistory,
    isLoadingHistory,
    refetchHistory,
  };
}
