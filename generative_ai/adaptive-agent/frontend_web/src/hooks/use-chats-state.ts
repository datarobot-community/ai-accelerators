import { createStore, type StateCreator } from 'zustand/vanilla';
import { immer } from 'zustand/middleware/immer';
import type { MessageResponse } from '@/api/chat/types';
import type { ToolSerialized } from '@/types/tools';
import { type ChatStateEvent, type ChatStateEventByType } from '@/types/events';
import type { ProgressState } from '@/types/progress';
import { useStore } from 'zustand/react';
import { HttpAgent } from '@ag-ui/client';
import { createAgent } from '@/lib/agent';
import { ToolInvocationUIPart } from '@/types/message.ts';

export interface CreateChatArgs {
  id: string;
}

interface ChatState {
  id: string;
  agent: HttpAgent;
  state: Record<string, unknown>;
  events: ChatStateEvent[];
  message: MessageResponse | null;
  userInput: string;
  progress: ProgressState;
  initialState: Record<string, unknown>;
  isAgentRunning: boolean;
  isThinking: boolean;
  isBackground: boolean;
  setEvents: (events: ChatStateEvent[]) => void;
  finishStepEvent: (name: string) => void;
  addEvent: (event: ChatStateEvent) => void;
  addToolResult: ({ toolCallId, result }: { toolCallId: string; result: string }) => void;
  setState: (nextState: Record<string, unknown>) => void;
  setMessage: (message: MessageResponse | null) => void;
  setProgress: (cb: (progress: ProgressState) => void) => void;
  deleteProgress: (progressId: string) => void;
  setUserInput: (userInput: string) => void;
  setInitialState: (initialState: Record<string, unknown>) => void;
  setIsAgentRunning: (isAgentRunning: boolean) => void;
  setIsThinking: (isThinking: boolean) => void;
  setIsBackground: (background: boolean) => void;
  deleteChatState: () => void;
}

interface ChatsState {
  chats: Record<string, ChatState>;
  initialMessages: MessageResponse[];
  tools: Record<string, ToolSerialized>;
  addChat: (chatId: string) => ChatState;
}

const createChatSliceFactory = ({ id }: CreateChatArgs) => {
  const createChatSlice: StateCreator<
    ChatsState,
    [['zustand/immer', never]],
    [],
    ChatState
  > = set => {
    return {
      id,
      agent: createAgent({ threadId: id }),
      state: {},
      events: [],
      message: null,
      userInput: '',
      initialState: {},
      progress: {},
      isAgentRunning: false,
      isThinking: false,
      isBackground: false,
      /* access methods */
      finishStepEvent: (stepName: string) =>
        set(state => {
          if (state.chats[id]) {
            const runningStep = state.chats[id].events.find(
              event => (event as ChatStateEventByType<'step'>).value.name === stepName
            ) as ChatStateEventByType<'step'>;
            if (runningStep) {
              runningStep.value.isRunning = false;
            }
          }
        }),
      setEvents: (events: ChatStateEvent[]) =>
        set(state => {
          if (state.chats[id]) {
            // @ts-ignore
            state.chats[id].events = events;
          }
        }),
      addEvent: (event: ChatStateEvent) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].events.push(event);
          }
        }),
      addToolResult: ({ toolCallId, result }: { toolCallId: string; result: string }) => {
        set(state => {
          if (state.chats[id]) {
            let toolInvocationPart: ToolInvocationUIPart | null = null;
            state.chats[id].events.some(event => {
              return (event.value as MessageResponse).content?.parts.some(part => {
                if ((part as ToolInvocationUIPart).toolInvocation?.toolCallId === toolCallId) {
                  toolInvocationPart = part as ToolInvocationUIPart;
                  return true;
                }
                return false;
              });
            });
            if (toolInvocationPart) {
              (toolInvocationPart as ToolInvocationUIPart).toolInvocation.result = result;
              (toolInvocationPart as ToolInvocationUIPart).toolInvocation.state = 'result';
            }
          }
        });
      },
      setState: (nextState: Record<string, unknown>) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].state = nextState;
          }
        }),
      setMessage: (message: MessageResponse | null) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].message = message;
          }
        }),
      setProgress: (cb: (progress: ProgressState) => void) =>
        set(state => {
          if (state.chats[id]) {
            cb(state.chats[id].progress);
          }
        }),
      deleteProgress: (progressId: string) =>
        set(state => {
          if (state.chats[id]) {
            delete state.chats[id].progress[progressId];
          }
        }),
      setUserInput: (userInput: string) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].userInput = userInput;
          }
        }),
      setInitialState: (initialState: Record<string, unknown>) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].initialState = initialState;
          }
        }),
      setIsAgentRunning: (isAgentRunning: boolean) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].isAgentRunning = isAgentRunning;
          }
        }),
      setIsThinking: (isThinking: boolean) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].isThinking = isThinking;
          }
        }),
      setIsBackground: (background: boolean) =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].isBackground = background;
          }
        }),
      deleteChatState: () =>
        set(state => {
          if (state.chats[id]) {
            state.chats[id].agent.abortController.abort();
            delete state.chats[id];
          }
        }),
    };
  };

  return createChatSlice;
};

const chatsStore = createStore<ChatsState>()(
  immer((set, get, store) => ({
    chats: {},
    initialMessages: [],
    tools: {},
    addChat: id => {
      const createChatSlice = createChatSliceFactory({ id });
      const chatSlice = createChatSlice(set, get, store);
      set(state => {
        if (!state.chats[id]) {
          state.chats[id] = chatSlice;
        }
      });

      return chatSlice;
    },
  }))
);

export const useChat = (id: string): ChatState => {
  return useStore(chatsStore, state => state.chats[id]);
};

export const useHasChat = (id: string): boolean => {
  return useStore(chatsStore, state => !!state.chats[id]);
};

export const useAddChat = () => {
  return useStore(chatsStore, state => state.addChat);
};

export const useCurrentChatState = (): ((chatId: string) => ChatState | undefined) => {
  return (chatId: string) => chatsStore.getState().chats[chatId];
};
