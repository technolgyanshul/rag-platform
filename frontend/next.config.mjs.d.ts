declare module "./next.config.mjs" {
  const config: {
    allowedDevOrigins: string[];
    rewrites: () => Promise<Array<{ source: string; destination: string }>>;
  };

  export default config;
}
