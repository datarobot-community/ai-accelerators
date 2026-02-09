// These types are copied from @ai-sdk
// TODO update according to history API
import { ToolResult } from '@ai-sdk/provider-utils';

export type ContentPart =
  | TextUIPart
  | ReasoningUIPart
  | ToolInvocationUIPart
  | SourceUIPart
  | FileUIPart
  | StepStartUIPart;

export type MessageContent = {
  format: number;
  parts: ContentPart[];
  content: string;
};

/**
 * A text part of a message.
 */
export type TextUIPart = {
  type: 'text';
  /**
   * The text content.
   */
  text: string;
};
/**
 * A reasoning part of a message.
 */
export type ReasoningUIPart = {
  type: 'reasoning';
  /**
   * The reasoning text.
   */
  reasoning: string;
  details: Array<
    | {
        type: 'text';
        text: string;
        signature?: string;
      }
    | {
        type: 'redacted';
        data: string;
      }
  >;
};

/**
 * A tool invocation part of a message.
 */
export interface ToolInvocationData {
  state: string; // e.g. 'call' | 'result'
  toolCallId?: string;
  toolName: string;
  args: Record<string, unknown>;
  result?: string;
}

export type ToolInvocationUIPart = {
  type: 'tool-invocation';
  /**
   * The tool invocation.
   */
  toolInvocation: ToolInvocationData;
};
/**
 * A source part of a message.
 */
export type SourceUIPart = {
  type: 'source';
  /**
   * The source.
   */
  source: unknown;
};
/**
 * A file part of a message.
 */
export type FileUIPart = {
  type: 'file';
  mimeType: string;
  data: string;
};
/**
 * A step boundary part of a message.
 */
export type StepStartUIPart = {
  type: 'step-start';
};

export type ToolInvocation =
  | ({
      state: 'partial-call';
      step?: number;
    } & ToolCall<string, any>)
  | ({
      state: 'call';
      step?: number;
    } & ToolCall<string, any>)
  | ({
      state: 'result';
      step?: number;
    } & ToolResult<string, any, any>);

interface ToolCall<NAME extends string, INPUT> {
  toolCallId: string;
  toolName: NAME;
  input: INPUT;
  providerExecuted?: boolean;
  dynamic?: boolean;
}

export function isToolInvocationPart(part: ContentPart): part is ToolInvocationUIPart {
  return part.type === 'tool-invocation';
}
