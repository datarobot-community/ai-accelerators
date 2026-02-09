import axios from 'axios';

import { getApiUrl } from '@/lib/utils';

const baseApiUrl = getApiUrl();

const apiClient = axios.create({
  baseURL: baseApiUrl,
  headers: {
    Accept: 'application/json',
    'Content-type': 'application/json',
  },
  withCredentials: true,
});

export default apiClient;
