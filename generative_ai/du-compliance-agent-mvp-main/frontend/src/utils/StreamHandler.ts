/**
 * StreamHandler - Generic TypeScript utility for handling streaming JSON events from fetch APIs
 * 
 * @example
 * ```typescript
 * type MyStreamEvent = 
 *   | { type: 'start'; data: string }
 *   | { type: 'update'; progress: number }
 *   | { type: 'complete'; result: any };
 * 
 * const handler = new StreamHandler<MyStreamEvent>({
 *   url: '/api/stream',
 *   method: 'POST',
 *   headers: { 'Content-Type': 'application/json' },
 *   body: JSON.stringify({ query: 'example' }),
 *   onConnect: () => console.log('Connected'),
 *   onDisconnect: () => console.log('Disconnected'),
 *   onError: (error) => console.error(error),
 *   onComplete: () => console.log('Completed'),
 *   onEvent: (event) => console.log(event)
 * });
 * 
 * handler
 *   .on('start', (event) => console.log(event.data))
 *   .on('update', (event) => updateProgress(event.progress))
 *   .on('complete', (event) => displayResult(event.result));
 * 
 * await handler.start();
 * handler.close();
 * ```
 */

export interface StreamHandlerConfig<T> {
  url: string;
  method?: string;
  headers?: Record<string, string>;
  body?: BodyInit;
  signal?: AbortSignal;
  
  onConnect?: () => void;
  onDisconnect?: () => void;
  onReconnect?: (attempt: number) => void;
  onComplete?: () => void;
  onAbort?: () => void;
  onError?: (error: StreamError) => void;
  onEvent?: (event: T) => void;
}

export type StreamErrorType = 
  | 'network_error'
  | 'http_error'
  | 'parse_error'
  | 'stream_error'
  | 'abort_error';

export interface StreamError {
  type: StreamErrorType;
  message: string;
  originalError?: Error;
  statusCode?: number;
  statusText?: string;
  line?: string;
}

type EventListener<T> = (event: T) => void;

export class StreamHandler<T extends { type: string }> {
  private config: StreamHandlerConfig<T>;
  private listeners: Map<string, EventListener<any>[]> = new Map();
  private abortController: AbortController;
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private isActive = false;
  private hasCompleted = false;

  constructor(config: StreamHandlerConfig<T>) {
    this.config = {
      method: 'GET',
      ...config
    };
    
    this.abortController = new AbortController();
    
    if (config.signal) {
      config.signal.addEventListener('abort', () => {
        this.abortController.abort();
      });
    }
  }

  on<K extends T['type']>(
    eventType: K | '*',
    listener: EventListener<Extract<T, { type: K }>>
  ): this {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(listener);
    return this;
  }

  off<K extends T['type']>(
    eventType: K | '*',
    listener: EventListener<Extract<T, { type: K }>>
  ): this {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
    return this;
  }

  private emit(event: T): void {
    if (this.config.onEvent) {
      try {
        this.config.onEvent(event);
      } catch (error) {
        console.error('Error in onEvent callback:', error);
      }
    }

    const typeListeners = this.listeners.get(event.type) || [];
    const wildcardListeners = this.listeners.get('*') || [];
    
    [...typeListeners, ...wildcardListeners].forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error(`Error in event listener for ${event.type}:`, error);
      }
    });
  }

  private emitError(error: StreamError): void {
    if (this.config.onError) {
      try {
        this.config.onError(error);
      } catch (err) {
        console.error('Error in onError callback:', err);
      }
    }
  }

  async start(): Promise<void> {
    if (this.isActive) {
      throw new Error('Stream is already active');
    }

    this.isActive = true;
    this.hasCompleted = false;

    try {
      const response = await fetch(this.config.url, {
        method: this.config.method,
        headers: this.config.headers,
        body: this.config.body,
        signal: this.abortController.signal
      });

      if (!response.ok) {
        this.emitError({
          type: 'http_error',
          message: `HTTP ${response.status}: ${response.statusText}`,
          statusCode: response.status,
          statusText: response.statusText
        });
        this.cleanup();
        return;
      }

      if (this.config.onConnect) {
        try {
          this.config.onConnect();
        } catch (error) {
          console.error('Error in onConnect callback:', error);
        }
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      this.reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (this.isActive) {
        const { done, value } = await this.reader.read();

        if (done) {
          this.hasCompleted = true;
          if (this.config.onComplete) {
            try {
              this.config.onComplete();
            } catch (error) {
              console.error('Error in onComplete callback:', error);
            }
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;

          try {
            const event = JSON.parse(line) as T;
            this.emit(event);
          } catch (error) {
            this.emitError({
              type: 'parse_error',
              message: 'Failed to parse JSON event',
              originalError: error as Error,
              line: line
            });
          }
        }
      }
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          if (this.config.onAbort) {
            try {
              this.config.onAbort();
            } catch (err) {
              console.error('Error in onAbort callback:', err);
            }
          }
        } else {
          this.emitError({
            type: 'network_error',
            message: error.message,
            originalError: error
          });
        }
      }
    } finally {
      this.cleanup();
    }
  }

  abort(): void {
    if (this.isActive) {
      this.abortController.abort();
    }
  }

  close(): void {
    this.cleanup();
  }

  private cleanup(): void {
    if (this.reader) {
      try {
        this.reader.cancel();
      } catch (error) {
        console.error('Error canceling reader:', error);
      }
      this.reader = null;
    }

    if (this.isActive) {
      this.isActive = false;
      if (!this.hasCompleted && this.config.onDisconnect) {
        try {
          this.config.onDisconnect();
        } catch (error) {
          console.error('Error in onDisconnect callback:', error);
        }
      }
    }
  }

  isStreamActive(): boolean {
    return this.isActive;
  }

  hasStreamCompleted(): boolean {
    return this.hasCompleted;
  }
}

export async function streamJSON<T extends { type: string }>(
  config: StreamHandlerConfig<T>
): Promise<void> {
  const handler = new StreamHandler(config);
  await handler.start();
}

export default StreamHandler;
