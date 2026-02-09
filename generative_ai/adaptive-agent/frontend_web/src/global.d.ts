// global.d.ts

export {};

declare global {
  interface Window {
    ENV: {
      BASE_PATH?: string;
      API_PORT?: string;
    };
  }
}
