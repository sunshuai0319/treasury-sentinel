// 启动 Next.js dev server,就绪后自动打开浏览器。
// Next.js 的 `next dev` 没有内置 --open,这里解析其 "Local:" 输出行获取真实地址
// (端口被占用时 Next.js 会自动 +1,解析输出比硬编码端口更可靠)。
import { spawn } from "node:child_process";

const isWin = process.platform === "win32";
const child = spawn("next", ["dev"], {
  stdio: ["inherit", "pipe", "inherit"],
  shell: isWin,
});

let opened = false;
let tail = "";

child.stdout.on("data", (chunk) => {
  process.stdout.write(chunk);
  if (opened) return;
  tail = (tail + chunk.toString()).slice(-512);
  const match = tail.match(/Local:\s+(https?:\/\/\S+)/);
  if (match) openBrowser(match[1]);
});

function openBrowser(url) {
  opened = true;
  const target = isWin
    ? { cmd: "cmd", args: ["/c", "start", "", url] }
    : { cmd: process.platform === "darwin" ? "open" : "xdg-open", args: [url] };
  spawn(target.cmd, target.args, { stdio: "ignore" });
  console.log(`\n[dev] 已自动打开浏览器: ${url}`);
}

// 透传 Ctrl+C / kill 给子进程,保持与直接跑 next dev 一致的行为
for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => child.kill(sig));
}
child.on("exit", (code) => process.exit(code ?? 0));
