import { type ReactNode } from 'react';
import { Topbar } from './Topbar';

interface PageLayoutProps {
  children: ReactNode;
}

export function PageLayout({ children }: PageLayoutProps) {
  return (
    <div className="flex flex-col min-h-screen bg-white">
      <Topbar />
      {children}
    </div>
  );
}
