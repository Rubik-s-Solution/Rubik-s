import React, { useState, useRef, useCallback, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import CubePiece from './CubePiece'

const ROTATION_DURATION = 500

function RubiksCubeStable() {
  // 26개의 큐브 조각 생성
  const [pieces, setPieces] = useState(() => {
    const COLORS = {
      red: 0xC41E3A,
      green: 0x009E60,
      blue: 0x0051BA,
      orange: 0xFF5800,
      yellow: 0xFFD500,
      white: 0xFFFFFF,
      black: 0x212121
    }
    
    const pieceArray = []
    
    for (let x = -1; x <= 1; x++) {
      for (let y = -1; y <= 1; y++) {
        for (let z = -1; z <= 1; z++) {
          // 중앙 조각 제외
          if (x === 0 && y === 0 && z === 0) continue
          
          // 각 면의 초기 색상 배열 [Right, Left, Top, Bottom, Front, Back]
          const faceColors = [
            x === 1 ? COLORS.red : COLORS.black,      // Right (+X)
            x === -1 ? COLORS.orange : COLORS.black,  // Left (-X)
            y === 1 ? COLORS.white : COLORS.black,    // Top (+Y)
            y === -1 ? COLORS.yellow : COLORS.black,  // Bottom (-Y)
            z === 1 ? COLORS.green : COLORS.black,    // Front (+Z)
            z === -1 ? COLORS.blue : COLORS.black     // Back (-Z)
          ]
          
          pieceArray.push({
            id: `${x}_${y}_${z}`,
            position: [x, y, z],
            faceColors: faceColors
          })
        }
      }
    }
    
    return pieceArray
  })

  const [isRotating, setIsRotating] = useState(false)
  const [rotationQueue, setRotationQueue] = useState([])
  const pivotRef = useRef()
  const groupRef = useRef()
  
  const [rotationState, setRotationState] = useState({
    axis: null,
    direction: 1,
    startTime: 0,
    activeGroup: []
  })

  // 회전할 조각들 선택
  const selectPiecesForRotation = useCallback((face) => {
    const faceMap = {
      'R': { axis: 'x', value: 1 },
      'L': { axis: 'x', value: -1 },
      'U': { axis: 'y', value: 1 },
      'D': { axis: 'y', value: -1 },
      'F': { axis: 'z', value: 1 },
      'B': { axis: 'z', value: -1 }
    }
    
    const { axis, value } = faceMap[face]
    const axisIndex = ['x', 'y', 'z'].indexOf(axis)
    
    return pieces.filter(piece => piece.position[axisIndex] === value)
  }, [pieces])

  // 회전 추가
  const addRotation = useCallback((face, direction = 1) => {
    if (isRotating) {
      setRotationQueue(prev => [...prev, { face, direction }])
      return
    }
    
    const activePieces = selectPiecesForRotation(face)
    const faceMap = {
      'R': 'x', 'L': 'x',
      'U': 'y', 'D': 'y', 
      'F': 'z', 'B': 'z'
    }
    
    setRotationState({
      axis: faceMap[face],
      direction,
      startTime: 0,
      activeGroup: activePieces.map(p => p.id)
    })
    
    setIsRotating(true)
  }, [isRotating, selectPiecesForRotation])

  // easing 함수
  const easeInOutCubic = (t) => {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
  }

  // 위치 회전 함수
  const rotatePosition = (position, axis, direction) => {
    const [x, y, z] = position
    const angle = direction * Math.PI / 2
    
    switch (axis) {
      case 'x':
        return [
          x,
          Math.round(y * Math.cos(angle) - z * Math.sin(angle)),
          Math.round(y * Math.sin(angle) + z * Math.cos(angle))
        ]
      case 'y':
        return [
          Math.round(x * Math.cos(angle) + z * Math.sin(angle)),
          y,
          Math.round(-x * Math.sin(angle) + z * Math.cos(angle))
        ]
      case 'z':
        return [
          Math.round(x * Math.cos(angle) - y * Math.sin(angle)),
          Math.round(x * Math.sin(angle) + y * Math.cos(angle)),
          z
        ]
      default:
        return position
    }
  }

  // 면 색상 회전 함수
  const rotateFaceColors = (colors, axis, direction) => {
    const newColors = [...colors]
    
    if (axis === 'x') {
      // X축 회전: Top, Front, Bottom, Back 순환
      if (direction === 1) { // 시계방향
        const temp = newColors[2] // Top
        newColors[2] = newColors[5] // Top = Back
        newColors[5] = newColors[3] // Back = Bottom  
        newColors[3] = newColors[4] // Bottom = Front
        newColors[4] = temp // Front = Top
      } else { // 반시계방향
        const temp = newColors[2] // Top
        newColors[2] = newColors[4] // Top = Front
        newColors[4] = newColors[3] // Front = Bottom
        newColors[3] = newColors[5] // Bottom = Back
        newColors[5] = temp // Back = Top
      }
    } else if (axis === 'y') {
      // Y축 회전: Right, Front, Left, Back 순환
      if (direction === 1) { // 시계방향
        const temp = newColors[0] // Right
        newColors[0] = newColors[4] // Right = Front
        newColors[4] = newColors[1] // Front = Left
        newColors[1] = newColors[5] // Left = Back
        newColors[5] = temp // Back = Right
      } else { // 반시계방향
        const temp = newColors[0] // Right
        newColors[0] = newColors[5] // Right = Back
        newColors[5] = newColors[1] // Back = Left
        newColors[1] = newColors[4] // Left = Front
        newColors[4] = temp // Front = Right
      }
    } else if (axis === 'z') {
      // Z축 회전: Right, Top, Left, Bottom 순환
      if (direction === 1) { // 시계방향
        const temp = newColors[0] // Right
        newColors[0] = newColors[3] // Right = Bottom
        newColors[3] = newColors[1] // Bottom = Left
        newColors[1] = newColors[2] // Left = Top
        newColors[2] = temp // Top = Right
      } else { // 반시계방향
        const temp = newColors[0] // Right
        newColors[0] = newColors[2] // Right = Top
        newColors[2] = newColors[1] // Top = Left
        newColors[1] = newColors[3] // Left = Bottom
        newColors[3] = temp // Bottom = Right
      }
    }
    
    return newColors
  }

  // 회전 애니메이션
  useFrame((state) => {
    if (isRotating && rotationState.axis && pivotRef.current) {
      const currentTime = state.clock.elapsedTime * 1000
      
      if (rotationState.startTime === 0) {
        setRotationState(prev => ({ ...prev, startTime: currentTime }))
        return
      }
      
      const elapsed = currentTime - rotationState.startTime
      const progress = Math.min(elapsed / ROTATION_DURATION, 1)
      const easedProgress = easeInOutCubic(progress)
      
      const targetRotation = (Math.PI / 2) * rotationState.direction
      const currentRotation = targetRotation * easedProgress
      
      if (progress >= 1) {
        // 회전 완료
        pivotRef.current.rotation[rotationState.axis] = targetRotation
        
        // pivot 초기화
        pivotRef.current.rotation.set(0, 0, 0)
        
        // 조각들의 위치와 색상 업데이트
        setPieces(prevPieces => 
          prevPieces.map(piece => {
            if (rotationState.activeGroup.includes(piece.id)) {
              const newPosition = rotatePosition(piece.position, rotationState.axis, rotationState.direction)
              const newFaceColors = rotateFaceColors(piece.faceColors, rotationState.axis, rotationState.direction)
              return {
                ...piece,
                position: newPosition,
                faceColors: newFaceColors
              }
            }
            return piece
          })
        )
        
        // 회전 상태 초기화
        setRotationState({ axis: null, direction: 1, startTime: 0, activeGroup: [] })
        setIsRotating(false)
        
        // 다음 회전 처리
        if (rotationQueue.length > 0) {
          const nextRotation = rotationQueue[0]
          setRotationQueue(prev => prev.slice(1))
          setTimeout(() => {
            addRotation(nextRotation.face, nextRotation.direction)
          }, 50)
        }
      } else {
        // 회전 진행
        pivotRef.current.rotation[rotationState.axis] = currentRotation
      }
    }
  })

  // 키보드 조작
  React.useEffect(() => {
    const handleKeyDown = (event) => {
      if (isRotating) return
      
      const key = event.key.toLowerCase()
      const isShift = event.shiftKey
      
      const keyMap = {
        'r': () => addRotation('R', isShift ? -1 : 1),
        'l': () => addRotation('L', isShift ? 1 : -1),
        'u': () => addRotation('U', isShift ? -1 : 1),
        'd': () => addRotation('D', isShift ? 1 : -1),
        'f': () => addRotation('F', isShift ? -1 : 1),
        'b': () => addRotation('B', isShift ? 1 : -1)
      }
      
      if (keyMap[key]) {
        event.preventDefault()
        keyMap[key]()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isRotating, addRotation])

  // 클릭 핸들러
  const handlePieceClick = useCallback((event, pieceData) => {
    if (isRotating) return
    
    const { position } = pieceData
    const [x, y, z] = position
    
    // 클릭된 조각의 위치를 기준으로 회전할 면 결정
    if (Math.abs(x) === 1) {
      addRotation(x === 1 ? 'R' : 'L')
    } else if (Math.abs(y) === 1) {
      addRotation(y === 1 ? 'U' : 'D')
    } else if (Math.abs(z) === 1) {
      addRotation(z === 1 ? 'F' : 'B')
    }
  }, [isRotating, addRotation])

  // 렌더링할 조각들 분리
  const { rotatingPieces, staticPieces } = useMemo(() => {
    const rotating = pieces.filter(piece => rotationState.activeGroup.includes(piece.id))
    const stationary = pieces.filter(piece => !rotationState.activeGroup.includes(piece.id))
    return { rotatingPieces: rotating, staticPieces: stationary }
  }, [pieces, rotationState.activeGroup])

  return (
    <group ref={groupRef}>
      {/* 정적 조각들 */}
      {staticPieces.map(piece => (
        <CubePiece
          key={`static-${piece.id}`}
          position={piece.position}
          faceColors={piece.faceColors}
          onClick={handlePieceClick}
        />
      ))}
      
      {/* 회전하는 조각들 */}
      <group ref={pivotRef}>
        {rotatingPieces.map(piece => (
          <CubePiece
            key={`rotating-${piece.id}`}
            position={piece.position}
            faceColors={piece.faceColors}
            onClick={handlePieceClick}
          />
        ))}
      </group>
    </group>
  )
}

export default RubiksCubeStable