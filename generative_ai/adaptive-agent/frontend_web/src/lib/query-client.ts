import { QueryCache, QueryClient } from '@tanstack/react-query';

const networkMode = process.env.NODE_ENV === 'development' ? 'always' : 'online';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      networkMode,
      refetchOnWindowFocus: false,
      retry: false,
    },
    mutations: {
      networkMode,
    },
  },
  queryCache: new QueryCache({
    onError: error => {
      console.error(error);
    },
  }),
});
