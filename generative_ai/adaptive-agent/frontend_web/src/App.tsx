import { SidebarProvider } from '@/components/ui/sidebar';
import Pages from '@/pages';

export function App() {
  return (
    <SidebarProvider>
      <Pages />
    </SidebarProvider>
  );
}
