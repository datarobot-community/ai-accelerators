import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export interface ConfirmDialogModalProps {
  open: boolean;
  setOpen: (state: boolean) => void;
  onSuccess: () => void;
  onDiscard: () => void;
  chatName: string;
}

export const ConfirmDialogModal = ({
  open,
  setOpen,
  onSuccess,
  onDiscard,
  chatName,
}: ConfirmDialogModalProps) => {
  const handleXButton = () => {
    setOpen(false);
  };

  return (
    <Dialog defaultOpen={false} open={open} onOpenChange={handleXButton}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Remove chat?</DialogTitle>
        </DialogHeader>
        <DialogDescription>This action will remove {chatName} chat.</DialogDescription>
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => {
              onDiscard();
              setOpen(false);
            }}
          >
            Cancel
          </Button>
          <Button
            onClick={() => {
              onSuccess();
              setOpen(false);
            }}
          >
            Remove
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
