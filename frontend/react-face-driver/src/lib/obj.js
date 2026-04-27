import * as THREE from 'three'

function parseFaceToken(token, vertexCount) {
  const [rawVertex] = token.split('/')
  const parsed = Number(rawVertex)
  if (!Number.isFinite(parsed)) return null
  if (parsed > 0) return parsed - 1
  if (parsed < 0) return vertexCount + parsed
  return null
}

export function normalizePositions(positions) {
  let minX = Infinity
  let minY = Infinity
  let minZ = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  let maxZ = -Infinity

  for (let i = 0; i < positions.length; i += 3) {
    const x = positions[i]
    const y = positions[i + 1]
    const z = positions[i + 2]
    if (x < minX) minX = x
    if (y < minY) minY = y
    if (z < minZ) minZ = z
    if (x > maxX) maxX = x
    if (y > maxY) maxY = y
    if (z > maxZ) maxZ = z
  }

  const centerX = (minX + maxX) / 2
  const centerY = (minY + maxY) / 2
  const centerZ = (minZ + maxZ) / 2
  const scale = Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1
  const normalized = new Float32Array(positions.length)

  for (let i = 0; i < positions.length; i += 3) {
    normalized[i] = (positions[i] - centerX) / scale
    normalized[i + 1] = (positions[i + 1] - centerY) / scale
    normalized[i + 2] = (positions[i + 2] - centerZ) / scale
  }

  return {
    positions: normalized,
    bounds: {
      min: [minX, minY, minZ],
      max: [maxX, maxY, maxZ],
      normalizedScale: scale,
    },
  }
}

export function parseOBJ(text) {
  const vertices = []
  const faces = []
  const lines = text.split(/\r?\n/)

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line || line.startsWith('#')) continue

    if (line.startsWith('v ')) {
      const [, ...rest] = line.split(/\s+/)
      if (rest.length < 3) continue
      vertices.push(Number(rest[0]), Number(rest[1]), Number(rest[2]))
      continue
    }

    if (line.startsWith('f ')) {
      const [, ...rest] = line.split(/\s+/)
      const polygon = rest
        .map((token) => parseFaceToken(token, vertices.length / 3))
        .filter((value) => value !== null)

      if (polygon.length < 3) continue

      for (let i = 1; i < polygon.length - 1; i += 1) {
        faces.push(polygon[0], polygon[i], polygon[i + 1])
      }
    }
  }

  if (vertices.length === 0 || faces.length === 0) {
    throw new Error('OBJ 文件中没有可用的顶点或面数据。')
  }

  const normalized = normalizePositions(new Float32Array(vertices))
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(normalized.positions.slice(), 3))
  geometry.setIndex(faces)
  geometry.computeVertexNormals()

  return {
    basePositions: normalized.positions,
    indices: Uint32Array.from(faces),
    vertexCount: normalized.positions.length / 3,
    faceCount: faces.length / 3,
    bounds: normalized.bounds,
    geometry,
    sourceText: text,
  }
}

export function serializeOBJ(positions, indices) {
  const lines = []
  for (let i = 0; i < positions.length; i += 3) {
    lines.push(`v ${positions[i].toFixed(6)} ${positions[i + 1].toFixed(6)} ${positions[i + 2].toFixed(6)}`)
  }

  for (let i = 0; i < indices.length; i += 3) {
    lines.push(`f ${indices[i] + 1} ${indices[i + 1] + 1} ${indices[i + 2] + 1}`)
  }

  return `${lines.join('\n')}\n`
}
