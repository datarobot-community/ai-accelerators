import { useChatContext } from '@/hooks/use-chat-context';
import { useEffect, useMemo } from 'react';
import z from 'zod/v4';
import type { Tool } from '@/types/tools';

export function useAgUiTool<Shape extends Record<string, unknown>>(toolWithHandler: Tool<Shape>) {
  const { handler, renderAndWait, render, ...rest } = toolWithHandler;
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const parameters = useMemo(() => {
    const json = z.toJSONSchema(rest.parameters);
    delete (json as Record<string, unknown>).$schema;
    delete (json as Record<string, unknown>).additionalProperties;
    return json;
  }, []);
  const name = `ui-${rest.name}`;
  const tool = useMemo(
    () => ({ ...rest, name, parameters }),
    [rest.enabled, rest.background, rest.description, name, parameters]
  );
  const context = useChatContext();

  useEffect(() => {
    context.registerOrUpdateTool(name, tool);
    context.updateToolHandler(name, {
      handler,
      renderAndWait,
      render,
    } as Pick<Tool, 'handler' | 'render' | 'renderAndWait'>);
    return () => {
      context.removeTool(name);
    };
  }, [tool.name, tool.description, tool.enabled, tool.background]);

  useEffect(() => {
    context.updateToolHandler(name, {
      handler,
      renderAndWait,
      render,
    } as Pick<Tool, 'handler' | 'render' | 'renderAndWait'>);
  }, [handler, renderAndWait, render, name]);
}
