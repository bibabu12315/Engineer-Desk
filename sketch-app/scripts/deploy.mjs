/**
 * 把 sketch-app 的构建产物部署到 ../resources/sketch/
 *
 *   node scripts/deploy.mjs               # 轻量产物（不含中文手绘字体 Xiaolai）
 *   node scripts/deploy.mjs --with-cn     # 含中文手绘字体（+13MB）
 *
 * 说明：
 *   - 覆盖式镜像，不做整目录删除（目录里可能同时有别的工具在用）
 *   - 只额外拷贝 fonts/：手绘字体通过 window.EXCALIDRAW_ASSET_PATH="./" 在运行时
 *     按 URL 拉取（./fonts/xxx.woff2），Vite 不会打包，缺了就回落系统字体。
 *   - locales/ 不需要拷：语言包是源码里的动态 import，已被 Vite 打进 dist/assets/*.js
 */

import { cp, mkdir, readdir, rm, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const DIST = path.join(ROOT, "dist");
const TARGET = path.resolve(ROOT, "..", "resources", "sketch");
const FONTS_SRC = path.join(
  ROOT,
  "node_modules",
  "@excalidraw",
  "excalidraw",
  "dist",
  "prod",
  "fonts"
);

const withCn = process.argv.includes("--with-cn");

/** 拷贝 src → dst，并删除 dst 中 src 里已不存在的文件（镜像同步，不做整树删除） */
async function mirrorCopy(src, dst, filter) {
  await mkdir(dst, { recursive: true });

  // 1) 覆盖拷贝
  await cp(src, dst, { recursive: true, force: true, filter });

  // 2) 清理 dst 里的陈旧文件（源里已没有的）
  const keep = new Set();
  const walk = async (dir, base) => {
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      const rel = base ? `${base}/${entry.name}` : entry.name;
      if (filter && !filter(path.join(dir, entry.name), rel)) continue;
      if (entry.isDirectory()) await walk(path.join(dir, entry.name), rel);
      else keep.add(rel);
    }
  };
  await walk(src, "");

  let pruned = 0;
  const prune = async (dir, base) => {
    let entries;
    try {
      entries = await readdir(dir, { withFileTypes: true });
    } catch (_) {
      return;
    }
    for (const entry of entries) {
      const rel = base ? `${base}/${entry.name}` : entry.name;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        await prune(full, rel);
      } else if (!keep.has(rel)) {
        try {
          await rm(full, { force: true });
          pruned++;
        } catch (_) {
          /* 删不掉就留着，不影响运行 */
        }
      }
    }
  };
  await prune(dst, "");

  return pruned;
}

async function dirSize(dir) {
  let total = 0;
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) total += await dirSize(p);
    else total += (await stat(p)).size;
  }
  return total;
}

async function main() {
  if (!existsSync(DIST)) {
    console.error("[deploy] 找不到 dist/，请先执行：npm run build");
    process.exit(1);
  }
  if (!existsSync(FONTS_SRC)) {
    console.error("[deploy] 找不到 @excalidraw/excalidraw，请先执行：npm install");
    process.exit(1);
  }

  // 1) Vite 产物（index.html + assets/）
  const p1 = await mirrorCopy(DIST, TARGET);

  // 2) 手绘字体（可选排除中文字体 Xiaolai，13MB）
  const fontFilter = (src) => !(!withCn && src.split(path.sep).includes("Xiaolai"));
  const p2 = await mirrorCopy(FONTS_SRC, path.join(TARGET, "fonts"), fontFilter);

  const size = await dirSize(TARGET);
  console.log(
    `[deploy] 已部署到 ${TARGET}\n` +
      `         体积 ${(size / 1024 / 1024).toFixed(2)} MB · 清理陈旧文件 ${p1 + p2} 个 · ` +
      `中文手绘字体：${withCn ? "包含" : "已排除（--with-cn 可包含）"}`
  );
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
