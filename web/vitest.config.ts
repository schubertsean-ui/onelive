import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // `*.test.ts` at the web root is included so `middleware.test.ts` is
    // COLLECTED. It is the only file that can exercise the auth boundary's
    // decisions, and a test file the runner never picks up is worse than none:
    // it looks like coverage in the diff and runs nowhere.
    include: ["*.test.ts", "lib/**/*.test.ts", "app/**/*.test.{ts,tsx}"],
    environment: "node",
  },
});
