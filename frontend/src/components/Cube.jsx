import React, { useRef, useState, useMemo, useEffect } from 'react'
import * as THREE from 'three'

// 루빅스 큐브의 6가지 색상 (원본과 동일)
const COLORS = {
  red: 0xC41E3A,
  green: 0x009E60,
  blue: 0x0051BA,
  orange: 0xFF5800,
  yellow: 0xFFD500,
  white: 0xFFFFFF,
  black: 0x000000
}

function Cube({ position, cubeId, onClick, onContextMenu, onDrag, faceColors }) {
  const meshRef = useRef()
  const cubeSize = 0.98 // 겹침을 줄이기 위해 크기 조정
  const [isDragging, setIsDragging] = useState(false)
  const [startPosition, setStartPosition] = useState(null)

  // 전달받은 색상을 사용하거나 기본 색상 생성
  const currentColors = useMemo(() => {
    if (faceColors) return faceColors
    
    // cubeId에서 원래 위치 추출
    const [origX, origY, origZ] = cubeId.split('_').map(Number)
    const colors = []
    
    // Right face (x = 1)
    colors.push(origX === 1 ? COLORS.red : COLORS.black)
    // Left face (x = -1)  
    colors.push(origX === -1 ? COLORS.orange : COLORS.black)
    // Top face (y = 1)
    colors.push(origY === 1 ? COLORS.white : COLORS.black)
    // Bottom face (y = -1)
    colors.push(origY === -1 ? COLORS.yellow : COLORS.black)
    // Front face (z = 1)
    colors.push(origZ === 1 ? COLORS.green : COLORS.black)
    // Back face (z = -1)
    colors.push(origZ === -1 ? COLORS.blue : COLORS.black)
    
    return colors
  }, [faceColors, cubeId])
  
  // 머티리얼을 한 번만 생성하고 재사용 - 더 안정적인 설정
  const materials = useMemo(() => {
    return Array.from({ length: 6 }, (_, index) => 
      new THREE.MeshPhongMaterial({ 
        color: 0x000000, // 초기값은 검은색으로 시작
        transparent: false,
        side: THREE.FrontSide,
        depthTest: true,
        depthWrite: true,
        polygonOffset: true,
        polygonOffsetFactor: 1,
        polygonOffsetUnits: index * 0.1, // 각 면마다 약간씩 다른 offset
        shininess: 30, // 약간의 광택으로 더 부드러운 외관
        specular: 0x222222, // 미묘한 반사광
        flatShading: false, // 부드러운 셰이딩
        vertexColors: false // 버텍스 컬러 비활성화
      })
    )
  }, [cubeId]) // cubeId에만 의존하도록 변경

  // 색상이 변곽될 때 부드럽게 업데이트
  useEffect(() => {
    if (materials && currentColors) {
      // requestAnimationFrame을 사용하여 다음 프레임에 업데이트
      const updateColors = () => {
        materials.forEach((material, index) => {
          const currentHex = material.color.getHex()
          const targetHex = currentColors[index]
          
          if (currentHex !== targetHex) {
            material.color.setHex(targetHex)
            material.needsUpdate = true
          }
        })
      }
      
      requestAnimationFrame(updateColors)
    }
  }, [currentColors, materials])

  const handlePointerDown = (event) => {
    event.stopPropagation()
    setIsDragging(false)
    setStartPosition([event.clientX, event.clientY])
  }

  const handlePointerMove = (event) => {
    if (!startPosition) return
    
    const currentPosition = [event.clientX, event.clientY]
    const dragDistance = Math.sqrt(
      Math.pow(currentPosition[0] - startPosition[0], 2) + 
      Math.pow(currentPosition[1] - startPosition[1], 2)
    )
    
    if (dragDistance > 10 && !isDragging) {
      setIsDragging(true)
    }
  }

  const handlePointerUp = (event) => {
    event.stopPropagation()
    
    if (!startPosition) return
    
    const endPosition = [event.clientX, event.clientY]
    const dragDistance = Math.sqrt(
      Math.pow(endPosition[0] - startPosition[0], 2) + 
      Math.pow(endPosition[1] - startPosition[1], 2)
    )
    
    if (dragDistance < 10) {
      // 클릭으로 간주
      if (onClick) {
        onClick(event, { position, id: cubeId, mesh: meshRef.current })
      }
    } else {
      // 드래그로 간주
      const dragVector = [
        endPosition[0] - startPosition[0],
        endPosition[1] - startPosition[1]
      ]
      if (onDrag) {
        onDrag(event, { position, id: cubeId, mesh: meshRef.current, dragVector })
      }
    }
    
    setStartPosition(null)
    setIsDragging(false)
  }

  const handleContextMenu = (event) => {
    event.preventDefault()
    event.stopPropagation()
    if (onContextMenu) {
      onContextMenu(event, { position, id: cubeId, mesh: meshRef.current })
    }
  }

  return (
    <mesh
      ref={meshRef}
      position={[position[0] * 1.05, position[1] * 1.05, position[2] * 1.05]}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onContextMenu={handleContextMenu}
      castShadow
      receiveShadow
      material={materials}
    >
      <boxGeometry args={[cubeSize, cubeSize, cubeSize]} />
    </mesh>
  )
}

export default Cube