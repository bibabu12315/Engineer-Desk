import { registerFamily } from "./registry";
import { GRID, WAVE_BLUE } from "./theme";
import { num, str, type BBox, type Params, type Vec2, type WaveShape } from "./types";

/** 画幅顶部留给标题的高度（场景 px） */
const CAPTION_H = 18;
/** 通道带内的上下留白（场景 px） */
const LANE_PAD = 6;

export type CountMode = "up" | "center" | "down";

const MODE_LABEL: Record<CountMode, string> = {
  up: "向上",
  center: "中央对齐",
  down: "向下",
};

/**
 * 三角波 / 锯齿波（对应芯片手册定时器 counter 的三种计数模式）：
 *   up     —— 上升-垂直回落（向上计数锯齿）
 *   center —— 升-降对称三角（中央对齐）
 *   down   —— 垂直上升-下降（向下计数锯齿）
 */
function triWave(
  ox: number, yHigh: number, yLow: number,
  T: number, n: number, mode: CountMode
): Vec2[] {
  const pts: Vec2[] = [];
  if (mode === "up") {
    pts.push([ox, yLow]);
    for (let k = 0; k < n; k++) {
      const a = ox + k * T;
      const b = a + T;
      pts.push([a, yLow], [b, yHigh], [b, yLow]);
    }
  } else if (mode === "center") {
    pts.push([ox, yLow]);
    for (let k = 0; k < n; k++) {
      const a = ox + k * T;
      const m = a + T / 2;
      const b = a + T;
      pts.push([a, yLow], [m, yHigh], [b, yLow]);
    }
  } else {
    // down：每个周期起点垂直跳到峰值，再线性下降
    pts.push([ox, yLow]);
    for (let k = 0; k < n; k++) {
      const a = ox + k * T;
      const b = a + T;
      pts.push([a, yLow], [a, yHigh], [b, yLow]);
    }
  }
  return pts;
}

export const triangleFamily = registerFamily({
  id: "tri",
  label: "三角波",

  schema: [
    { kind: "number", key: "N", label: "周期数", value: 5, min: 1, max: 40, step: 1 },
    {
      kind: "option",
      key: "mode",
      label: "计数模式",
      value: "center",
      options: [
        { value: "up", label: "向上" },
        { value: "center", label: "中央" },
        { value: "down", label: "向下" },
      ],
    },
    { kind: "number", key: "amp", label: "幅值（格）", value: 8, min: 1, max: 30, step: 1 },
  ],

  defaultBox(p: Params) {
    const N = Math.max(1, Math.round(num(p, "N", 5)));
    const amp = Math.max(1, Math.round(num(p, "amp", 8)));
    return { w: N * GRID, h: CAPTION_H + amp * GRID };
  },

  generate(p: Params, box: BBox): WaveShape {
    const N = Math.max(1, Math.round(num(p, "N", 5)));
    const mode = (str(p, "mode", "center") as CountMode) || "center";
    const T = box.w / N;

    const lanesTop = box.y + CAPTION_H;
    const lanesH = Math.max(LANE_PAD * 2 + 4, box.h - CAPTION_H);

    const points = triWave(
      box.x,
      lanesTop + LANE_PAD,
      lanesTop + lanesH - LANE_PAD,
      T,
      N,
      mode,
    );

    return {
      lanes: [{ name: "TRI", color: WAVE_BLUE, points }],
      markers: [],
      caption: {
        // 标题放画幅右上角（x = 右缘，转换后按文本宽度右对齐）
        x: box.x + box.w,
        y: box.y + 2,
        text: `三角波 · ${MODE_LABEL[mode] ?? "中央对齐"} · ${N} 周期`,
      },
    };
  },
});
