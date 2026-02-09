import { Button } from '@/components/ui/button';

export function StartNewChat({ createChat }: { createChat: () => void }) {
  return (
    <section className="flex min-h-full flex-1 items-center justify-center px-6 py-12 text-center">
      <div className="flex w-full max-w-md flex-col items-center gap-6 rounded-lg border border-border/40 bg-background/60 px-8 py-10 shadow-xs">
        <div className="space-y-3">
          <p className="text-2xl font-semibold capitalize">No chats selected</p>
          <p className="text-sm text-muted-foreground">
            Choose an existing conversation in the sidebar or start a brand-new chat to begin.
          </p>
        </div>
        <Button size="lg" onClick={createChat}>
          Start new chat
        </Button>
      </div>
    </section>
  );
}
