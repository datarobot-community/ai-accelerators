import { NavLink, Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';

const navItems = [{ label: 'Connected sources', to: '/settings/sources' }];

export const SettingsLayout = () => {
  return (
    <div className="flex flex-1 h-full justify-center">
      {/* Side navigation within settings */}
      <aside className="w-56 p-4 space-y-2">
        <NavLink key="go-back" to="/" className={cn('gap-2 px-3 py-2')}>
          <X />
        </NavLink>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-accent',
                isActive && 'bg-accent text-accent-foreground'
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </aside>

      {/* Active tab content */}
      <main className="w-full max-w-3xl overflow-y-auto px-6">
        <Outlet />
      </main>
    </div>
  );
};
