import { defineConfig } from 'astro/config';
export default defineConfig({
  site: 'https://rateterrain.com',
  trailingSlash: 'always',
  build: { format: 'directory' }
});
