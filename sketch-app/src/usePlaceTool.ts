import { useCallback, useEffect, useRef, useState } from "react";
import {
  sceneCoordsToViewportCoords,
  viewportCoordsToSceneCoords,
} from "@excalidraw/excalidraw";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import { commitWave } from "./wavegen/place";
import type { BBox, Params, Vec2, WaveFamily } from "./wavegen/types";

/** 拖拽包围盒（视口 px） */
export interface ViewportRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** ghost 预览数据（全部为视口 px，直接用于 SVG 绘制） */
export interface GhostData {
  rect: ViewportRect;
  lanes: { name: string; color: string; points: Vec2[] }[];
  markers: { x: number; y1: number; y2: number; label?: string }[];
  caption?: { x: number; y: number; text: string };
  labelW: string;
  labelH: string;
}

/** 小于该尺寸视为误触，回落到默认尺寸单击放置（设计稿 §5） */
const MIN_DRAG_W = 40;
const MIN_DRAG_H = 24;
/** 位移小于该阈值视为单击（设计稿 §4） */
const CLICK_SLOP = 4;

export interface PlaceToolOptions {
  api: ExcalidrawImperativeAPI | null;
  /** 待发态：面板开启 且 当前工具为选择工具 */
  armed: boolean;
  family: WaveFamily;
  params: Params;
  /** 编辑态：提交时替换该组；为 null 表示新建 */
  editGroupId: string | null;
  /** 提交完成回调（用于退出编辑态） */
  onPlaced(): void;
}

const rectOf = (ax: number, ay: number, bx: number, by: number): ViewportRect => ({
  x: Math.min(ax, bx),
  y: Math.min(ay, by),
  w: Math.abs(bx - ax),
  h: Math.abs(by - ay),
});

/**
 * 放置状态机（设计稿 §4）
 *   S1 待发   —— 面板开 + 选择工具，画布显示十字光标
 *   S2 拖拽中 —— pointerdown 后移动，ghost 实时预览 + 宽高标注
 *   S3 提交   —— pointerup，注入原生元素并整组选中
 * 拖拽中 Esc / 右键 → 取消，回到 S1，参数保留
 */
export function usePlaceTool({
  api,
  armed,
  family,
  params,
  editGroupId,
  onPlaced,
}: PlaceToolOptions) {
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const startRef = useRef<{ x: number; y: number } | null>(null);
  const [ghost, setGhost] = useState<GhostData | null>(null);

  /** 视口 px → 场景坐标 */
  const toScene = useCallback(
    (vx: number, vy: number) => {
      const host = overlayRef.current;
      if (!api || !host) return { x: 0, y: 0 };
      const hr = host.getBoundingClientRect();
      const st = api.getAppState();
      return viewportCoordsToSceneCoords(
        { clientX: hr.left + vx, clientY: hr.top + vy },
        {
          zoom: st.zoom,
          offsetLeft: hr.left,
          offsetTop: hr.top,
          scrollX: st.scrollX,
          scrollY: st.scrollY,
        }
      );
    },
    [api]
  );

  /** 场景坐标 → 视口 px */
  const toViewport = useCallback(
    (p: Vec2): Vec2 => {
      const host = overlayRef.current;
      if (!api || !host) return [0, 0];
      const hr = host.getBoundingClientRect();
      const st = api.getAppState();
      const v = sceneCoordsToViewportCoords(
        { sceneX: p[0], sceneY: p[1] },
        {
          zoom: st.zoom,
          offsetLeft: hr.left,
          offsetTop: hr.top,
          scrollX: st.scrollX,
          scrollY: st.scrollY,
        }
      );
      return [v.x - hr.left, v.y - hr.top];
    },
    [api]
  );

  const cancel = useCallback(() => {
    startRef.current = null;
    setGhost(null);
  }, []);

  // 失活时清理拖拽状态
  useEffect(() => {
    if (!armed) cancel();
  }, [armed, cancel]);

  const buildGhost = useCallback(
    (rect: ViewportRect): GhostData | null => {
      if (!api) return null;
      const host = overlayRef.current;
      if (!host) return null;
      const hr = host.getBoundingClientRect();
      const st = api.getAppState();
      const view = {
        zoom: st.zoom,
        offsetLeft: hr.left,
        offsetTop: hr.top,
        scrollX: st.scrollX,
        scrollY: st.scrollY,
      };
      const a = viewportCoordsToSceneCoords(
        { clientX: hr.left + rect.x, clientY: hr.top + rect.y },
        view
      );
      const b = viewportCoordsToSceneCoords(
        { clientX: hr.left + rect.x + rect.w, clientY: hr.top + rect.y + rect.h },
        view
      );
      const box: BBox = { x: a.x, y: a.y, w: b.x - a.x, h: b.y - a.y };
      const shape = family.generate(params, box);

      const tx = (x: number) => (x + st.scrollX) * st.zoom.value;
      const ty = (y: number) => (y + st.scrollY) * st.zoom.value;

      return {
        rect,
        lanes: shape.lanes.map((l) => ({
          name: l.name,
          color: l.color,
          points: l.points.map(([px, py]) => [tx(px), ty(py)] as Vec2),
        })),
        markers: shape.markers.map((m) => ({
          x: tx(m.x),
          y1: ty(m.y1),
          y2: ty(m.y2),
          label: m.label,
        })),
        caption: shape.caption
          ? { x: tx(shape.caption.x), y: ty(shape.caption.y), text: shape.caption.text }
          : undefined,
        labelW: `${Math.round(rect.w)} px`,
        labelH: `${Math.round(rect.h)} px`,
      };
    },
    [api, family, params]
  );

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!api || !armed) return;
      if (e.button !== 0) return; // 只响应左键，右键交给 contextmenu 取消
      const host = e.currentTarget as HTMLElement;
      const hr = host.getBoundingClientRect();
      startRef.current = { x: e.clientX - hr.left, y: e.clientY - hr.top };
      host.setPointerCapture(e.pointerId);
      setGhost(buildGhost({ x: startRef.current.x, y: startRef.current.y, w: 0, h: 0 }));
      e.preventDefault();
      e.stopPropagation();
    },
    [api, armed, buildGhost]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const s = startRef.current;
      if (!s || !api) return;
      const hr = (e.currentTarget as HTMLElement).getBoundingClientRect();
      const rect = rectOf(s.x, s.y, e.clientX - hr.left, e.clientY - hr.top);
      setGhost(buildGhost(rect));
      e.stopPropagation();
    },
    [api, buildGhost]
  );

  const finish = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const s = startRef.current;
      if (!s || !api) return;
      const hr = (e.currentTarget as HTMLElement).getBoundingClientRect();
      const vx = e.clientX - hr.left;
      const vy = e.clientY - hr.top;
      const rect = rectOf(s.x, s.y, vx, vy);

      startRef.current = null;
      setGhost(null);
      try {
        (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
      } catch (_) {}

      const isClick = Math.abs(vx - s.x) < CLICK_SLOP && Math.abs(vy - s.y) < CLICK_SLOP;
      const tooSmall = rect.w < MIN_DRAG_W || rect.h < MIN_DRAG_H;

      let box: BBox;
      if (isClick || tooSmall) {
        // 单击放置：默认画幅，锚点 = 点击点左上（设计稿 §4）
        const d = family.defaultBox(params);
        const o = toScene(rect.x, rect.y);
        box = { x: o.x, y: o.y, w: d.w, h: d.h };
      } else {
        const p0 = toScene(rect.x, rect.y);
        const p1 = toScene(rect.x + rect.w, rect.y + rect.h);
        box = { x: p0.x, y: p0.y, w: p1.x - p0.x, h: p1.y - p0.y };
      }

      if (editGroupId) {
        // 编辑态下点击画布 = 另起一组并退出编辑
        commitWave(api, family, params, box, { replaceGroupId: null });
      } else {
        commitWave(api, family, params, box);
      }
      // 一次性放置：落一组就收工，下次用再点开「∿ 波形」（用户反馈 #4）
      onPlaced();
      e.stopPropagation();
    },
    [api, editGroupId, family, params, onPlaced, toScene]
  );

  const onContextMenu = useCallback(
    (e: React.MouseEvent) => {
      if (!startRef.current) return;
      e.preventDefault();
      cancel();
    },
    [cancel]
  );

  // 拖拽中 Esc 取消（设计稿 §4）
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && startRef.current) {
        cancel();
        e.stopPropagation();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [cancel]);

  return {
    overlayRef,
    ghost,
    dragging: startRef.current !== null,
    handlers: { onPointerDown, onPointerMove, onPointerUp: finish, onPointerCancel: cancel, onContextMenu },
  };
}
