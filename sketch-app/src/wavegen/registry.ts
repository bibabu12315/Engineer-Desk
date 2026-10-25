import type { Params, WaveFamily } from "./types";

/**
 * 波形族注册表
 *
 * 扩展方式：
 *   registerFamily({ id, label, schema, defaultBox, generate })
 * 面板会自动多出一个 tab 并按 schema 渲染字段 —— 加波形不动面板代码。
 */

const families: WaveFamily[] = [];

export function registerFamily(f: WaveFamily): WaveFamily {
  if (families.some((x) => x.id === f.id)) {
    console.warn(`[wavegen] 波形族 "${f.id}" 重复注册，已忽略`);
    return f;
  }
  families.push(f);
  return f;
}

export const listFamilies = (): readonly WaveFamily[] => families;

export const getFamily = (id: string): WaveFamily | undefined =>
  families.find((f) => f.id === id);

/** 取某族的默认参数快照（schema.value 的拷贝） */
export function defaultParams(f: WaveFamily): Params {
  const p: Params = {};
  for (const fd of f.schema) p[fd.key] = fd.value;
  return p;
}

/** 字段条件显隐求值：未声明 visibleWhen 视为恒显示 */
export function isVisible(
  fd: { visibleWhen?: (p: Params) => boolean },
  p: Params
): boolean {
  return fd.visibleWhen ? fd.visibleWhen(p) : true;
}

/** 按 schema 夹取并规整参数（防止手工编辑 / 旧版本数据越界） */
export function clampParams(f: WaveFamily, raw: Params | undefined): Params {
  const p = defaultParams(f);
  if (!raw) return p;
  for (const fd of f.schema) {
    if (!(fd.key in raw)) continue;
    const v = raw[fd.key];
    if (fd.kind === "number" && typeof v === "number" && Number.isFinite(v)) {
      const q = fd.precision ?? 0;
      const val = Math.min(fd.max, Math.max(fd.min, v));
      p[fd.key] = q > 0 ? Number(val.toFixed(q)) : Math.round(val);
    } else if (
      fd.kind === "option" &&
      typeof v === "string" &&
      fd.options.some((o) => o.value === v)
    ) {
      p[fd.key] = v;
    }
  }
  return p;
}
