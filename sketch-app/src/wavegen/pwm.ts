import { registerFamily } from "./registry";
import { GRID, WAVE_BLUE, WAVE_BLUE_ALT } from "./theme";
import { num, type BBox, type Params, type Vec2, type WaveMarker, type WaveShape } from "./types";

/** 画幅顶部留给标题的高度（场景 px） */
const CAPTION_H = 18;
/** 通道带内的上下留白（场景 px），避免波形线贴边 */
const LANE_PAD = 6;

/**
 * 主路波形：低 → 高 → 低，每周期一个脉冲。
 * 与设计稿 §3 一致：从低电平起步，高电平宽 = D × 周期宽。
 */
function mainWave(ox: number, yHigh: number, yLow: number, T: number, high: number, n: number): Vec2[] {
  const pts: Vec2[] = [[ox, yLow]];
  for (let k = 0; k < n; k++) {
    const a = ox + k * T; // 上升沿
    const b = a + high;   // 下降沿
    pts.push([a, yLow], [a, yHigh], [b, yHigh], [b, yLow], [a + T, yLow]);
  }
  return pts;
}

/**
 * 互补路波形：高电平出现在主路的低电平区间，
 * 且上升沿延后 dt、下降沿提前 dt —— 即死区期间两管全关（设计稿 §3）。
 */
function compWave(
  ox: number, yHigh: number, yLow: number,
  T: number, high: number, n: number, dt: number
): Vec2[] {
  const pts: Vec2[] = [[ox, yLow]];
  for (let k = 0; k < n; k++) {
    const rise = ox + k * T + high + dt; // 主路关断 dt 后才开通
    const fall = ox + (k + 1) * T - dt;   // 主路开通 dt 前先关断
    if (fall <= rise) continue;           // 死区吃满整个低电平，跳过
    pts.push([rise, yLow], [rise, yHigh], [fall, yHigh], [fall, yLow]);
  }
  pts.push([ox + n * T, yLow]);
  return pts;
}

export const pwmFamily = registerFamily({
  id: "pwm",
  label: "PWM",

  schema: [
    { kind: "number", key: "N", label: "周期数", value: 5, min: 1, max: 40, step: 1 },
    { kind: "number", key: "D", label: "占空比 %", value: 40, min: 1, max: 99, step: 1 },
    {
      kind: "option",
      key: "comp",
      label: "互补 + 死区",
      value: "on",
      options: [
        { value: "on", label: "开" },
        { value: "off", label: "关" },
      ],
    },
    {
      kind: "number",
      key: "dt",
      label: "死区（格）",
      value: 0.5,
      min: 0,
      max: 4,
      step: 0.5,
      precision: 1,
      // 条件显隐：仅在「互补 + 死区」开启时出现
      visibleWhen: (p) => p.comp === "on",
    },
  ],

  defaultBox(p: Params) {
    const N = Math.max(1, Math.round(num(p, "N", 5)));
    const lanes = p.comp === "on" ? 2 : 1;
    return { w: N * GRID, h: CAPTION_H + lanes * GRID * 2 };
  },

  generate(p: Params, box: BBox): WaveShape {
    const N = Math.max(1, Math.round(num(p, "N", 5)));
    const D = Math.min(0.99, Math.max(0.01, num(p, "D", 40) / 100));
    const comp = p.comp === "on";
    const dt = Math.max(0, num(p, "dt", 0.5)) * GRID;

    const T = box.w / N;
    // 取整到 1px，保证边沿垂直（设计稿 §3）
    const high = Math.round(D * T);

    const lanesTop = box.y + CAPTION_H;
    const lanesH = Math.max(LANE_PAD * 2 + 4, box.h - CAPTION_H);
    const laneH = lanesH / (comp ? 2 : 1);

    const main: Vec2[] = mainWave(
      box.x, lanesTop + LANE_PAD, lanesTop + laneH - LANE_PAD, T, high, N
    );

    const lanes = [
      { name: "CHA2", color: WAVE_BLUE, points: main },
    ];

    const markers: WaveMarker[] = [];

    if (comp) {
      const alt: Vec2[] = compWave(
        box.x,
        lanesTop + laneH + LANE_PAD,
        lanesTop + laneH * 2 - LANE_PAD,
        T,
        high,
        N,
        dt,
      );
      lanes.push({ name: "CHB1", color: WAVE_BLUE_ALT, points: alt });

      // 死区边沿红色虚线：只标第一个周期，不画 T1~T4 文字标记；
      // 死区为 0 时无死区可言，不画任何标注线
      if (dt > 0) {
        const y1 = lanesTop - 4;
        const y2 = lanesTop + lanesH + 4;
        const edges: number[] = [
          box.x,               // 主路上升沿
          box.x + high,        // 主路下降沿
          box.x + high + dt,   // 互补路上升沿（死区结束）
          box.x + T - dt,      // 互补路下降沿（死区开始）
        ];
        edges
          .filter((x) => x >= box.x - 0.5 && x <= box.x + box.w + 0.5)
          .sort((a, b) => a - b)
          .forEach((x) => {
            markers.push({ x, y1, y2 });
          });
      }
    }

    const names = comp ? "互补" : "单路";
    return {
      lanes,
      markers,
      caption: {
        // 标题放画幅右上角（x = 右缘，转换后按文本宽度右对齐）
        x: box.x + box.w,
        y: box.y + 2,
        text: `PWM · ${names}`,
      },
    };
  },
});
