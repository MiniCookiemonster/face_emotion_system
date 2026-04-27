import { OrbitControls } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'

function smoothstep(edge0, edge1, x) {
  const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0 || 1)))
  return t * t * (3 - 2 * t)
}

function ovalMask(x, y, centerX, centerY, radiusX, radiusY) {
  const dx = (x - centerX) / radiusX
  const dy = (y - centerY) / radiusY
  return Math.max(0, 1 - dx * dx - dy * dy)
}

function createFaceColors(positions) {
  const colors = new Float32Array(positions.length)
  const skin = new THREE.Color('#d8a07c')
  const warmSkin = new THREE.Color('#e7b08e')
  const cheekTint = new THREE.Color('#e89c91')
  const lip = new THREE.Color('#a84255')
  const brow = new THREE.Color('#2a1914')
  const nose = new THREE.Color('#c88969')
  const eyeShadow = new THREE.Color('#4f342c')

  for (let i = 0; i < positions.length; i += 3) {
    const x = positions[i]
    const y = positions[i + 1]
    const z = positions[i + 2]
    const absX = Math.abs(x)
    const color = skin.clone()

    const centerWarmth = Math.max(0, 1 - absX * 1.8) * Math.max(0, 1 - Math.abs(y) * 1.3)
    color.lerp(warmSkin, 0.25 * centerWarmth)

    const cheek = ovalMask(absX, y, 0.2, -0.03, 0.22, 0.14)
    color.lerp(cheekTint, Math.min(0.45, cheek * 0.42))

    const mouth = ovalMask(x, y, 0, -0.25, 0.26, 0.07)
    color.lerp(lip, Math.min(0.9, mouth * 0.85))

    const eyebrowBand = smoothstep(0.1, 0.16, y) * (1 - smoothstep(0.22, 0.3, y))
    const eyebrow = eyebrowBand * smoothstep(0.06, 0.14, absX) * (1 - smoothstep(0.36, 0.5, absX))
    color.lerp(brow, Math.min(0.9, eyebrow * 0.82))

    const eyeBand = smoothstep(0.0, 0.05, y) * (1 - smoothstep(0.09, 0.16, y))
    const eye = eyeBand * smoothstep(0.08, 0.16, absX) * (1 - smoothstep(0.34, 0.46, absX))
    color.lerp(eyeShadow, Math.min(0.68, eye * 0.58))

    const noseMask = ovalMask(x, y, 0, -0.03, 0.13, 0.24) * Math.max(0, 1 - Math.abs(z) * 0.3)
    color.lerp(nose, Math.min(0.55, noseMask * 0.38))

    colors[i] = color.r
    colors[i + 1] = color.g
    colors[i + 2] = color.b
  }

  return colors
}

function createGeometry(model, positions = model.basePositions) {
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.BufferAttribute(positions.slice(), 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(createFaceColors(positions), 3))
  geometry.setIndex(Array.from(model.indices))
  geometry.computeVertexNormals()
  geometry.computeBoundingSphere()
  return geometry
}

function FaceMaterial({ result = false }) {
  return (
    <meshPhysicalMaterial
      vertexColors
      roughness={0.52}
      metalness={0}
      clearcoat={0.12}
      clearcoatRoughness={0.8}
      sheen={0.22}
      side={THREE.DoubleSide}
      emissive={result ? '#150b0b' : '#0b0705'}
      emissiveIntensity={0.06}
    />
  )
}

function StaticFaceMesh({ model }) {
  const geometry = useMemo(() => createGeometry(model), [model])

  useEffect(() => () => geometry.dispose(), [geometry])

  return (
    <mesh geometry={geometry}>
      <FaceMaterial />
    </mesh>
  )
}

function AnimatedFaceMesh({ model, targetPositions, speed }) {
  const geometryRef = useRef(null)
  const displayedRef = useRef(model.basePositions.slice())
  const normalCooldownRef = useRef(0)

  useEffect(() => {
    displayedRef.current = model.basePositions.slice()
    if (!geometryRef.current) return
    geometryRef.current.setAttribute('position', new THREE.BufferAttribute(displayedRef.current, 3))
    geometryRef.current.setAttribute('color', new THREE.BufferAttribute(createFaceColors(displayedRef.current), 3))
    geometryRef.current.setIndex(Array.from(model.indices))
    geometryRef.current.computeVertexNormals()
    geometryRef.current.computeBoundingSphere()
  }, [model])

  useFrame((_, delta) => {
    const geometry = geometryRef.current
    if (!geometry || !targetPositions) return

    const attribute = geometry.getAttribute('position')
    if (!attribute) return

    const displayed = displayedRef.current
    const lerpAlpha = 1 - Math.exp(-delta * (6 + speed * 18))
    let changed = false

    for (let i = 0; i < displayed.length; i += 1) {
      const next = THREE.MathUtils.lerp(displayed[i], targetPositions[i], lerpAlpha)
      if (Math.abs(next - displayed[i]) > 1e-5) changed = true
      displayed[i] = next
      attribute.array[i] = next
    }

    if (!changed) return

    attribute.needsUpdate = true
    normalCooldownRef.current -= delta
    if (normalCooldownRef.current <= 0) {
      geometry.computeVertexNormals()
      geometry.computeBoundingSphere()
      normalCooldownRef.current = 1 / 24
    }
  })

  return (
    <mesh>
      <bufferGeometry ref={geometryRef} />
      <FaceMaterial result />
    </mesh>
  )
}

function SceneFrame({ children }) {
  return (
    <>
      <color attach="background" args={['#101827']} />
      <ambientLight intensity={0.9} />
      <hemisphereLight args={['#fff5e8', '#24324b', 1.3]} />
      <directionalLight position={[2.5, 3, 4]} intensity={2.9} />
      <directionalLight position={[-2.5, 1.5, 2]} intensity={1.2} color="#f1d5c4" />
      <group position={[0, -0.03, 0]} rotation={[0, 0, 0]}>
        {children}
      </group>
      <OrbitControls enablePan={false} minDistance={1.25} maxDistance={4} />
    </>
  )
}

export default function FaceCanvas({ model, targetPositions, animated = false, speed = 0.3 }) {
  if (!model) {
    return <div className="canvas-empty">请先上传 OBJ 模型</div>
  }

  return (
    <Canvas camera={{ position: [0, 0, 2.15], fov: 34, near: 0.01, far: 100 }} dpr={[1, 2]}>
      <SceneFrame>
        {animated ? (
          <AnimatedFaceMesh model={model} targetPositions={targetPositions} speed={speed} />
        ) : (
          <StaticFaceMesh model={model} />
        )}
      </SceneFrame>
    </Canvas>
  )
}
