# 多情绪 3D 人脸表情驱动系统（React + react-three-fiber）

这是一个从 Streamlit 升级到 **React + react-three-fiber + three.js** 的前端版本。

## 功能

- 左侧导航栏
- 中间双预览：原始模型 / 结果模型
- OBJ 上传
- Shape Key JSON 上传
- 实时表情连续驱动（同一个 mesh 顶点插值）
- 情绪与局部区域参数面板
- 历史记录恢复
- 导出当前参数 JSON
- 导出当前结果 OBJ

## 启动

```bash
npm install
npm run dev
```

浏览器打开终端显示的本地地址。

## 构成

- `src/App.jsx`：主界面与状态管理
- `src/components/FaceCanvas.jsx`：R3F 画布与连续顶点插值
- `src/lib/obj.js`：OBJ 解析、归一化、导出
- `src/lib/shapeKeys.js`：shape key 读取、区域 mask、变形计算

## 说明

当前版本优先解决你的核心问题：

1. 不再像 Streamlit 一样整页重跑导致“闪一下”
2. 右侧结果模型始终是同一个 mesh
3. 参数变化时只更新顶点数组

如果你后面要把你 Python 里的 `deform_mesh / compute_region_response / shape_key_driver` 逻辑完全对齐，主要改 `src/lib/shapeKeys.js` 里的 `computeDeformedPositions()` 即可。
