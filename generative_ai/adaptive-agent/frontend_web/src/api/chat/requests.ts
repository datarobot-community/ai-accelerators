import { APIChat, APIChatWithMessages } from './types';
import apiClient from '../apiClient';

export async function getChats({ signal }: { signal: AbortSignal }) {
  return apiClient.get<APIChat[]>('v1/chat', { signal });
}

export async function deleteChat({ chatId }: any): Promise<void> {
  await apiClient.delete(`v1/chat/${chatId}`);
}

export async function updateChat({
  chatId,
  name,
}: {
  chatId: string;
  name: string;
}): Promise<void> {
  await apiClient.patch(`v1/chat/${chatId}`, { name });
}

export async function getChatHistory({ signal, chatId }: { signal: AbortSignal; chatId: string }) {
  return await apiClient.get<APIChatWithMessages>(`v1/chat/${chatId}`, { signal });
}
