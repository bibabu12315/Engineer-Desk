import ReactDOM from "react-dom/client";
import App from "./App";
// Excalidraw 自身样式（工具栏 / 面板 / 画布布局全靠它）
import "@excalidraw/excalidraw/index.css";
import "./style.css";

// 注意：不套 React.StrictMode —— Excalidraw 在双次挂载下会重复初始化场景，
// 导致自动保存与波形放置状态机出现重复副作用。
ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
