import { useMemo, useRef, useState } from 'react'
import FaceCanvas from './components/FaceCanvas'
import { deformMesh } from './lib/api'
import { parseOBJ, serializeOBJ } from './lib/obj'
import {
  createDefaultEmotionWeights,
  createDefaultRegionWeights,
  getEmotionNames,
  getRegionNames,
  normalizeShapeKeyJSON,
} from './lib/shapeKeys'

const NAV_ITEMS = ['上传模型', '参数调节', '历史记录', '导出结果', '系统设置']

const EMOTION_PRESETS = {
  Happy: { Happy: 1, Sad: 0, Angry: 0, Surprise: 0, Disgust: 0, Fear: 0 },
  Sad: { Happy: 0, Sad: 1, Angry: 0, Surprise: 0, Disgust: 0, Fear: 0 },
  Angry: { Happy: 0, Sad: 0, Angry: 1, Surprise: 0, Disgust: 0, Fear: 0 },
  Surprise: { Happy: 0, Sad: 0, Angry: 0, Surprise: 1, Disgust: 0, Fear: 0 },
  Disgust: { Happy: 0, Sad: 0, Angry: 0, Surprise: 0, Disgust: 1, Fear: 0 },
  Fear: { Happy: 0, Sad: 0, Angry: 0, Surprise: 0, Disgust: 0, Fear: 1 },
}

const EMOTION_LABELS = {
  Happy: '快乐',
  Sad: '悲伤',
  Angry: '愤怒',
  Surprise: '惊讶',
  Disgust: '厌恶',
  Fear: '恐惧',
}

const REGION_LABELS = {
  Eyebrows: '眉毛',
  Eyes: '眼睛',
  Cheeks: '脸颊',
  Mouth: '嘴部',
  Jaw: '下颌',
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function downloadTextFile(filename, content, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value))
}

export default function App() {
  const [nav, setNav] = useState('上传模型')
  const [emotionWeights, setEmotionWeights] = useState(createDefaultEmotionWeights)
  const [regionWeights, setRegionWeights] = useState(createDefaultRegionWeights)
  const [transitionSpeed, setTransitionSpeed] = useState(0.3)
  const [continuousPreview, setContinuousPreview] = useState(true)
  const [normalizeWeights, setNormalizeWeights] = useState(false)
  const [model, setModel] = useState(null)
  const [shapeKeys, setShapeKeys] = useState({})
  const [historyRecords, setHistoryRecords] = useState([])
  const [statusMessage, setStatusMessage] = useState('请先上传 OBJ 模型。')
  const [shapeKeyInfo, setShapeKeyInfo] = useState('未加载')
  const [resultPositions, setResultPositions] = useState(null)
  const [loading, setLoading] = useState(false)
  const [objFile, setObjFile] = useState(null)
  const [shapeKeyFile, setShapeKeyFile] = useState(null)
  const objInputRef = useRef(null)
  const jsonInputRef = useRef(null)

  const effectiveEmotionWeights = useMemo(() => {
    if (!normalizeWeights) return emotionWeights
    const total = Object.values(emotionWeights).reduce((sum, value) => sum + value, 0)
    if (total <= 1e-8) return emotionWeights
    const normalized = {}
    for (const [key, value] of Object.entries(emotionWeights)) {
      normalized[key] = value / total
    }
    return normalized
  }, [emotionWeights, normalizeWeights])

  const dominantEmotion = useMemo(() => {
    const entries = Object.entries(effectiveEmotionWeights)
    if (!entries.length) return 'Neutral'
    const [name, value] = entries.reduce((best, current) => (current[1] > best[1] ? current : best), [
      'Neutral',
      0,
    ])
    return value > 0 ? name : 'Neutral'
  }, [effectiveEmotionWeights])

  async function handleOBJUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const nextModel = parseOBJ(text)
      setModel(nextModel)
      setObjFile(file)
      setResultPositions(null)
      setStatusMessage(`已加载模型：${file.name}`)
    } catch (error) {
      console.error(error)
      setStatusMessage(`OBJ 读取失败：${error.message}`)
    }
  }

  async function handleShapeKeyUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const json = JSON.parse(text)
      const normalized = normalizeShapeKeyJSON(json)
      setShapeKeys(normalized)
      setShapeKeyFile(file)
      setShapeKeyInfo(`已加载 ${Object.keys(normalized).length} 个 shape key`)
      setStatusMessage(`已加载 shape key 文件：${file.name}`)
    } catch (error) {
      console.error(error)
      setShapeKeyInfo('加载失败')
      setStatusMessage(`Shape Key JSON 读取失败：${error.message}`)
    }
  }

  function applyPreset(name) {
    setEmotionWeights(EMOTION_PRESETS[name])
    setStatusMessage(`已应用${EMOTION_LABELS[name]}预设。`)
  }

  function resetEmotions() {
    setEmotionWeights(createDefaultEmotionWeights())
  }

  function resetRegions() {
    setRegionWeights(createDefaultRegionWeights())
  }

  function restoreNeutral() {
    setEmotionWeights({ Happy: 0, Sad: 0, Angry: 0, Surprise: 0, Disgust: 0, Fear: 0 })
    setStatusMessage('已恢复到中立表情。')
  }

  function saveHistory() {
    setHistoryRecords((records) => [
      {
        time: new Date().toLocaleString(),
        emotionWeights: deepClone(emotionWeights),
        regionWeights: deepClone(regionWeights),
        transitionSpeed,
        normalizeWeights,
        dominantEmotion,
      },
      ...records,
    ])
    setStatusMessage('当前参数已保存到历史记录。')
  }

  function restoreHistory(record) {
    setEmotionWeights(record.emotionWeights)
    setRegionWeights(record.regionWeights)
    setTransitionSpeed(record.transitionSpeed)
    setNormalizeWeights(record.normalizeWeights)
    setStatusMessage(`已恢复记录：${record.time}`)
  }

  async function handleDeform() {
    if (!objFile || !model) {
      alert('请先上传 OBJ 文件')
      return
    }

    try {
      setLoading(true)
      const result = await deformMesh({
        objFile,
        shapeKeyFile,
        params: {
          emotion_values: emotionWeights,
          region_weights: regionWeights,
          normalize_weights: normalizeWeights,
        },
      })

      const flatVertices = new Float32Array(result.vertices.flat())
      setResultPositions(flatVertices)
      setStatusMessage(`后端驱动完成：${result.model_name ?? objFile.name}`)
    } catch (error) {
      console.error(error)
      setStatusMessage(`驱动失败：${error.message}`)
      alert(error.message || '驱动失败')
    } finally {
      setLoading(false)
    }
  }

  function exportJSON() {
    const payload = {
      dominantEmotion,
      emotionWeights,
      effectiveEmotionWeights,
      regionWeights,
      transitionSpeed,
      normalizeWeights,
      modelStats: model
        ? {
            vertexCount: model.vertexCount,
            faceCount: model.faceCount,
          }
        : null,
      shapeKeyNames: Object.keys(shapeKeys),
    }
    downloadTextFile('emotion_driver_params.json', JSON.stringify(payload, null, 2), 'application/json')
  }

  function exportOBJ() {
    if (!model || !resultPositions) return
    downloadTextFile('deformed_result.obj', serializeOBJ(resultPositions, model.indices), 'text/plain')
  }

  const previewMetrics = [
    { label: '当前模型', value: model ? `${model.vertexCount} 顶点` : '未加载' },
    { label: '主情绪', value: dominantEmotion === 'Neutral' ? '中立' : EMOTION_LABELS[dominantEmotion] ?? dominantEmotion },
    { label: '过渡速度', value: transitionSpeed.toFixed(2) },
  ]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand">3D 表情驱动</div>
          <div className="sidebar-caption">React + react-three-fiber 实时版本</div>
        </div>

        <nav className="nav-list">
          {NAV_ITEMS.map((item) => (
            <button
              key={item}
              className={`nav-item ${nav === item ? 'active' : ''}`}
              onClick={() => setNav(item)}
            >
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-status">
          <div className="status-title">当前状态</div>
          <div className="status-line">模型：{model ? '已加载' : '未加载'}</div>
          <div className="status-line">Shape Key：{shapeKeyInfo}</div>
          <div className="status-line">连续预览：{continuousPreview ? '开启' : '关闭'}</div>
        </div>

        <div className="sidebar-actions">
          <button className="secondary-button" onClick={saveHistory}>保存当前记录</button>
          <button className="secondary-button" onClick={resetEmotions}>恢复 app.py 默认值</button>
          <button className="secondary-button" onClick={resetRegions}>重置区域参数</button>
        </div>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <h1>多情绪 3D 人脸表情驱动工作台</h1>
            <p>上传 OBJ 模型，调节六种基础情绪与区域权重，并实时预览表情驱动后的彩色 3D 人脸。</p>
          </div>
          <div className="status-badge">{statusMessage}</div>
        </header>

        <section className="metrics-row">
          {previewMetrics.map((metric) => (
            <div className="metric-card" key={metric.label}>
              <div className="metric-label">{metric.label}</div>
              <div className="metric-value">{metric.value}</div>
            </div>
          ))}
        </section>

        <section className="preview-grid">
          <article className="panel-card preview-card">
            <div className="panel-title">原始模型</div>
            <div className="panel-subtitle">左侧显示上传后的基准 OBJ 模型，已加入皮肤、嘴唇、鼻部和眉眼区域着色。</div>
            <div className="canvas-frame">
              <FaceCanvas model={model} animated={false} />
            </div>
          </article>

          <article className="panel-card preview-card">
            <div className="panel-title">结果模型</div>
            <div className="panel-subtitle">右侧在同一个 mesh 上连续插值到目标表情，可以拖拽旋转查看五官细节。</div>
            <div className="canvas-frame">
              <FaceCanvas
                model={model}
                targetPositions={resultPositions ?? model?.basePositions}
                animated={continuousPreview}
                speed={transitionSpeed}
              />
            </div>
          </article>
        </section>

        {nav === '上传模型' && (
          <section className="panel-card">
            <div className="panel-title">上传模型</div>
            <div className="panel-subtitle">上传 OBJ 模型和可选的 shape_key_deltas.json。</div>

            <div className="upload-grid">
              <button className="primary-button" onClick={() => objInputRef.current?.click()}>
                上传 OBJ 模型
              </button>
              <button className="secondary-button" onClick={() => jsonInputRef.current?.click()}>
                上传 Shape Key JSON
              </button>
            </div>

            <input ref={objInputRef} type="file" accept=".obj" hidden onChange={handleOBJUpload} />
            <input ref={jsonInputRef} type="file" accept=".json" hidden onChange={handleShapeKeyUpload} />

            <div className="info-grid">
              <div className="info-card">
                <div className="info-label">顶点数</div>
                <div className="info-value">{model?.vertexCount ?? 0}</div>
              </div>
              <div className="info-card">
                <div className="info-label">面数</div>
                <div className="info-value">{model?.faceCount ?? 0}</div>
              </div>
              <div className="info-card">
                <div className="info-label">Shape Key</div>
                <div className="info-value">{Object.keys(shapeKeys).length}</div>
              </div>
            </div>
          </section>
        )}

        {nav === '参数调节' && (
          <section className="panel-card">
            <div className="panel-title">参数调节</div>
            <div className="panel-subtitle">预设按钮已与 app.py 的六种情绪保持一致。</div>

            <div className="preset-row">
              {getEmotionNames().map((preset) => (
                <button key={preset} className="chip-button" onClick={() => applyPreset(preset)}>
                  {EMOTION_LABELS[preset]}
                </button>
              ))}
            </div>

            <div className="form-grid">
              <div>
                <h3>情绪强度</h3>
                {getEmotionNames().map((name) => (
                  <label className="slider-block" key={name}>
                    <span>{EMOTION_LABELS[name]} <strong>{emotionWeights[name].toFixed(2)}</strong></span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={emotionWeights[name]}
                      onChange={(event) =>
                        setEmotionWeights((current) => ({
                          ...current,
                          [name]: clamp(Number(event.target.value), 0, 1),
                        }))
                      }
                    />
                  </label>
                ))}
              </div>

              <div>
                <h3>局部区域</h3>
                {getRegionNames().map((name) => (
                  <label className="slider-block" key={name}>
                    <span>{REGION_LABELS[name]} <strong>{regionWeights[name].toFixed(2)}</strong></span>
                    <input
                      type="range"
                      min="0"
                      max="1.5"
                      step="0.01"
                      value={regionWeights[name]}
                      onChange={(event) =>
                        setRegionWeights((current) => ({
                          ...current,
                          [name]: clamp(Number(event.target.value), 0, 1.5),
                        }))
                      }
                    />
                  </label>
                ))}
              </div>
            </div>

            <div className="form-grid compact">
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={continuousPreview}
                  onChange={(event) => setContinuousPreview(event.target.checked)}
                />
                <span>启用连续预览</span>
              </label>

              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={normalizeWeights}
                  onChange={(event) => setNormalizeWeights(event.target.checked)}
                />
                <span>归一化情绪权重</span>
              </label>
            </div>

            <label className="slider-block">
              <span>表情过渡速度 <strong>{transitionSpeed.toFixed(2)}</strong></span>
              <input
                type="range"
                min="0.05"
                max="1"
                step="0.01"
                value={transitionSpeed}
                onChange={(event) => setTransitionSpeed(Number(event.target.value))}
              />
            </label>

            <div className="action-row">
              <button className="primary-button" onClick={handleDeform} disabled={loading || !objFile}>
                {loading ? '驱动中...' : '应用驱动'}
              </button>
              <button className="secondary-button" onClick={restoreNeutral}>恢复中立表情</button>
              <button className="secondary-button" onClick={saveHistory}>保存当前记录</button>
            </div>
          </section>
        )}

        {nav === '历史记录' && (
          <section className="panel-card">
            <div className="panel-title">历史记录</div>
            <div className="panel-subtitle">保存每次调节参数，支持一键恢复。</div>
            <div className="history-list">
              {historyRecords.length === 0 && <div className="empty-state">还没有历史记录。</div>}
              {historyRecords.map((record, index) => (
                <article className="history-card" key={`${record.time}-${index}`}>
                  <div>
                    <div className="history-title">{record.time}</div>
                    <div className="history-meta">
                      主情绪：{record.dominantEmotion === 'Neutral' ? '中立' : EMOTION_LABELS[record.dominantEmotion]}
                    </div>
                  </div>
                  <button className="secondary-button" onClick={() => restoreHistory(record)}>
                    恢复这条记录
                  </button>
                </article>
              ))}
            </div>
          </section>
        )}

        {nav === '导出结果' && (
          <section className="panel-card">
            <div className="panel-title">导出结果</div>
            <div className="panel-subtitle">导出当前参数 JSON 或当前驱动后的 OBJ。</div>
            <div className="action-row">
              <button className="primary-button" onClick={exportJSON}>导出当前参数 JSON</button>
              <button className="secondary-button" onClick={exportOBJ} disabled={!model || !resultPositions}>
                导出当前结果 OBJ
              </button>
            </div>
          </section>
        )}

        {nav === '系统设置' && (
          <section className="panel-card">
            <div className="panel-title">系统设置</div>
            <div className="panel-subtitle">项目渲染与结果更新信息。</div>
            <div className="settings-grid">
              <div className="info-card">
                <div className="info-label">渲染模式</div>
                <div className="info-value">React + R3F</div>
              </div>
              <div className="info-card">
                <div className="info-label">模型材质</div>
                <div className="info-value">彩色皮肤</div>
              </div>
              <div className="info-card">
                <div className="info-label">结果更新</div>
                <div className="info-value">顶点连续插值</div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
