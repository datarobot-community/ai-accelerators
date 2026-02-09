/**
 * Get the base URL with proper path handling for deployed environments
 * Trims trailing slash
 */
export const getBaseUrl = (): string => {
  // Get current URL and trim trailing slash if present
  const url = window.location.href;
  return url.endsWith('/') ? url.slice(0, -1) : url;
};

/**
 * Get a full URL by appending a path to the base URL
 * @param path - The path to append (will be normalized to start with /)
 */
export const getUrl = (path: string = ''): string => {
  const baseUrl = getBaseUrl();
  // Ensure path starts with / if it's not empty
  const normalizedPath = path && !path.startsWith('/') ? `/${path}` : path;
  return `${baseUrl}${normalizedPath}`;
};
