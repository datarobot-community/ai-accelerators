import React, { useState } from 'react';
import { ChatPage as ChatPageImplementation } from '@/components/page/ChatPage.tsx';

export const ChatPage: React.FC = () => {
  const [chatId, setChatId] = useState<string>(() => window.location.hash?.substring(1));

  const setChatIdHandler = (id: string) => {
    setChatId(id);
    window.location.hash = id;
  };

  return <ChatPageImplementation chatId={chatId} setChatId={setChatIdHandler} />;
};
