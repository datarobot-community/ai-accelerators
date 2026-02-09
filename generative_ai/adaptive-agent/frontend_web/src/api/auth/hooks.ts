import { useQuery, useMutation } from '@tanstack/react-query';
import { getCurrentUser, logout as logoutRequest } from './requests';
import { IUser } from './types';

export const authKeys = {
  currentUser: ['auth', 'me'] as const,
};

export const useCurrentUser = () => {
  return useQuery<IUser, Error>({
    queryKey: authKeys.currentUser,
    queryFn: () => getCurrentUser(),
    retry: false,
    staleTime: 60000, // User shouldn't suddenly change, set longer stale time
  });
};

export const useLogout = () => {
  return useMutation<void, Error>({
    mutationFn: () => logoutRequest(),
  });
};
