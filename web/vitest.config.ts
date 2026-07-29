import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["lib/**/*.test.ts", "app/**/*.test.{ts,tsx}"],
    environment: "node",
  },
  // The app's tsconfig sets jsx:"preserve" for Next, which leaves JSX in the
  // emitted source and the bundler cannot parse it. Tests that import a PAGE
  // (rather than a lib module) need it transformed — and page-level tests are
  // the only ones that can prove "San Antonio cannot reach a user" rather than
  // "the helper works".
  //
  // This must be `oxc`, not `esbuild`: vitest 4 ships rolldown-vite, whose
  // transformer is oxc. Setting `esbuild` here is silently ignored (it prints
  // "esbuild options will be ignored" and then fails on the unparsed JSX).
  oxc: {
    jsx: { runtime: "automatic" },
  },
});
