import apiClient from '../apiClient';
import { IUser } from './types';

export async function getCurrentUser(signal?: AbortSignal): Promise<IUser> {
  const { data } = await apiClient.get<IUser>('/v1/user/', { signal });
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/v1/logout/');
}
