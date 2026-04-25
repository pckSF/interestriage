import { cpSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const rootDir = resolve(new URL("..", import.meta.url).pathname);
const distDir = resolve(rootDir, "dist");
const assetsDir = resolve(distDir, "assets");

rmSync(distDir, { force: true, recursive: true });
mkdirSync(assetsDir, { recursive: true });

cpSync(resolve(rootDir, "src", "index.html"), resolve(distDir, "index.html"));
cpSync(resolve(rootDir, "build", "main.js"), resolve(assetsDir, "main.js"));
