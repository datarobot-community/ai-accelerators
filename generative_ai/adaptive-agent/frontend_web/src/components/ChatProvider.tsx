import { type PropsWithChildren } from 'react';
import { useAgUiChat } from '@/hooks/use-ag-ui-chat';
import { ChatContext } from './context';
import { useFetchChats } from '@/api/chat';

export type ChatProviderInput = {
  chatId: string;
  refetchChats?: () => Promise<any>;
  runInBackground?: boolean;
  isNewChat?: boolean;
};
export type ChatProviderProps = ChatProviderInput & PropsWithChildren;

export function ChatProvider({
  children,
  chatId,
  runInBackground = false,
  isNewChat = false,
}: ChatProviderProps) {
  const { refetch } = useFetchChats();
  const refetchChats = refetch || (() => Promise.resolve());
  const value = useAgUiChat({
    chatId,
    isNewChat,
    runInBackground,
    refetchChats,
  });
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
