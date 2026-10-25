import { convertToExcalidrawElements } from "@excalidraw/excalidraw";
import {
  FONT_CAPTION,
  LABEL,
  MARK_RED,
  STROKE_MARKER,
  STROKE_WAVE,
} from "./theme";
import type { BBox, Params, WaveShape } from "./types";

/** convertToExcalidrawElements 接受的骨架类型 */
type Skeletons = Parameters<typeof convertToExcalidrawElements>[0];
/** convertToExcalidrawElements 返回的完整元素类型 */
export type WaveElement = ReturnType<typeof convertToExcalidrawElements>[number];

/** 写入元素 customData 的元信息（Q1：参数随场景保存） */
export interface WaveMeta {
  waveFamily: string;
  params: Params;
  bbox: BBox;
  /** 同一次生成的所有元素共享一个组 id，用于原位重生成时整体替换 */
  groupId: string;
}

/**
 * 几何 → Excalidraw 元素骨架。
 *
 * 映射规则（设计稿 §3）：
 *   一条通道 = 1 个 line 元素（折线顶点序列）
 *   一条标注 = 1 个红色 dashed line（可单独拖动）
 *   标题     = 1 个 text 元素
 */
export function shapeToElements(
  shape: WaveShape,
  meta: WaveMeta
): WaveElement[] {
  const skeletons: any[] = [];

  for (const lane of shape.lanes) {
    if (!lane.points.length) continue;
    const [x0, y0] = lane.points[0];
    skeletons.push({
      type: "line",
      x: x0,
      y: y0,
      // line 骨架的 points 相对元素原点，首点必须为 [0, 0]
      points: lane.points.map(([px, py]) => [px - x0, py - y0] as [number, number]),
      strokeColor: lane.color,
      backgroundColor: "transparent",
      fillStyle: "solid",
      strokeWidth: STROKE_WAVE,
      strokeStyle: "solid",
      roughness: 1,
      customData: { ...meta },
    });
  }

  for (const m of shape.markers) {
    skeletons.push({
      type: "line",
      x: m.x,
      y: m.y1,
      points: [
        [0, 0],
        [0, m.y2 - m.y1],
      ],
      strokeColor: MARK_RED,
      backgroundColor: "transparent",
      fillStyle: "solid",
      strokeWidth: STROKE_MARKER,
      strokeStyle: "dashed",
      roughness: 0,
      customData: { ...meta, markerLabel: m.label },
    });

    if (m.label) {
      skeletons.push({
        type: "text",
        x: m.x,
        // 标记编号放图形下方，避免遮挡波形
        y: m.y2 + 4,
        text: m.label,
        fontSize: FONT_CAPTION,
        textAlign: "center",
        verticalAlign: "top",
        strokeColor: MARK_RED,
        customData: { ...meta, markerLabel: m.label, markerX: m.x },
      });
    }
  }

  if (shape.caption) {
    skeletons.push({
      type: "text",
      // x 暂存右缘坐标，转换出文本宽度后再右对齐（见下方 map）
      x: shape.caption.x,
      y: shape.caption.y,
      text: shape.caption.text,
      fontSize: FONT_CAPTION,
      textAlign: "right",
      verticalAlign: "top",
      strokeColor: LABEL,
      customData: { ...meta, role: "caption" },
    });
  }

  const elements = convertToExcalidrawElements(skeletons as Skeletons);

  // 整组化：统一 groupId + customData，便于双击回填与整组替换
  return elements.map((el) => {
    const cd: Record<string, any> = { ...(el.customData ?? {}), ...meta };
    // 标题右对齐：Excalidraw 文本元素的 x 是文本框左缘，需按实测宽度回移
    let x = el.x;
    const raw = el.customData as any;
    if (raw?.role === "caption") {
      x = meta.bbox.x + meta.bbox.w - (el.width ?? 0);
    } else if (typeof raw?.markerX === "number") {
      // T1/T2 编号在标注线下方居中
      x = raw.markerX - (el.width ?? 0) / 2;
    }
    return {
      ...el,
      x,
      groupIds: [...(el.groupIds ?? []), meta.groupId],
      customData: cd,
    };
  }) as WaveElement[];
}

/** 判断元素是否属于波形组 */
export function waveMetaOf(el: { customData?: Record<string, any> }): WaveMeta | null {
  const cd = el?.customData;
  if (!cd || typeof cd !== "object") return null;
  if (typeof cd.waveFamily !== "string" || !cd.bbox) return null;
  return cd as unknown as WaveMeta;
}

/** 收集场景里所有波形组（groupId → 元素们 + 元信息） */
export function collectWaveGroups(
  elements: readonly { id: string; customData?: Record<string, any> }[]
): Map<string, { meta: WaveMeta; ids: Set<string> }> {
  const groups = new Map<string, { meta: WaveMeta; ids: Set<string> }>();
  for (const el of elements) {
    const meta = waveMetaOf(el);
    if (!meta) continue;
    let g = groups.get(meta.groupId);
    if (!g) {
      g = { meta, ids: new Set() };
      groups.set(meta.groupId, g);
    }
    g.ids.add(el.id);
  }
  return groups;
}
