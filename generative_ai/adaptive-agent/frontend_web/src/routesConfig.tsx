import { PATHS } from '@/constants/path.ts';
import { lazy } from 'react';
import { Navigate } from 'react-router-dom';
import { SettingsSources } from './pages/SettingSources.tsx';
import { SettingsLayout } from './pages/SettingsLayout';
import { ChatPage } from './pages/Chat.tsx';
const OAuthCallback = lazy(() => import('./pages/OAuthCallback'));

export const appRoutes = [
  { path: PATHS.OAUTH_CB, element: <OAuthCallback /> },
  { path: PATHS.CHAT_PAGE, element: <ChatPage /> },
  {
    path: PATHS.SETTINGS.ROOT,
    element: <SettingsLayout />,
    children: [
      { index: true, element: <Navigate to="sources" replace /> },
      { path: 'sources', element: <SettingsSources /> },
    ],
  },
  { path: '*', element: <Navigate to={PATHS.CHAT_PAGE} replace /> },
];
