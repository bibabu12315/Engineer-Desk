import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  getFamily,
  isVisible,
  listFamilies,
  clampParams,
} from "./wavegen/registry";
import type { Field, NumberField, OptionField, Params } from "./wavegen/types";

/** 面板位置持久化 key（设计稿 §5：可拖拽标题栏移动位置，记忆到 localStorage） */
const POS_KEY = "sketch-wave-panel-pos";

/** 面板尺寸/锚点（设计稿 §2） */
const PANEL_W = 236;
const DEFAULT_POS = { left: 16, top: 64 };

interface WavePanelProps {
  open: boolean;
  familyId: string;
  params: Params;
  /** true 表示正在编辑画布上已有的波形组（改参即原位重生成） */
  editing: boolean;
  onClose(): void;
  onFamilyChange(id: string): void;
  onParamsChange(next: Params): void;
}

function loadPos(): { left: number; top: number } {
  try {
    const raw = localStorage.getItem(POS_KEY);
    if (!raw) return { ...DEFAULT_POS };
    const p = JSON.parse(raw);
    if (typeof p?.left === "number" && typeof p?.top === "number") {
      return { left: p.left, top: p.top };
    }
  } catch (_) {
    /* 忽略损坏数据 */
  }
  return { ...DEFAULT_POS };
}

/** 数字步进器行：[−] 值 [＋] */
function NumberRow({
  field,
  value,
  onChange,
}: {
  field: NumberField;
  value: number;
  onChange(v: number): void;
}) {
  const dec = field.precision ?? 0;
  const clamp = (v: number) =>
    Number(Math.min(field.max, Math.max(field.min, v)).toFixed(dec));
  return (
    <div className="fl">
      <label>{field.label}</label>
      <div className="stepper">
        <button type="button" onClick={() => onChange(clamp(value - field.step))}>
          −
        </button>
        <span className="v">{value.toFixed(dec)}</span>
        <button type="button" onClick={() => onChange(clamp(value + field.step))}>
          ＋
        </button>
      </div>
    </div>
  );
}

/** 选项段行：一排小按钮 */
function OptionRow({
  field,
  value,
  onChange,
}: {
  field: OptionField;
  value: string;
  onChange(v: string): void;
}) {
  return (
    <div className="fl">
      <label>{field.label}</label>
      <div className="segopt">
        {field.options.map((o) => (
          <i
            key={o.value}
            className={o.value === value ? "on" : ""}
            onClick={() => onChange(o.value)}
          >
            {o.label}
          </i>
        ))}
      </div>
    </div>
  );
}

export default function WavePanel({
  open,
  familyId,
  params,
  editing,
  onClose,
  onFamilyChange,
  onParamsChange,
}: WavePanelProps) {
  const [pos, setPos] = useState(loadPos);
  const dragRef = useRef<{ dx: number; dy: number } | null>(null);
  const [container, setContainer] = useState<{ w: number; h: number }>({
    w: window.innerWidth,
    h: window.innerHeight,
  });

  // 窗口尺寸变化时把面板夹回可视区
  useLayoutEffect(() => {
    const onResize = () =>
      setContainer({ w: window.innerWidth, h: window.innerHeight });
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    setPos((p) => ({
      left: Math.max(0, Math.min(p.left, Math.max(0, container.w - PANEL_W - 8))),
      top: Math.max(0, Math.min(p.top, Math.max(0, container.h - 80))),
    }));
  }, [container]);

  useEffect(() => {
    try {
      localStorage.setItem(POS_KEY, JSON.stringify(pos));
    } catch (_) {
      /* 隐私模式下可能写失败，忽略 */
    }
  }, [pos]);

  const onHeadDown = useCallback(
    (e: React.PointerEvent) => {
      if ((e.target as HTMLElement).closest(".x")) return; // 点关闭按钮不拖拽
      dragRef.current = { dx: e.clientX - pos.left, dy: e.clientY - pos.top };
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    },
    [pos.left, pos.top]
  );

  const onHeadMove = useCallback((e: React.PointerEvent) => {
    const d = dragRef.current;
    if (!d) return;
    setPos({
      left: Math.max(0, Math.min(e.clientX - d.dx, window.innerWidth - PANEL_W - 8)),
      top: Math.max(0, Math.min(e.clientY - d.dy, window.innerHeight - 80)),
    });
  }, []);

  const onHeadUp = useCallback((e: React.PointerEvent) => {
    dragRef.current = null;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch (_) {}
  }, []);

  if (!open) return null;

  const families = listFamilies();
  const family = getFamily(familyId) ?? families[0];
  if (!family) return null;

  const setParam = (key: string, v: number | string) => {
    const next = { ...params, [key]: v };
    // 参数变化后重新夹取，避免条件字段残留越界值
    onParamsChange(clampParams(family, next));
  };

  return (
    <div
      className="fpanel wave-panel"
      style={{ left: pos.left, top: pos.top, width: PANEL_W }}
    >
      <div
        className="fp-head"
        onPointerDown={onHeadDown}
        onPointerMove={onHeadMove}
        onPointerUp={onHeadUp}
        onPointerCancel={onHeadUp}
      >
        <b>∿ 波形{editing ? " · 编辑" : ""}</b>
        <span className="x" title="关闭（W / Esc）" onClick={onClose}>
          ✕
        </span>
      </div>

      <div className="seg2">
        {families.map((f) => (
          <i
            key={f.id}
            className={f.id === family.id ? "on" : ""}
            onClick={() => onFamilyChange(f.id)}
          >
            {f.label}
          </i>
        ))}
      </div>

      {/* 族切换时重新挂载，触发淡入过渡（160ms） */}
      <div className="fam-body" key={family.id}>
        {family.schema
          .filter((fd: Field) => isVisible(fd, params))
          .map((fd: Field) =>
            fd.kind === "number" ? (
              <NumberRow
                key={fd.key}
                field={fd}
                value={typeof params[fd.key] === "number" ? (params[fd.key] as number) : fd.value}
                onChange={(v) => setParam(fd.key, v)}
              />
            ) : (
              <OptionRow
                key={fd.key}
                field={fd}
                value={typeof params[fd.key] === "string" ? (params[fd.key] as string) : fd.value}
                onChange={(v) => setParam(fd.key, v)}
              />
            )
          )}
      </div>

      <div className="place-hint">
        {editing ? (
          <>
            改参即<b>原位重生成</b> · 关闭面板退出编辑
          </>
        ) : (
          <>
            在画布<b>单击放置</b>或<b>按住拖拽</b>定大小 · 放置后自动收起
          </>
        )}
      </div>
    </div>
  );
}
