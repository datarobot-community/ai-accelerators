import { type ReactNode } from 'react';

interface ContentSectionProps {
  children: ReactNode;
  className?: string;
}

export function ContentSection({ children, className = '' }: ContentSectionProps) {
  return (
    <div className={`flex flex-col ${className}`}>
      {children}
    </div>
  );
}
