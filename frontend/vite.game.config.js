
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "public/game",
    emptyOutDir: false,
    rollupOptions: {
      input: "../game/index.js",
      output: {
        entryFileNames: "game.bundle.js"
      }
    }
  }
});
