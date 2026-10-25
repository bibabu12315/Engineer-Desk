# Engineer Sketch × 波形生成器 · 实现说明（V2.1-a + V2.1-b）

> 依据：`docs/EngineerDesk-sketch-design.html`（Rev2 主稿）+ `docs/EngineerDesk-wavegen-interaction.html`（Rev3 交互专项）
> 日期：2026-10-25

---

## 1. 与设计稿的差异（3 处，均有实测依据）

| # | 设计稿原方案 | 实际实现 | 原因 |
|---|---|---|---|
| D1 | §1/§5：双击 `resources/sketch/index.html`，用系统浏览器以 `file://` 打开 | **本地 HTTP 服务（127.0.0.1:8756 起）+ 系统浏览器** | **实测推翻前提**：Excalidraw 0.18 官方 dist 只发 ES module，浏览器在 `file://` 下因 CORS 直接不执行 `<script type="module">`（Edge 156 实测页面白屏）；手绘字体 woff2 同样被 CORS 拦截。走 127.0.0.1 后手绘风格 / 语言包 / undo 完整保留，且依然完全离线、无 Node 依赖 |
| D2 | §8：强调色 `#6965DB`（Rev3 mock） | **`#FF9F0A`（主工具强调橙）** | 主稿 §8 明确「品牌色对齐主工具」。代码里只有 `wavegen/theme.ts` 的 `ACCENT` 和 `style.css` 的 `--sk-accent` 两处，想换回紫色改这两行即可 |
| D3 | 打包体积 +1~2MB | **resources/sketch ≈ 8.1MB（默认不含中文字体）** | Excalidraw 自带 Mermaid/图表懒加载 chunk（约 2.5MB，保留以保证功能完整）。**中文手绘字体 Xiaolai 占 13MB，默认排除**（构建脚本加 `--with-cn` 可包含）；排除后中文回退系统字体，其余手绘字体（Excalifont 等，约 0.5MB）完整保留 |

## 2. 交付清单

```
sketch-app/                      # Vite + React + TS 工程（唯一长期维护的前端源码）
├── src/
│   ├── App.tsx                  # 壳：Excalidraw 内嵌 + 自动保存 + 顶栏 island + 双击回填 + 快捷键
│   ├── WavePanel.tsx            # 浮动属性卡：族 tabs + schema 渲染 + 可拖拽标题栏（位置记忆）
│   ├── usePlaceTool.ts          # 放置状态机 S1 待发 / S2 拖拽 ghost / S3 提交 + Esc/右键取消
│   ├── GhostOverlay.tsx         # ghost SVG 预览（不进 scene，不污染 undo 栈）
│   └── wavegen/
│       ├── types.ts  theme.ts   # 类型 + 配色/格宽令牌（GRID=20px）
│       ├── registry.ts          # 族注册表 + 参数夹取（加波形只 registerFamily，面板零改动）
│       ├── pwm.ts               # 单路 / 互补+死区（上升沿延后 dt、下降沿提前 dt）+ T1~T4 标注
│       ├── triangle.ts          # 向上 / 中央对齐 / 向下三种计数模式
│       ├── toElements.ts        # 几何 → Excalidraw 元素（groupIds + customData 注入）
│       └── place.ts             # commitWave（updateScene + IMMEDIATELY）/ 命中测试 / 删组
└── scripts/deploy.mjs           # 镜像同步 dist → resources/sketch（不做整目录删除）

src/services/sketch_service.py   # 本地 HTTP 服务（约 130 行）+ 健康检查 + 端口顺延 + 退出关闭
src/ui/main_window.py            # 格式栏新增 ✏️ 按钮（最右侧）→ _open_sketch()
main.py                          # aboutToQuit → sketch_service.shutdown()
build.bat / EngineerDesk.spec    # 打包加入 --add-data resources/sketch
.gitignore                       # 新增 sketch-app/node_modules/
```

构建产物 `resources/sketch/`（index.html + assets/ + fonts/）**入库**，clone 后无需 Node 即可打包 exe。

## 3. 常用命令

```bash
cd sketch-app
npm install          # 首次 / 依赖变更后
npm run dev          # 本地调试（热更新，http://localhost:5173）
npm run build        # 产出 dist/
npm run deploy       # dist + 字体 → ../resources/sketch/（--with-cn 含中文手绘字体）
```

改完前端后重跑 `build && deploy` 即可，Python 侧无需动。

## 4. 自检钩子（无头验证用，也可日常排查）

URL 参数，仅显式触发：
- `?panel=1` —— 启动即打开波形面板
- `?demo=pwm` / `?demo=tri` —— 启动即在场景里落一组默认参数波形（验证注入链路）
- `<html data-boot-error="...">` —— 启动期脚本错误会写到该属性，白屏时先看它

## 5. 验收状态（对照 Rev3 §6 五条）

| 验收项 | 状态 |
|---|---|
| 点「∿ 波形」→ 左上浮出属性卡，画布布局零变化；再点 / W / Esc 收起 | ✅ 截图实测（island 紧贴原生工具栏右侧，激活态高亮） |
| PWM / 三角波 tab 切换，字段只显示当前族的；互补关 → 死区行消失 | ✅ schema + visibleWhen 实现，面板截图验证 |
| 画布单击 → 默认尺寸落图；拖拽 → ghost 跟手 + 宽高标注 → 松手转正并整组选中 | ⚠️ 代码按稿实现（视口↔场景坐标换算走官方 `viewportCoordsToSceneCoords`），**无头环境无法模拟拖拽，待人工点一下确认手感** |
| 拖拽中 Esc 取消无残留；连续放置参数不丢 | ⚠️ 同上，待人工验证 |
| 双击已生成波形组 → 面板回填参数 → 改参原位重生成 | ⚠️ 同上，待人工验证 |

已验证的底层链路：波形注入（PWM 互补+死区 + T1~T4 红虚线、三角波三种模式）✅、自动保存/恢复 ✅、本地服务/字体加载 ✅、PySide6 离屏冒烟（按钮存在、服务起、健康检查、字体 200、退出清理）✅。

## 6. 已知边界 / 后续（V2.1-c）

- **端口**：8756 起顺延 20 个；端口变了自动保存的 localStorage origin 也变（数据仍在旧 origin 里）。已关 `SO_REUSEADDR`，避免 Windows 上与占用端口的程序静默错绑。
- **中文手绘字体**：默认不含（-13MB）。要手绘中文，`npm run deploy -- --with-cn`。
- Engineer Desk 退出后，浏览器里已打开的画板标签仍可编辑和自动保存（localStorage 在浏览器侧），只是刷新需要服务在跑。
- 未做（按主稿排期）：多泳道一键成组、移相全桥模板、File System Access 按日期存档到 `data/sketches/`、多场景切换。

## 7. Rev4 用户反馈修订（5 点，全部已实现并截图验证）

| # | 反馈 | 实现 | 验证 |
|---|---|---|---|
| 1 | 红色虚线只标第一个周期的死区；T1/T2 标记移到图形下方 | `pwm.ts`：markers 边沿数组只取第一周期（`edges = [x, x+high, x+high+dt, x+T-dt]`）；`toElements.ts`/`GhostOverlay.tsx`：T 标记 y 改为 `m.y2 + 4`（转换后）/ `m.y2 + 14`（ghost） | ✅ 截图确认 T1~T4 在波形下方，红虚线仅覆盖第一周期 |
| 2 | 标题去掉通道名，"PWM 互补 CHA2/CHB1" → "互补PWM" | `pwm.ts` caption 文案改 `PWM · 互补` / `PWM · 单路` | ✅ 截图确认 |
| 3 | 标题移到右上角 | caption `x = bbox 右缘` + `textAlign: "right"`；ghost 用 `textAnchor="end"` | ✅ 截图确认（"PWM · 互补"、"三角波 · 中央对齐 · 5 周期" 均在右上） |
| 4 | 一次性放置：落一组后自动收起面板，下次再点 ✏️ | `usePlaceTool.finish()` 末尾无条件 `onPlaced()`；`App.tsx` 的 `onPlaced` → `setEdit(null); setPanelOpen(false)` | ✅ 代码按稿实现（无头环境无法模拟点击，待人工点一下确认） |
| 5 | 界面英文 → 中文 | `<Excalidraw langCode="zh-CN">` + 面板/提示文案全部中文 | ✅ 截图确认（工具栏提示、面板字段、"素材库"等均中文） |

另修复：`?demo=pwm|tri` 自检注入被 Excalidraw 场景初始化冲掉的问题 —— `App.tsx` demo 钩子改为 800ms 延迟落图。headless 截图需加 `--virtual-time-budget=6000`，否则会截在注入前。

Rev4 补充（同日第 2 轮反馈）：**T1~T4 文字标记整体去掉**，红色虚线保留（仍只标第一周期死区）。改动仅 `pwm.ts` 一处（markers 不再带 label），已截图验证。

Rev4 补充（同日第 3 轮反馈）：**死区 = 0 时不再画红色虚线**（无死区就无标注意义）。`pwm.ts` 加 `if (dt > 0)`；自检钩子支持 `?demo=pwm&dt=0|1` 覆盖死区参数，dt=0 / dt=1 两组截图均已验证。
