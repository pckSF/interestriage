import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const rootDir = resolve(new URL("..", import.meta.url).pathname);
const unpackedDir = resolve(rootDir, "dist", "unpacked");

rmSync(resolve(rootDir, "dist"), { force: true, recursive: true });
mkdirSync(unpackedDir, { recursive: true });

cpSync(resolve(rootDir, "src", "manifest.json"), resolve(unpackedDir, "manifest.json"));
cpSync(resolve(rootDir, "src", "popup.html"), resolve(unpackedDir, "popup.html"));
cpSync(resolve(rootDir, "build", "popup.js"), resolve(unpackedDir, "popup.js"));
cpSync(resolve(rootDir, "build", "background.js"), resolve(unpackedDir, "background.js"));

execFileSync("zip", ["-qr", "../extension.zip", "."], {
  cwd: unpackedDir,
  stdio: "inherit"
});
