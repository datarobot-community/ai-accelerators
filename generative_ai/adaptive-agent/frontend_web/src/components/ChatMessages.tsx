import { type PropsWithChildren, useEffect, useRef } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { ChatMessagesMemo } from '@/components/ChatMessage';
import { ChatError } from '@/components/ChatError';
import {
  isErrorStateEvent,
  isMessageStateEvent,
  isStepStateEvent,
  type ChatStateEvent,
  isThinkingEvent,
} from '@/types/events';
import { StepEvent } from '@/components/StepEvent';
import { ThinkingEvent } from '@/components/ThinkingEvent.tsx';

export type ChatMessageProps = {
  isLoading: boolean;
  chatId: string;
  messages?: ChatStateEvent[];
} & PropsWithChildren;

const THRESHOLD = 50;

export function ChatMessages({ children, messages, isLoading, chatId }: ChatMessageProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const shouldAutoscrollRef = useRef<boolean>(true);
  const prevScrollRef = useRef<number>(0);

  const onChatScroll = () => {
    if (!scrollContainerRef.current) {
      return;
    }
    if (prevScrollRef.current > scrollContainerRef.current.scrollTop) {
      shouldAutoscrollRef.current = false;
    } else if (scrollContainerRef.current.scrollTop - prevScrollRef.current > THRESHOLD) {
      shouldAutoscrollRef.current = true;
    }
    prevScrollRef.current = scrollContainerRef.current.scrollTop;
  };

  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [chatId]);

  useEffect(() => {
    if (scrollContainerRef.current && shouldAutoscrollRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="messages gap-2" ref={scrollContainerRef} onScroll={onChatScroll}>
      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : (
        children ||
        (messages &&
          messages.map(m => {
            if (isErrorStateEvent(m)) {
              return <ChatError key={m.value.id} {...m.value} />;
            }
            if (isMessageStateEvent(m)) {
              return <ChatMessagesMemo key={m.value.id} {...m.value} />;
            }
            if (isStepStateEvent(m)) {
              return <StepEvent key={m.value.id} {...m.value} />;
            }
            if (isThinkingEvent(m)) {
              return <ThinkingEvent key={m.type} />;
            }
          }))
      )}
    </div>
  );
}
