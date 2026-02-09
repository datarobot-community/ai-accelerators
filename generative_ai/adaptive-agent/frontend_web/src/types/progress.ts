export interface ProgressState {
  [actionName: string]: ProgressStep[];
}
export interface ProgressStep {
  id: string;
  name: string;
  done: boolean;
  error?: string;
}
