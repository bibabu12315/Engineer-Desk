import { ACCENT, MARK_RED, STROKE_MARKER, STROKE_WAVE } from "./wavegen/theme";
import type { GhostData } from "./usePlaceTool";

/**
 * S2 拖拽中的 ghost 预览。
 *
 * 画在独立 SVG overlay 上（不进 scene，不污染 undo 栈），
 * 坐标全部为视口 px，保证「拖到哪、松手就在哪」。
 */
export default function GhostOverlay({ ghost }: { ghost: GhostData | null }) {
  if (!ghost) return null;
  const { rect, lanes, markers, caption, labelW, labelH } = ghost;

  return (
    <svg className="ghost-svg" width="100%" height="100%">
      {/* 画幅包围盒 */}
      <rect
        x={rect.x}
        y={rect.y}
        width={rect.w}
        height={rect.h}
        rx={2}
        fill="rgba(255,159,10,0.05)"
        stroke={ACCENT}
        strokeWidth={1.4}
        strokeDasharray="4 3"
      />

      {/* 通道波形（半透明虚线） */}
      <g opacity={0.75}>
        {lanes.map((lane, i) => (
          <polyline
            key={`${lane.name}-${i}`}
            points={lane.points.map(([px, py]) => `${px},${py}`).join(" ")}
            fill="none"
            stroke={lane.color}
            strokeWidth={STROKE_WAVE}
            strokeDasharray="5 4"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
      </g>

      {/* 死区标注虚线 + 编号 */}
      {markers.map((m, i) => (
        <g key={`m-${i}`}>
          <line
            x1={m.x}
            y1={m.y1}
            x2={m.x}
            y2={m.y2}
            stroke={MARK_RED}
            strokeWidth={STROKE_MARKER}
            strokeDasharray="4 3"
          />
          {m.label ? (
            <text x={m.x} y={m.y2 + 14} fill={MARK_RED} fontSize={11} textAnchor="middle">
              {m.label}
            </text>
          ) : null}
        </g>
      ))}

      {/* 标题（右上角，右对齐） */}
      {caption ? (
        <text x={caption.x} y={caption.y + 10} fill="#8E8E99" fontSize={12} textAnchor="end">
          {caption.text}
        </text>
      ) : null}

      {/* 尺寸标注 */}
      <text
        x={rect.x + rect.w / 2}
        y={rect.y + rect.h + 16}
        fill={ACCENT}
        fontSize={11}
        fontWeight={600}
        textAnchor="middle"
      >
        {labelW}
      </text>
      <text
        x={rect.x + rect.w + 10}
        y={rect.y + rect.h / 2}
        fill={ACCENT}
        fontSize={11}
        fontWeight={600}
        textAnchor="middle"
        transform={`rotate(90 ${rect.x + rect.w + 10} ${rect.y + rect.h / 2})`}
      >
        {labelH}
      </text>
    </svg>
  );
}
