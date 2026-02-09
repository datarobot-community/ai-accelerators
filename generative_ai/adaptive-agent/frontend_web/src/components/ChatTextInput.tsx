import { Loader2, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Textarea } from '@/components/ui/textarea';
import { KeyboardEvent, useRef, useState } from 'react';

export interface ChatTextInputProps {
  onSubmit: (text: string) => any;
  userInput: string;
  setUserInput: (value: string) => void;
  runningAgent: boolean;
}

export function ChatTextInput({
  onSubmit,
  userInput,
  setUserInput,
  runningAgent,
}: ChatTextInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [isComposing, setIsComposing] = useState(false);

  function keyDownHandler(e: KeyboardEvent) {
    if (
      e.key === 'Enter' &&
      !e.shiftKey &&
      !isComposing &&
      !runningAgent &&
      userInput.trim().length
    ) {
      if (e.ctrlKey || e.metaKey) {
        const el = ref.current;
        e.preventDefault();
        if (el) {
          const start = el.selectionStart;
          const end = el.selectionEnd;

          const newValue = userInput.slice(0, start) + '\n' + userInput.slice(end);
          setUserInput(newValue);
        }
      } else {
        e.preventDefault();
        onSubmit(userInput);
      }
    }
  }

  return (
    <div className="chat-text-input relative">
      <Textarea
        ref={ref}
        value={userInput}
        onChange={e => setUserInput(e.target.value)}
        onCompositionStart={() => setIsComposing(true)}
        onCompositionEnd={() => setIsComposing(false)}
        onKeyDown={keyDownHandler}
        className="pr-12 text-area"
      ></Textarea>
      {runningAgent ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="absolute bottom-2 right-2">
              <Button testId="send-message-disabled-btn" type="submit" size="icon" disabled>
                <Loader2 className="animate-spin" />
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent>Agent is running</TooltipContent>
        </Tooltip>
      ) : (
        <Button
          type="submit"
          onClick={() => onSubmit(userInput)}
          className="absolute bottom-2 right-2"
          size="icon"
          testId="send-message-btn"
          disabled={!userInput.trim().length}
        >
          <Send />
        </Button>
      )}
    </div>
  );
}
