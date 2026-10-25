import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Excalidraw, viewportCoordsToSceneCoords } from "@excalidraw/excalidraw";
import type { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types";
import WavePanel from "./WavePanel";
import GhostOverlay from "./GhostOverlay";
import { usePlaceTool } from "./usePlaceTool";
import {
  clampParams,
  defaultParams,
  getFamily,
  listFamilies,
} from "./wavegen/registry";
import { commitWave, hitTestWave } from "./wavegen/place";
import type { Params } from "./wavegen/types";

// 波形族注册（副作用导入）：新增波形在此加一行，面板自动多一个 tab
import "./wavegen/pwm";
import "./wavegen/triangle";

/** 自动保存 key（设计稿 §5） */
const AUTOSAVE_KEY = "sketch-auto";
/** 自动保存节流间隔（ms） */
const AUTOSAVE_DELAY = 600;

interface EditTarget {
  groupId: string;
  familyId: string;
  bbox: { x: number; y: number; w: number; h: number };
}

function loadScene(): any | null {
  try {
    const raw = localStorage.getItem(AUTOSAVE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data || !Array.isArray(data.elements)) return null;
    return {
      elements: data.elements,
      appState: {
        viewBackgroundColor: data.appState?.viewBackgroundColor ?? "#FFFFFF",
        theme: data.appState?.theme === "dark" ? "dark" : "light",
        // 视口不还原：交给 scrollToContent，避免旧视口落在空白区
      },
      scrollToContent: true,
    };
  } catch (_) {
    return null;
  }
}

export default function App() {
  const [api, setApi] = useState<ExcalidrawImperativeAPI | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [activeTool, setActiveTool] = useState<string>("selection");
  const [islandLeft, setIslandLeft] = useState<number | null>(null);

  const stageRef = useRef<HTMLDivElement | null>(null);
  const saveTimer = useRef<number | null>(null);

  const families = listFamilies();
  const [familyId, setFamilyId] = useState<string>(families[0]?.id ?? "");
  const [params, setParams] = useState<Params>(() =>
    families[0] ? defaultParams(families[0]) : {}
  );
  const [edit, setEdit] = useState<EditTarget | null>(null);

  const family = getFamily(familyId) ?? families[0];

  /* ---------------- 自动保存 / 恢复 ---------------- */

  const onChange = useCallback(
    (els: readonly any[], st: any, files: any) => {
      if (st?.activeTool?.type && st.activeTool.type !== activeTool) {
        setActiveTool(st.activeTool.type);
      }
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(() => {
        try {
          localStorage.setItem(
            AUTOSAVE_KEY,
            JSON.stringify({
              elements: els,
              appState: {
                viewBackgroundColor: st?.viewBackgroundColor,
                theme: st?.theme,
              },
              files,
            })
          );
        } catch (e) {
          console.warn("[sketch] 自动保存失败", e);
        }
      }, AUTOSAVE_DELAY);
    },
    [activeTool]
  );

  useEffect(
    () => () => {
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
    },
    []
  );

  /* ---------------- 顶栏 island 定位（紧贴原生工具栏右侧） ---------------- */

  useLayoutEffect(() => {
    let ro: ResizeObserver | null = null;
    const measure = () => {
      const host = stageRef.current;
      if (!host) return;
      const bar =
        host.querySelector<HTMLElement>(".App-toolbar-container") ??
        host.querySelector<HTMLElement>(".App-toolbar");
      if (!bar) {
        setIslandLeft(null);
        return;
      }
      const br = bar.getBoundingClientRect();
      const hr = host.getBoundingClientRect();
      setIslandLeft(Math.round(br.right - hr.left + 8));
    };
    measure();
    const host = stageRef.current;
    const bar =
      host?.querySelector<HTMLElement>(".App-toolbar-container") ??
      host?.querySelector<HTMLElement>(".App-toolbar");
    if (bar && typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(measure);
      ro.observe(bar);
    }
    window.addEventListener("resize", measure);
    // Excalidraw 会重建顶栏 DOM，轮询兜底
    const t = window.setInterval(measure, 1500);
    return () => {
      ro?.disconnect();
      window.removeEventListener("resize", measure);
      window.clearInterval(t);
    };
  }, []);

  /* ---------------- 放置交互 ---------------- */

  // 待发态：面板开启 且 当前为选择工具（设计稿 §5：切换其它工具即暂停）
  const armed = panelOpen && activeTool === "selection";

  // 一次性放置：落完一组就关面板（用户反馈 #4）
  const onPlaced = useCallback(() => {
    setEdit(null);
    setPanelOpen(false);
  }, []);

  const { ghost, handlers, overlayRef } = usePlaceTool({
    api,
    armed,
    family,
    params,
    editGroupId: edit?.groupId ?? null,
    onPlaced,
  });

  // 编辑态：参数一变就原位重生成（Q1 闭环）
  const handleParamsChange = useCallback(
    (next: Params) => {
      setParams(next);
      if (edit && api && family) {
        commitWave(api, family, next, edit.bbox, { replaceGroupId: edit.groupId });
      }
    },
    [edit, api, family]
  );

  const handleFamilyChange = useCallback(
    (id: string) => {
      setFamilyId(id);
      setEdit(null); // 换族视为放弃编辑
      const f = getFamily(id);
      if (f) setParams(defaultParams(f));
    },
    []
  );

  const closePanel = useCallback(() => {
    setPanelOpen(false);
    setEdit(null);
  }, []);

  /* ---------------- 双击回填（Q1） ---------------- */

  useEffect(() => {
    const host = stageRef.current;
    if (!host || !api) return;
    const onDbl = (e: MouseEvent) => {
      const canvas = host.querySelector<HTMLElement>("canvas.excalidraw__canvas");
      if (!canvas) return;
      const r = canvas.getBoundingClientRect();
      const st = api.getAppState();
      const p = viewportCoordsToSceneCoords(
        { clientX: e.clientX, clientY: e.clientY },
        {
          zoom: st.zoom,
          offsetLeft: r.left,
          offsetTop: r.top,
          scrollX: st.scrollX,
          scrollY: st.scrollY,
        }
      );
      const hit = hitTestWave(api.getSceneElements() as any, p.x, p.y);
      if (!hit) return;
      e.stopPropagation();
      e.preventDefault();
      const f = getFamily(hit.waveFamily);
      setFamilyId(hit.waveFamily);
      setParams(f ? clampParams(f, hit.params) : hit.params);
      setEdit({
        groupId: hit.groupId,
        familyId: hit.waveFamily,
        bbox: { ...hit.bbox },
      });
      setPanelOpen(true);
    };
    host.addEventListener("dblclick", onDbl, true);
    return () => host.removeEventListener("dblclick", onDbl, true);
  }, [api]);

  /* ---------------- 快捷键 ---------------- */

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
        return;
      }
      if (e.key === "w" || e.key === "W") {
        setPanelOpen((v) => !v);
        e.preventDefault();
      } else if (e.key === "Escape") {
        if (panelOpen) {
          setPanelOpen(false);
          setEdit(null);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panelOpen]);

  const initialData = useRef(loadScene()).current;

  /* ---------------- 自检钩子（仅 URL 参数显式触发） ----------------
   * ?panel=1      启动即打开波形面板
   * ?demo=pwm|tri 启动即在场景里落一组默认参数波形，用于无头验证注入链路
   * ?dt=0         覆盖 PWM demo 的死区参数（如 dt=0 验证无标注线）
   */
  useEffect(() => {
    if (!api) return;
    const q = new URLSearchParams(window.location.search);
    if (q.get("panel") === "1") setPanelOpen(true);
    const demo = q.get("demo");
    if (!demo) return;
    // 延迟落图：等 Excalidraw 完成 initialData 恢复与 langCode 初始化，
    // 否则场景初始化会把先注入的元素冲掉
    const t = window.setTimeout(() => {
      const fam = getFamily(demo === "tri" ? "tri" : "pwm");
      if (!fam) return;
      const params = defaultParams(fam);
      const dtQ = q.get("dt");
      if (demo === "pwm" && dtQ !== null) params.dt = Number(dtQ) || 0;
      commitWave(api, fam, params, { x: 120, y: 160, w: 560, h: 240 }, {
        select: false,
      });
    }, 800);
    return () => window.clearTimeout(t);
  }, [api]);

  return (
    <div className="sketch-stage" ref={stageRef}>
      <div className="excalidraw-wrapper">
        <Excalidraw
          excalidrawAPI={(a) => setApi(a)}
          onChange={onChange}
          initialData={initialData ?? undefined}
          langCode="zh-CN"
          UIOptions={{ canvasActions: { loadScene: true, saveToActiveFile: true } }}
        />
      </div>

      {/* 顶栏波形入口（紧贴原生工具栏右侧） */}
      <div
        className="wave-island-anchor"
        style={{ left: islandLeft === null ? "calc(50% + 210px)" : islandLeft }}
      >
        <div
          className={`wave-island${panelOpen ? " on" : ""}`}
          title="波形生成器（W）"
          onClick={() => {
            setPanelOpen((v) => !v);
            setEdit(null);
          }}
        >
          <span className="ico">∿</span>
          <span>波形</span>
        </div>
      </div>

      {/* 浮动属性卡 */}
      <WavePanel
        open={panelOpen}
        familyId={familyId}
        params={params}
        editing={edit !== null}
        onClose={closePanel}
        onFamilyChange={handleFamilyChange}
        onParamsChange={handleParamsChange}
      />

      {/* 待发态覆盖层：接管画布指针事件做放置 */}
      {armed ? (
        <div className="place-overlay" ref={overlayRef} {...handlers} />
      ) : null}

      <GhostOverlay ghost={ghost} />
    </div>
  );
}
