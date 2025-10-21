import React, { useState, useRef, useCallback, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import CubePiece from './CubePiece'

const ROTATION_DURATION = 500 // 일반 회전 속도
const SHUFFLE_ROTATION_DURATION = 150 // 셔플 회전 속도 (빠르게)

// 색상 머티리얼 캐시
const materialCache = new Map()
const getMaterial = (color) => {
  if (!materialCache.has(color)) {
    materialCache.set(color, new THREE.MeshPhongMaterial({
      color: color,
      transparent: false,
      side: THREE.FrontSide,
      depthTest: true,
      depthWrite: true,
      shininess: 20,
      specular: 0x111111
    }))
  }
  return materialCache.get(color)
}

const RubiksCube = React.forwardRef(({ onDataUpdate, colorEditMode, selectedColor, selectedCell, onFaceColorChange, onCellSelect }, ref) => {
  // 초기 큐브 상태 생성 (한 번만 계산)
  const initialPieces = useMemo(() => {
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
  }, [])

  // 26개의 큐브 조각 생성
  const [pieces, setPieces] = useState(initialPieces)

  const [isRotating, setIsRotating] = useState(false)
  const [rotationQueue, setRotationQueue] = useState([])
  const pivotRef = useRef()
  const groupRef = useRef()
  
  const [rotationState, setRotationState] = useState({
    axis: null,
    direction: 1,
    startTime: 0,
    activeGroup: [],
    face: null,
    duration: ROTATION_DURATION // 회전 속도
  })

  // 회전 그룹 초기화
  React.useEffect(() => {
    if (pivotRef.current) {
      pivotRef.current.rotation.set(0, 0, 0)
    }
  }, [])

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
  const addRotation = useCallback((face, direction = 1, duration = ROTATION_DURATION) => {
    console.log(`🔧 [RubiksCube] addRotation 호출: face=${face}, direction=${direction}, duration=${duration}ms, isRotating=${isRotating}`)
    
    if (isRotating) {
      console.log(`⏳ [RubiksCube] 회전 중이므로 큐에 추가: face=${face}`)
      setRotationQueue(prev => [...prev, { face, direction, duration }])
      return
    }
    
    const activePieces = selectPiecesForRotation(face)
    const faceMap = {
      'R': 'x', 'L': 'x',
      'U': 'y', 'D': 'y', 
      'F': 'z', 'B': 'z'
    }
    
    console.log(`🎯 [RubiksCube] 회전 실행 시작: face=${face}, axis=${faceMap[face]}, direction=${direction}, pieces=${activePieces.length}개, duration=${duration}ms`)
    
    // 피벗 그룹 초기화
    if (pivotRef.current) {
      pivotRef.current.rotation.set(0, 0, 0)
    }
    
    setRotationState({
      axis: faceMap[face],
      direction,
      startTime: 0,
      activeGroup: activePieces.map(p => p.id),
      face,
      duration // 회전 속도 설정
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
      const duration = rotationState.duration || ROTATION_DURATION // 동적 duration 사용
      const progress = Math.min(elapsed / duration, 1)
      const easedProgress = easeInOutCubic(progress)
      
      const targetRotation = (Math.PI / 2) * rotationState.direction
      const currentRotation = targetRotation * easedProgress
      
      if (progress >= 1) {
        // 회전 완료 - 최종 위치 설정
        pivotRef.current.rotation[rotationState.axis] = targetRotation
        
        // 조각들의 위치와 색상 업데이트 (배치 처리)
        setPieces(prevPieces => {
          const updatedPieces = prevPieces.map(piece => {
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
          return updatedPieces
        })
        
        // 다음 프레임에서 피벗 초기화 (상태 업데이트 후)
        requestAnimationFrame(() => {
          if (pivotRef.current) {
            pivotRef.current.rotation.set(0, 0, 0)
          }
        })
        
        // 회전 상태 초기화
        console.log(`✅ [RubiksCube] 회전 완료! 큐에 남은 회전: ${rotationQueue.length}개`)
        
        // 다음 회전 처리 - isRotating을 false로 설정하기 전에 다음 회전 체크
        if (rotationQueue.length > 0) {
          const nextRotation = rotationQueue[0]
          setRotationQueue(prev => prev.slice(1))
          console.log(`➡️ [RubiksCube] 다음 회전 즉시 실행: face=${nextRotation.face}, direction=${nextRotation.direction}, duration=${nextRotation.duration}ms`)
          
          // 다음 회전을 바로 시작 (isRotating은 계속 true 유지)
          const nextActivePieces = selectPiecesForRotation(nextRotation.face)
          const faceMap = {
            'R': 'x', 'L': 'x',
            'U': 'y', 'D': 'y', 
            'F': 'z', 'B': 'z'
          }
          
          // 피벗 리셋
          if (pivotRef.current) {
            pivotRef.current.rotation.set(0, 0, 0)
          }
          
          setRotationState({
            axis: faceMap[nextRotation.face],
            direction: nextRotation.direction,
            startTime: 0,
            activeGroup: nextActivePieces.map(p => p.id),
            face: nextRotation.face,
            duration: nextRotation.duration
          })
          // isRotating은 true로 유지됨
        } else {
          console.log(`🏁 [RubiksCube] 모든 회전 완료!`)
          setRotationState({ axis: null, direction: 1, startTime: 0, activeGroup: [], face: null, duration: ROTATION_DURATION })
          setIsRotating(false)
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
        'r': () => addRotation('R', isShift ? 1 : -1),
        'l': () => addRotation('L', isShift ? -1 : 1),
        'u': () => addRotation('U', isShift ? 1 : -1),
        'd': () => addRotation('D', isShift ? -1 : 1),
        'f': () => addRotation('F', isShift ? 1 : -1),
        'b': () => addRotation('B', isShift ? -1 : 1)
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
    
    const { position, faceIndex } = pieceData
    const [x, y, z] = position
    
    // 색상 편집 모드인 경우 - 항상 셀 선택만 함 (색상 적용은 ColorPicker에서)
    if (colorEditMode && onCellSelect) {
      const pieceId = `${x}_${y}_${z}`
      onCellSelect(pieceId, faceIndex || 0)
      return
    }
    
    // 마우스 버튼 확인: 0 = 좌클릭(정방향), 2 = 우클릭(역방향)
    const direction = event.button === 2 ? -1 : 1
    
    // 일반 모드: 클릭된 조각의 위치를 기준으로 회전할 면 결정
    if (Math.abs(x) === 1) {
      addRotation(x === 1 ? 'R' : 'L', direction)
    } else if (Math.abs(y) === 1) {
      addRotation(y === 1 ? 'U' : 'D', direction)
    } else if (Math.abs(z) === 1) {
      addRotation(z === 1 ? 'F' : 'B', direction)
    }
  }, [isRotating, addRotation, colorEditMode, onFaceColorChange, onCellSelect])

  // 렌더링할 조각들 분리
  const { rotatingPieces, staticPieces } = useMemo(() => {
    const rotating = pieces.filter(piece => rotationState.activeGroup.includes(piece.id))
    const stationary = pieces.filter(piece => !rotationState.activeGroup.includes(piece.id))
    return { rotatingPieces: rotating, staticPieces: stationary }
  }, [pieces, rotationState.activeGroup])

  // 데이터 업데이트 전달
  React.useEffect(() => {
    if (onDataUpdate && pieces.length > 0) {
      onDataUpdate(pieces)
    }
  }, [pieces, onDataUpdate])

  // 면 색상 업데이트 함수
  const updatePieceFaceColor = useCallback((pieceId, faceIndex, color) => {
    setPieces(prevPieces => 
      prevPieces.map(piece => {
        if (piece.id === pieceId) {
          const newFaceColors = [...piece.faceColors]
          newFaceColors[faceIndex] = color
          return { ...piece, faceColors: newFaceColors }
        }
        return piece
      })
    )
  }, [])

  // Shuffle 함수 추가
  const shuffle = useCallback(() => {
    console.log('🎲 Shuffle 시작')
    const moves = ['R', 'L', 'U', 'D', 'F', 'B']
    const directions = [1, -1]
    const shuffleCount = 20 // 20번 랜덤 회전
    
    for (let i = 0; i < shuffleCount; i++) {
      const randomFace = moves[Math.floor(Math.random() * moves.length)]
      const randomDirection = directions[Math.floor(Math.random() * directions.length)]
      addRotation(randomFace, randomDirection, SHUFFLE_ROTATION_DURATION) // 빠른 속도로!
    }
    console.log(`🎲 ${shuffleCount}번 랜덤 회전 추가됨 (빠른 속도: ${SHUFFLE_ROTATION_DURATION}ms)`)
  }, [addRotation])

  // Reset 함수 추가
  const reset = useCallback(() => {
    console.log('🔄 Reset 시작')
    setRotationQueue([])
    setPieces(initialPieces)
    console.log('🔄 Reset 완료')
  }, [initialPieces])

  // Undo 함수 (임시 - 나중에 구현)
  const undo = useCallback(() => {
    console.log('↩️ Undo (미구현)')
  }, [])

  // ref 설정
  React.useImperativeHandle(ref, () => ({
    getPieces: () => pieces,
    setPieces: (newPieces) => {
      console.log('setPieces called with:', newPieces)
      
      // 회전 중이면 모든 회전을 완료할 때까지 기다림
      if (isRotating || rotationQueue.length > 0) {
        console.log('Rotation in progress, waiting...')
        const waitForRotationComplete = () => {
          if (!isRotating && rotationQueue.length === 0) {
            console.log('Rotation completed, updating pieces')
            setPieces(newPieces)
          } else {
            setTimeout(waitForRotationComplete, 100)
          }
        }
        waitForRotationComplete()
      } else {
        setPieces(newPieces)
      }
    },
    addRotation: addRotation,
    updatePieceFaceColor: updatePieceFaceColor,
    shuffle: shuffle,
    reset: reset,
    undo: undo,
    get isMoving() { return isRotating || rotationQueue.length > 0 }
  }))

  return (
    <group ref={groupRef}>
      {/* 정적 조각들 */}
      {staticPieces.map(piece => (
        <CubePiece
          key={`static-${piece.id}`}
          position={piece.position}
          faceColors={piece.faceColors}
          onClick={handlePieceClick}
          selectedCell={selectedCell}
          isStatic={true}
        />
      ))}
      
      {/* 회전하는 조각들 - 피벗 그룹 */}
      <group 
        ref={pivotRef}
        name={`pivot-${rotationState.face || 'none'}`}
      >
        {rotatingPieces.map(piece => (
          <CubePiece
            key={`rotating-${piece.id}`}
            position={piece.position}
            faceColors={piece.faceColors}
            onClick={handlePieceClick}
            selectedCell={selectedCell}
            isStatic={false}
          />
        ))}
      </group>
    </group>
  )
})

RubiksCube.displayName = 'RubiksCube'

export default RubiksCube