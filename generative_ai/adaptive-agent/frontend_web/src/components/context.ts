import { createContext } from 'react';
import { HttpAgent } from '@ag-ui/client';
import type { useAgUiChat } from '@/hooks/use-ag-ui-chat';

export type AgUiChatReturn = ReturnType<typeof useAgUiChat>;

export const ChatContext = createContext<AgUiChatReturn>({
  agent: new HttpAgent({ url: '' }),
  /*state*/
  state: {},
  setState: () => {},
  chatId: '',
  events: [],
  setEvents: () => {},
  message: null,
  combinedEvents: [],
  setMessage: () => {},
  userInput: '',
  setUserInput: () => {},
  initialMessages: [],
  setInitialMessages: () => {},
  initialState: {},
  setInitialState: () => {},
  progress: {},
  setProgress: () => {},
  isAgentRunning: false,
  setIsAgentRunning: () => {},
  isThinking: false,
  setIsThinking: () => {},
  deleteProgress: () => {},
  setIsBackground: () => {},
  /*methods*/
  sendMessage: () => Promise.resolve(),
  registerOrUpdateTool: () => {},
  updateToolHandler: () => {},
  removeTool: () => {},
  getTool: () => null,
  /*resolver*/
  useFetchHistory: (() => ({})) as unknown as AgUiChatReturn['useFetchHistory'],
  isLoadingHistory: false,
  refetchHistory: (() => Promise.resolve(undefined)) as unknown as AgUiChatReturn['refetchHistory'],
});
