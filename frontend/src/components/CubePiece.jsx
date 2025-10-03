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
  selectedCell,
  isStatic = true
}) {
  const meshRef = useRef()
  const cubeSize = 0.95

  // 이 조각이 선택된 셀인지 확인
  const isSelected = selectedCell && 
    selectedCell.x === position[0] && 
    selectedCell.y === position[1] && 
    selectedCell.z === position[2]

  // 캐시된 머티리얼 사용
  const materials = useMemo(() => {
    return faceColors.map(color => getMaterial(color))
  }, [faceColors])

  const handlePointerDown = (event) => {
    event.stopPropagation()
    if (onClick) {
      // 클릭된 면 감지: 교차점의 법선 벡터로 면 결정
      let faceIndex = 0
      if (event.face) {
        const normal = event.face.normal
        // Three.js BoxGeometry의 면 순서: [+X, -X, +Y, -Y, +Z, -Z]
        if (Math.abs(normal.x) > 0.5) {
          faceIndex = normal.x > 0 ? 0 : 1  // Right, Left
        } else if (Math.abs(normal.y) > 0.5) {
          faceIndex = normal.y > 0 ? 2 : 3  // Top, Bottom  
        } else if (Math.abs(normal.z) > 0.5) {
          faceIndex = normal.z > 0 ? 4 : 5  // Front, Back
        }
      }
      onClick(event, { position, faceIndex })
    }
  }

  // 우클릭 메뉴 방지
  const handleContextMenu = (event) => {
    event.stopPropagation()
    event.nativeEvent.preventDefault()
  }

  return (
    <group>
      <mesh
        ref={meshRef}
        position={[position[0] * 1.05, position[1] * 1.05, position[2] * 1.05]}
        scale={isSelected ? 1.1 : 1}
        onPointerDown={handlePointerDown}
        onContextMenu={handleContextMenu}
        castShadow
        receiveShadow
        material={materials}
      >
        <boxGeometry args={[cubeSize, cubeSize, cubeSize]} />
      </mesh>
      
      {/* 선택된 조각에 외곽선 효과 */}
      {isSelected && (
        <mesh
          position={[position[0] * 1.05, position[1] * 1.05, position[2] * 1.05]}
          scale={1.15}
        >
          <boxGeometry args={[cubeSize, cubeSize, cubeSize]} />
          <meshBasicMaterial 
            color="#FFD700" 
            wireframe={true} 
            wireframeLinewidth={3}
          />
        </mesh>
      )}
    </group>
  )
}

export default CubePiece