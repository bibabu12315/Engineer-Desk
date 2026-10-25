import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import { CaptureUpdateAction } from "@excalidraw/excalidraw";
import { shapeToElements, type WaveMeta } from "./toElements";
import type { BBox, Params, WaveFamily } from "./types";

/** 新的波形组 id */
export function newGroupId(): string {
  const c: Crypto | undefined = (globalThis as any).crypto;
  if (c && typeof c.randomUUID === "function") return `wave-${c.randomUUID()}`;
  return `wave-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * S3 提交：把波形几何作为 Excalidraw 原生元素注入场景。
 *
 * - 整组共享 groupId，可整组拖动/缩放/改色
 * - 一次 updateScene + CaptureUpdateAction.IMMEDIATELY → Ctrl+Z 一次撤掉整组
 * - 传入 replaceGroupId 时先删除旧组（原位重生成，Q1 闭环）
 */
export function commitWave(
  api: ExcalidrawImperativeAPI,
  family: WaveFamily,
  params: Params,
  box: BBox,
  opts: { replaceGroupId?: string | null; select?: boolean } = {}
): string {
  const groupId = opts.replaceGroupId ?? newGroupId();
  const shape = family.generate(params, box);

  const wave = shapeToElements(shape, {
    waveFamily: family.id,
    params: { ...params },
    bbox: { x: box.x, y: box.y, w: box.w, h: box.h },
    groupId,
  });

  let elements = api.getSceneElements();
  if (opts.replaceGroupId) {
    elements = elements.filter(
      (el) => (el as any)?.customData?.groupId !== opts.replaceGroupId
    );
  }

  const selectedElementIds: Record<string, true> = {};
  if (opts.select !== false) {
    for (const el of wave) selectedElementIds[el.id] = true;
  }

  api.updateScene({
    elements: [...elements, ...wave] as any,
    appState: { selectedElementIds } as any,
    captureUpdate: CaptureUpdateAction.IMMEDIATELY,
  });

  return groupId;
}

/** 删除一整个波形组 */
export function removeWaveGroup(
  api: ExcalidrawImperativeAPI,
  groupId: string
): void {
  const elements = api
    .getSceneElements()
    .filter((el) => (el as any)?.customData?.groupId !== groupId);
  api.updateScene({
    elements: elements as any,
    appState: { selectedElementIds: {} } as any,
    captureUpdate: CaptureUpdateAction.IMMEDIATELY,
  });
}

/** 场景命中测试：返回包含该点的波形组元信息 */
export function hitTestWave(
  elements: readonly { customData?: Record<string, any> }[],
  sx: number,
  sy: number
): WaveMeta | null {
  for (let i = elements.length - 1; i >= 0; i--) {
    const cd = elements[i]?.customData as any;
    if (!cd || typeof cd.waveFamily !== "string" || !cd.bbox) continue;
    const b = cd.bbox as BBox;
    // 包围盒外扩一点，便于命中细线
    const m = 8;
    if (sx >= b.x - m && sx <= b.x + b.w + m && sy >= b.y - m && sy <= b.y + b.h + m) {
      return cd as WaveMeta;
    }
  }
  return null;
}
