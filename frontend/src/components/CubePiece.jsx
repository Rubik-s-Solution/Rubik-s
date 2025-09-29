import React, { useRef, useMemo } from 'react'
import * as THREE from 'three'

// 루빅스 큐브의 6가지 색상
const COLORS = {
  red: 0xC41E3A,
  green: 0x009E60,
  blue: 0x0051BA,
  orange: 0xFF5800,
  yellow: 0xFFD500,
  white: 0xFFFFFF,
  black: 0x212121
}

// 머티리얼 캐시
const materialCache = new Map()
const getMaterial = (color) => {
  const key = `material_${color}`
  if (!materialCache.has(key)) {
    materialCache.set(key, new THREE.MeshPhongMaterial({
      color: color,
      transparent: false,
      side: THREE.FrontSide,
      depthTest: true,
      depthWrite: true,
      shininess: 20,
      specular: 0x111111
    }))
  }
  return materialCache.get(key)
}

function CubePiece({ 
  position, 
  faceColors, // 각 면의 현재 색상 배열
  onClick,
  isStatic = true
}) {
  const meshRef = useRef()
  const cubeSize = 0.95

  // 캐시된 머티리얼 사용
  const materials = useMemo(() => {
    return faceColors.map(color => getMaterial(color))
  }, [faceColors])

  const handlePointerDown = (event) => {
    event.stopPropagation()
    if (onClick) {
      onClick(event, { position })
    }
  }

  return (
    <mesh
      ref={meshRef}
      position={[position[0] * 1.05, position[1] * 1.05, position[2] * 1.05]}
      onPointerDown={handlePointerDown}
      castShadow
      receiveShadow
      material={materials}
    >
      <boxGeometry args={[cubeSize, cubeSize, cubeSize]} />
    </mesh>
  )
}

export default CubePiece