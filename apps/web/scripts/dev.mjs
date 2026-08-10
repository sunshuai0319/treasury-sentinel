// Start the Next.js dev server without opening a browser.
// Keeping dev startup side-effect free makes Playwright and manual testing
// use the same command without spawning extra Chrome windows.
import { spawn } from "node:child_process";

const isWin = process.platform === "win32";
const child = spawn("next", ["dev", ...process.argv.slice(2)], {
  stdio: "inherit",
  shell: isWin
});

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => child.kill(sig));
}

child.on("exit", (code) => process.exit(code ?? 0));
