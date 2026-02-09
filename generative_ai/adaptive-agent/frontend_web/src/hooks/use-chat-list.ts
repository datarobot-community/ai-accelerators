import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { v4 as uuid } from 'uuid';
import type { ChatListItem } from '@/api/chat/types';
import { useDeleteChat, useFetchChats } from '@/api/chat';
import { useAddChat, useHasChat } from '@/hooks/use-chats-state.ts';

export type UseChatListParams = {
  chatId: string;
  setChatId: (id: string) => void;
  /**
   * Set to true if "No chats selected" state should be shown
   */
  showStartChat?: boolean;
};

export function useChatList({ chatId, setChatId, showStartChat = false }: UseChatListParams) {
  const [newChat, setNewChat] = useState<ChatListItem | null>(null);
  const newChatRef = useRef<ChatListItem | null>(null);
  const hasChat = useHasChat(chatId);

  const addChatToState = useAddChat();
  const { mutateAsync: deleteChatMutation, isPending: isLoadingDeleteChat } = useDeleteChat();
  const { data: chats, isLoading: isLoadingChats, refetch } = useFetchChats();

  useEffect(() => {
    if (chats?.some(chat => chat.id === newChat?.id)) {
      setNewChat(null);
    }
  }, [chats]);

  useEffect(() => {
    newChatRef.current = newChat;
  });

  useLayoutEffect(() => {
    if (!hasChat && chatId && !isLoadingChats) {
      addChatToState(chatId);
    }
    if (!hasChat && !chatId && !isLoadingChats && !showStartChat) {
      addChatHandler();
    }
  }, [hasChat, chatId, isLoadingChats]);

  const chatsWithNew = useMemo(() => {
    if (chats?.some(chat => chat.id === newChat?.id)) {
      return chats;
    }
    return newChat ? [newChat, ...(chats || [])] : chats;
  }, [chats, newChat]);

  const refetchChats = (): Promise<any> => {
    return newChatRef.current ? refetch() : Promise.resolve();
  };

  /**
   * Returns new chat id
   */
  const createChat = (name: string): string => {
    const newChatID = uuid();
    setNewChat({
      id: newChatID,
      name: name,
      userId: '',
      createdAt: new Date(),
      updatedAt: null,
    });
    addChatToState(newChatID);
    return newChatID;
  };

  const deleteChat = (chatId: string) => {
    return deleteChatMutation({ chatId }).then(() => refetch());
  };

  useEffect(() => {
    if (isLoadingChats || !chats || chats?.find(c => c.id === chatId)) {
      return;
    }
    if (!chats.length) {
      addChatHandler();
    } else {
      setChatId(chats[0].id);
    }
  }, [chats, isLoadingChats]);

  function addChatHandler() {
    const newChatID = createChat('New');
    setChatId(newChatID);
  }

  function deleteChatHandler(id: string, callbackFn: () => void) {
    deleteChat(id)
      .then(() => {
        refetchChats();
      })
      .catch(error => console.error(error))
      .finally(callbackFn);
  }

  return {
    isNewChat: newChat?.id === chatId,
    hasChat,
    chatId,
    setChatId,
    chats: chatsWithNew,
    newChat,
    setNewChat,
    isLoadingChats,
    refetchChats,
    deleteChat,
    isLoadingDeleteChat,
    addChatHandler,
    deleteChatHandler,
  };
}
