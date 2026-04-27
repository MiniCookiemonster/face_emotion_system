const EMOTION_NAMES = ['Happy', 'Sad', 'Angry', 'Surprise', 'Disgust', 'Fear']
const REGION_NAMES = ['Eyebrows', 'Eyes', 'Cheeks', 'Mouth', 'Jaw']

function toTripletArray(value) {
  if (!value) return null

  if (Array.isArray(value) && value.length > 0) {
    if (Array.isArray(value[0])) return value
    if (typeof value[0] === 'number' && value.length % 3 === 0) {
      const triplets = []
      for (let i = 0; i < value.length; i += 3) {
        triplets.push([Number(value[i]), Number(value[i + 1]), Number(value[i + 2])])
      }
      return triplets
    }
  }

  if (typeof value === 'object') {
    if (Array.isArray(value.deltas)) return toTripletArray(value.deltas)
    if (Array.isArray(value.offsets)) return toTripletArray(value.offsets)
    if (Array.isArray(value.vertices)) return toTripletArray(value.vertices)
  }

  return null
}

export function normalizeShapeKeyJSON(input) {
  if (!input || typeof input !== 'object') {
    throw new Error('Shape Key JSON 结构无效。')
  }

  const candidateRoots = [input, input.shape_keys, input.shapeKeys, input.keys, input.blendshapes].filter(Boolean)
  const normalized = {}

  for (const root of candidateRoots) {
    for (const key of Object.keys(root)) {
      const triplets = toTripletArray(root[key])
      if (triplets) normalized[key] = triplets
    }
  }

  return normalized
}

export function createDefaultEmotionWeights() {
  return {
    Happy: 0.2,
    Sad: 0,
    Angry: 0,
    Surprise: 0.1,
    Disgust: 0,
    Fear: 0,
  }
}

export function createDefaultRegionWeights() {
  return {
    Eyebrows: 0.8,
    Eyes: 0.7,
    Cheeks: 0.6,
    Mouth: 1.0,
    Jaw: 0.5,
  }
}

export function getEmotionNames() {
  return EMOTION_NAMES
}

export function getRegionNames() {
  return REGION_NAMES
}
