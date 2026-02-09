import { useContext } from 'react';
import { ChatContext } from '@/components/context';

export function useChatContext() {
  return useContext(ChatContext);
}
