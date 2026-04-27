const API_BASE = 'http://127.0.0.1:8000'

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/api/health`)
  if (!res.ok) throw new Error('后端健康检查失败')
  return res.json()
}

export async function getConfig() {
  const res = await fetch(`${API_BASE}/api/config`)
  if (!res.ok) throw new Error('读取配置失败')
  return res.json()
}

export async function deformMesh({ objFile, shapeKeyFile, params }) {
  const formData = new FormData()
  formData.append('obj_file', objFile)
  formData.append('params_json', JSON.stringify(params))

  if (shapeKeyFile) {
    formData.append('shape_key_file', shapeKeyFile)
  }

  const res = await fetch(`${API_BASE}/api/deform`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    let detail = '后端请求失败'
    try {
      const err = await res.json()
      detail = err.detail || detail
    } catch {}
    throw new Error(detail)
  }

  return res.json()
}
