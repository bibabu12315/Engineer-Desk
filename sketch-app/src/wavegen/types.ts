/**
 * 波形生成器 · 公共类型
 *
 * 分层原则：
 *   wavegen/ 只负责「参数 + 包围盒 → 几何」，不含任何 Excalidraw 依赖（纯函数，可单测）。
 *   几何 → 画布元素的转换集中在 toElements.ts，便于将来换渲染后端。
 */

/** 二维点（场景坐标 px） */
export type Vec2 = [number, number];

/** 放置包围盒（场景坐标 px）—— 拖拽ghost 与最终元素共用同一套坐标 */
export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export type ParamValue = number | string | boolean;
export type Params = Record<string, ParamValue>;

/**
 * 数字步进器字段
 * 面板渲染为 [−] 值 [＋]
 */
export interface NumberField {
  kind: "number";
  key: string;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  /** 小数位（决定显示与夹取的精度，如 0.5 → 1 位） */
  precision?: number;
  /** 条件显隐：返回 false 时整行不渲染 */
  visibleWhen?: (p: Params) => boolean;
}

/** 选项段字段（面板渲染为一排小按钮） */
export interface OptionField {
  kind: "option";
  key: string;
  label: string;
  value: string;
  options: { value: string; label: string }[];
  visibleWhen?: (p: Params) => boolean;
}

export type Field = NumberField | OptionField;

/** 一条通道（泳道） */
export interface WaveLane {
  /** 通道名，如 CHA2 / CHB1 */
  name: string;
  color: string;
  /** 折线顶点，绝对场景坐标 */
  points: Vec2[];
}

/** 竖直标注虚线（死区边沿 / 采样点等） */
export interface WaveMarker {
  x: number;
  y1: number;
  y2: number;
  label?: string;
}

/** generate() 的产出：纯几何 */
export interface WaveShape {
  lanes: WaveLane[];
  markers: WaveMarker[];
  /** 画幅上方的标题，如「三角波 · 中央对齐 · 5 周期」 */
  caption?: { x: number; y: number; text: string };
}

/**
 * 一个波形族 = 面板上一个 tab + 一组参数 + 一个几何生成函数。
 * 新增波形只需 registerFamily({...})，面板代码零改动。
 */
export interface WaveFamily {
  id: string;
  label: string;
  schema: Field[];
  /** 单击放置时的默认画幅（场景 px） */
  defaultBox(p: Params): { w: number; h: number };
  /** 参数 + 包围盒 → 几何（纯函数） */
  generate(p: Params, box: BBox): WaveShape;
}

/** 安全取数：参数缺失或类型不符时回落到默认值 */
export const num = (p: Params, k: string, d: number): number =>
  typeof p[k] === "number" ? (p[k] as number) : d;

/** 安全取字符串 */
export const str = (p: Params, k: string, d: string): string =>
  typeof p[k] === "string" ? (p[k] as string) : d;
