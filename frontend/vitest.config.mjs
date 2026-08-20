import { defineConfig } from "vitest/config"
import react from "@vitejs/plugin-react"
import path from "path"
import { fileURLToPath } from "url"

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig({
  plugins: [react()],
  test: {
    // jsdom so component tests can render and query the DOM; plain unit
    // tests (query keys, retry policy, etc.) run fine under it too.
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
