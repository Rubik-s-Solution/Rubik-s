import React, { useState, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import RubiksCube from './components/RubiksCube'
import Controls from './components/Controls'
import CubeNet from './components/CubeNet'
import ViewModeSelector from './components/ViewModeSelector'
import Resizer from './components/Resizer'
import ColorPicker, { COLORS } from './components/ColorPicker'
import ImageUpload from './components/ImageUpload'
import SolutionViewer from './components/SolutionViewer'
import { loadAndConvertCubeData } from './utils/cubeColorLoader'
import { generateSolution, createSession, clearSessionId } from './utils/imageApi'
import { parseMove } from './utils/cubeSolver'
import './App.css'

function App() {
  const [viewMode, setViewMode] = useState('3D')
  const [cubeData, setCubeData] = useState([])
  const [sceneWidth, setSceneWidth] = useState(60) // 3D 씬의 너비 (%)
  const [colorEditMode, setColorEditMode] = useState(false)
  const [selectedColor, setSelectedColor] = useState('red')
  const [selectedCell, setSelectedCell] = useState(null) // 선택된 칸 {pieceId, faceIndex}
  const [isLoadingJson, setIsLoadingJson] = useState(false)
  const [jsonLoadError, setJsonLoadError] = useState(null)
  const [jsonLoadSuccess, setJsonLoadSuccess] = useState(false)
  const [showImageUpload, setShowImageUpload] = useState(false)
  const [uploadedImages, setUploadedImages] = useState({}) // 면별 업로드된 이미지
  const [solution, setSolution] = useState(null) // 생성된 해법
  const [showSolution, setShowSolution] = useState(false) // 해법 뷰어 표시
  const [isGeneratingSolution, setIsGeneratingSolution] = useState(false) // 해법 생성 중
  const [solutionError, setSolutionError] = useState(null) // 해법 생성 오류
  const [initialCubeState, setInitialCubeState] = useState(null) // 해법 생성 시점의 큐브 상태
  const cubeRef = useRef()
  const fileInputRef = useRef()

  // cubeRef를 window.rubiksCube에 연결
  React.useEffect(() => {
    if (cubeRef.current) {
      window.rubiksCube = cubeRef.current
      console.log('✅ window.rubiksCube 연결됨')
    }
    return () => {
      window.rubiksCube = null
    }
  }, [])

  // 큐브가 풀렸는지 확인하는 함수
  const checkCubeSolved = (pieces) => {
    if (!pieces || pieces.length !== 26) return false
    
    // 각 면이 단일 색상인지 확인
    const faces = {
      right: pieces.filter(p => p.position[0] === 1),   // x = 1
      left: pieces.filter(p => p.position[0] === -1),   // x = -1
      top: pieces.filter(p => p.position[1] === 1),     // y = 1
      bottom: pieces.filter(p => p.position[1] === -1), // y = -1
      front: pieces.filter(p => p.position[2] === 1),   // z = 1
      back: pieces.filter(p => p.position[2] === -1)    // z = -1
    }
    
    let solved = true
    const faceNames = ['right', 'left', 'top', 'bottom', 'front', 'back']
    const faceIndexMap = [0, 1, 2, 3, 4, 5] // R, L, U, D, F, B
    
    faceNames.forEach((faceName, idx) => {
      const facePieces = faces[faceName]
      if (facePieces.length > 0) {
        const firstColor = facePieces[0].faceColors[faceIndexMap[idx]]
        const allSameColor = facePieces.every(p => p.faceColors[faceIndexMap[idx]] === firstColor)
        if (!allSameColor) {
          console.log(`❌ ${faceName} 면이 풀리지 않음`)
          solved = false
        }
      }
    })
    
    return solved
  }

  // 큐브 데이터 업데이트 핸들러
  const handleCubeDataUpdate = (pieces) => {
    setCubeData(pieces)
  }

  // 리사이저 핸들러
  const handleResize = (newWidth) => {
    setSceneWidth(newWidth)
  }

  // 색상 편집 모드 토글
  const handleColorEditToggle = () => {
    setColorEditMode(!colorEditMode)
    setSelectedCell(null) // 모드 변경 시 선택된 칸 초기화
  }

  // 색상 선택 (2단계: 색상 적용)
  const handleColorSelect = (color) => {
    console.log('handleColorSelect called:', { color, selectedCell })
    if (selectedCell) {
      // 선택된 칸에 색상 적용
      const colorHex = COLORS[color].hex
      const colorNumber = parseInt(colorHex.replace('#', ''), 16)
      
      if (cubeRef.current && cubeRef.current.updatePieceFaceColor) {
        // pieceId가 있으면 사용, 없으면 x,y,z 좌표로 생성
        const pieceId = selectedCell.pieceId || `${selectedCell.x}_${selectedCell.y}_${selectedCell.z}`
        console.log('Updating piece color:', { pieceId, faceIndex: selectedCell.faceIndex, colorNumber })
        cubeRef.current.updatePieceFaceColor(pieceId, selectedCell.faceIndex, colorNumber)
      } else {
        console.log('cubeRef.current.updatePieceFaceColor not available')
      }
      
      // 색상 적용 후 선택 해제
      setSelectedCell(null)
    }
    setSelectedColor(color)
  }

  // 큐브 면 선택 (1단계: 칸 선택)
  const handleCellSelect = (pieceId, faceIndex) => {
    if (!colorEditMode) return
    
    // pieceId에서 x, y, z 좌표 추출 (예: "1_0_-1" -> x=1, y=0, z=-1)
    const [x, y, z] = pieceId.split('_').map(Number)
    
    setSelectedCell({ 
      pieceId, 
      faceIndex,
      x, 
      y, 
      z 
    })
  }

  // 전개도에서 칸 선택
  const handleNetCellSelect = (face, row, col) => {
    if (!colorEditMode) return
    
    // 전개도 좌표를 3D 좌표로 변환
    const coords = convertNetTo3DCoords(face, row, col)
    
    // 면별 faceIndex 매핑 (0:R, 1:L, 2:U, 3:D, 4:F, 5:B)
    const faceIndexMap = { 'R': 0, 'L': 1, 'U': 2, 'D': 3, 'F': 4, 'B': 5 }
    const faceIndex = faceIndexMap[face] || 0
    
    // 격자 인덱스 (해당 면 내에서의 위치 0-8)
    const gridIndex = row * 3 + col
    
    setSelectedCell({
      face,
      faceIndex,
      gridIndex, // 전개도에서 하이라이트에 사용
      x: coords.x,
      y: coords.y, 
      z: coords.z,
      faceType: coords.faceType
    })
  }

  // 전개도 좌표를 3D 좌표로 변환하는 함수
  const convertNetTo3DCoords = (face, row, col) => {
    // 각 면의 격자 좌표를 3D 위치로 변환
    switch (face) {
      case 'U': // Top
        return {
          x: col - 1,  // 0,1,2 -> -1,0,1
          y: 1,
          z: row - 1,  // 0,1,2 -> -1,0,1 (수정: U7이 z=-1에 위치하도록)
          faceType: 'top'
        }
      case 'D': // Bottom
        return {
          x: col - 1,  // 0,1,2 -> -1,0,1
          y: -1,
          z: 1 - row, // 0,1,2 -> 1,0,-1 (수정: D1이 z=1에 위치하도록)
          faceType: 'bottom'
        }
      case 'F': // Front
        return {
          x: col - 1,  // 0,1,2 -> -1,0,1
          y: 1 - row,  // 0,1,2 -> 1,0,-1
          z: 1,
          faceType: 'front'
        }
      case 'B': // Back
        return {
          x: 1 - col,  // 0,1,2 -> 1,0,-1
          y: 1 - row,  // 0,1,2 -> 1,0,-1
          z: -1,
          faceType: 'back'
        }
      case 'L': // Left
        return {
          x: -1,
          y: 1 - row,  // 0,1,2 -> 1,0,-1
          z: col - 1,  // 0,1,2 -> -1,0,1
          faceType: 'left'
        }
      case 'R': // Right
        return {
          x: 1,
          y: 1 - row,  // 0,1,2 -> 1,0,-1
          z: 1 - col,  // 0,1,2 -> 1,0,-1
          faceType: 'right'
        }
      default: 
        return { x: 0, y: 0, z: 0, faceType: 'unknown' }
    }
  }

  // JSON 파일에서 큐브 색상 데이터 로드
  const handleLoadCubeColorsFromJson = async () => {
    setIsLoadingJson(true)
    setJsonLoadError(null)
    setJsonLoadSuccess(false)
    
    try {
      console.log('큐브 색상 JSON 로드 시작...')
      const pieces = await loadAndConvertCubeData('/cube_colors.json')
      console.log('변환된 큐브 조각:', pieces)
      
      if (cubeRef.current && cubeRef.current.setPieces) {
        cubeRef.current.setPieces(pieces)
        setCubeData(pieces)
        setJsonLoadSuccess(true)
        console.log('큐브 색상 데이터가 성공적으로 적용되었습니다.')
        
        // 성공 메시지를 3초 후에 숨김
        setTimeout(() => {
          setJsonLoadSuccess(false)
        }, 3000)
      } else {
        throw new Error('cubeRef.current.setPieces 메소드를 찾을 수 없습니다.')
      }
    } catch (error) {
      console.error('큐브 색상 JSON 로드 실패:', error)
      setJsonLoadError(error.message)
      
      // 에러 메시지를 5초 후에 숨김
      setTimeout(() => {
        setJsonLoadError(null)
      }, 5000)
    } finally {
      setIsLoadingJson(false)
    }
  }

  // 파일 업로드로 JSON 로드
  const handleFileUpload = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.json')) {
      setJsonLoadError('JSON 파일만 업로드 가능합니다.')
      setTimeout(() => setJsonLoadError(null), 3000)
      return
    }

    setIsLoadingJson(true)
    setJsonLoadError(null)
    setJsonLoadSuccess(false)

    try {
      const text = await file.text()
      const cubeData = JSON.parse(text)
      
      // cubeColorLoader의 convertJsonToCubePieces 함수 사용
      const { convertJsonToCubePieces } = await import('./utils/cubeColorLoader')
      const pieces = convertJsonToCubePieces(cubeData)
      
      if (cubeRef.current && cubeRef.current.setPieces) {
        cubeRef.current.setPieces(pieces)
        setCubeData(pieces)
        setJsonLoadSuccess(true)
        console.log('업로드된 큐브 색상 데이터가 성공적으로 적용되었습니다.')
        
        setTimeout(() => setJsonLoadSuccess(false), 3000)
      } else {
        throw new Error('cubeRef.current.setPieces 메소드를 찾을 수 없습니다.')
      }
    } catch (error) {
      console.error('파일 업로드 실패:', error)
      setJsonLoadError(`파일 처리 실패: ${error.message}`)
      setTimeout(() => setJsonLoadError(null), 5000)
    } finally {
      setIsLoadingJson(false)
      // 파일 입력 초기화
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // 면 색상 변경 (구버전 호환)
  const handleFaceColorChange = (pieceId, faceIndex) => {
    if (!selectedColor) return
    
    const colorHex = COLORS[selectedColor].hex
    const colorNumber = parseInt(colorHex.replace('#', ''), 16)
    
    if (cubeRef.current.updatePieceFaceColor) {
      cubeRef.current.updatePieceFaceColor(pieceId, faceIndex, colorNumber)
    }
  }

  // 이미지 업로드 모드 토글
  const handleImageUploadToggle = async () => {
    if (!showImageUpload) {
      // 이미지 업로드 모달을 열 때 새 세션 생성
      try {
        console.log('🔄 이미지 업로드 모달 열기: 새 세션 생성 중...')
        await createSession()
        console.log('✅ 새 세션 생성 완료')
      } catch (error) {
        console.error('세션 생성 실패:', error)
        // 세션 생성 실패해도 모달은 열리도록 함
      }
    }
    setShowImageUpload(!showImageUpload)
  }

  // 이미지 업로드 핸들러
  const handleImageUpload = (face, imageData) => {
    setUploadedImages(prev => {
      const newImages = { ...prev }
      if (imageData) {
        // 기존 이미지 URL이 있다면 해제
        if (newImages[face]?.url) {
          URL.revokeObjectURL(newImages[face].url)
        }
        newImages[face] = imageData
      } else {
        // 이미지 제거
        if (newImages[face]?.url) {
          URL.revokeObjectURL(newImages[face].url)
        }
        delete newImages[face]
      }
      return newImages
    })
  }

  // 색상 분석 완료 핸들러
  const handleAnalysisComplete = (cubeColors, analysisResults) => {
    console.log('색상 분석 완료:', cubeColors)
    
    // analysisResults에 해법이 있으면 저장
    if (analysisResults && analysisResults.solution && analysisResults.solution.status === 'success') {
      console.log('✅ 기존 해법 발견:', analysisResults.solution.solution_string)
      setSolution(analysisResults.solution.solution_string)
    }
    
    // test.py의 색상 레이블을 THREE.js 색상 번호로 변환
    const colorMap = {
      'w': 0xFFFFFF,  // white
      'y': 0xFFD500,  // yellow
      'o': 0xFF5800,  // orange
      'r': 0xC41E3A,  // red
      'g': 0x009E60,  // green
      'b': 0x0051BA,  // blue
      '?': 0x212121   // black (미인식)
    }
    
    // 면 매핑: 백엔드(U,D,F,B,L,R) → Three.js(R,L,U,D,F,B) 인덱스
    const faceIndexMap = {
      'R': 0,
      'L': 1,
      'U': 2,
      'D': 3,
      'F': 4,
      'B': 5
    }
    
    // 각 큐브 조각의 위치와 면 색상 업데이트
    if (cubeRef.current && cubeRef.current.setPieces) {
      // 기존 큐브 데이터를 복사하여 수정
      const updatedPieces = []
      
      for (let x = -1; x <= 1; x++) {
        for (let y = -1; y <= 1; y++) {
          for (let z = -1; z <= 1; z++) {
            if (x === 0 && y === 0 && z === 0) continue // 중앙 제외
            
            const faceColors = [
              0x212121, // Right (+X)
              0x212121, // Left (-X)
              0x212121, // Top (+Y)
              0x212121, // Bottom (-Y)
              0x212121, // Front (+Z)
              0x212121  // Back (-Z)
            ]
            
            // 각 면의 색상 설정
            for (const [faceName, grid] of Object.entries(cubeColors)) {
              const faceIndex = faceIndexMap[faceName]
              if (faceIndex === undefined) continue
              
              // 해당 조각이 이 면에 속하는지 확인
              let belongsToFace = false
              let row = 0, col = 0
              
              if (faceName === 'R' && x === 1) {
                belongsToFace = true
                row = 1 - y  // y: 1,0,-1 → row: 0,1,2
                col = 1 - z  // z: 1,0,-1 → col: 0,1,2
              } else if (faceName === 'L' && x === -1) {
                belongsToFace = true
                row = 1 - y
                col = z + 1
              } else if (faceName === 'U' && y === 1) {
                belongsToFace = true
                row = z + 1   // z: -1,0,1 → row: 0,1,2
                col = x + 1   // x: -1,0,1 → col: 0,1,2
              } else if (faceName === 'D' && y === -1) {
                belongsToFace = true
                row = 1 - z  // z: 1,0,-1 → row: 0,1,2
                col = x + 1  // x: -1,0,1 → col: 0,1,2
              } else if (faceName === 'F' && z === 1) {
                belongsToFace = true
                row = 1 - y
                col = x + 1
              } else if (faceName === 'B' && z === -1) {
                belongsToFace = true
                row = 1 - y
                col = 1 - x
              }
              
              if (belongsToFace && row >= 0 && row < 3 && col >= 0 && col < 3) {
                const colorLabel = grid[row][col]
                faceColors[faceIndex] = colorMap[colorLabel] || 0x212121
              }
            }
            
            updatedPieces.push({
              id: `${x}_${y}_${z}`,
              position: [x, y, z],
              faceColors: faceColors
            })
          }
        }
      }
      
      // 큐브에 새로운 색상 데이터 적용
      cubeRef.current.setPieces(updatedPieces)
      setCubeData(updatedPieces)
      
      // 큐브 상태 저장 (해법 적용 전 상태)
      setInitialCubeState(JSON.parse(JSON.stringify(updatedPieces)))
      
      console.log('큐브에 색상이 성공적으로 적용되었습니다!')
    }
  }

  // 해법 생성
  const handleGenerateSolution = async () => {
    setIsGeneratingSolution(true)
    setSolutionError(null)
    
    try {
      console.log('해법 생성 중...')
      
      // 세션이 없으면 생성 (수동 조작 모드용)
      let sessionId = localStorage.getItem('rubiks_session_id')
      if (!sessionId) {
        console.log('🆕 세션이 없습니다. 수동 조작 모드용 세션 생성 중...')
        await createSession()
        console.log('✅ 수동 조작 모드용 세션 생성 완료')
      }
      
      // 현재 3D 큐브 상태를 백엔드 형식으로 변환
      let cubeColors = null
      if (cubeRef.current && cubeRef.current.getPieces) {
        const currentPieces = cubeRef.current.getPieces()
        console.log('📦 현재 큐브 조각:', currentPieces.length, '개')
        
        // 해법 생성 시점의 큐브 상태 저장 (깊은 복사)
        setInitialCubeState(currentPieces.map(piece => ({
          ...piece,
          position: [...piece.position],
          faceColors: [...piece.faceColors]
        })))
        
        // pieces를 백엔드 형식으로 변환
        const { convertCubePiecesToJson } = await import('./utils/cubeColorLoader')
        cubeColors = convertCubePiecesToJson(currentPieces)
        console.log('🎨 변환된 큐브 색상:', cubeColors)
      }
      
      const result = await generateSolution(cubeColors)
      
      if (result.success && result.data) {
        setSolution(result.data)
        setShowSolution(true)
        console.log('✅ 해법 생성 완료:', result.data)
      } else {
        throw new Error(result.error || '해법 생성 실패')
      }
    } catch (error) {
      console.error('해법 생성 오류:', error)
      setSolutionError(error.message)
      
      setTimeout(() => {
        setSolutionError(null)
      }, 5000)
    } finally {
      setIsGeneratingSolution(false)
    }
  }

  // 큐브에 이동 적용
  const handleApplyMove = (face, rotation) => {
    if (!cubeRef.current || !cubeRef.current.addRotation) {
      console.error('큐브 참조가 없습니다.')
      return
    }

    // rotation: 1(CW), -1(CCW), 2(180°)
    // addRotation의 direction: -1(CW), 1(CCW)
    // L, D, B 면은 반대쪽에서 보므로 방향 반전
    let direction = rotation === -1 ? 1 : -1
    
    // L, D, B 면은 방향 반전
    if (face === 'L' || face === 'D' || face === 'B') {
      direction = -direction
    }
    
    let rotations = Math.abs(rotation) === 2 ? 2 : 1

    console.log(`🔄 이동 적용: ${face} ${rotation} (방향: ${direction}, 회전수: ${rotations})`)

    // 첫 번째 회전
    cubeRef.current.addRotation(face, direction, 500)
    
    // 180도 회전은 두 번
    if (rotations === 2) {
      setTimeout(() => {
        cubeRef.current.addRotation(face, direction, 500)
      }, 50)
    }
  }

  // 모든 이동을 즉시 적용 (자동 해결)
  const handleAutoSolve = () => {
    if (!solution || !solution.moves) {
      console.error('해법이 없습니다.')
      return
    }

    if (!cubeRef.current || !cubeRef.current.addRotation) {
      console.error('큐브 참조가 없습니다.')
      return
    }

    console.log('⚡ 자동 해결 시작...', solution.moves.length, '개 이동')
    
    // 모든 이동을 큐에 추가 (빠른 속도로)
    solution.moves.forEach((move) => {
      const { face, rotation } = parseMove(move)
      
      // direction 계산
      let direction = rotation === -1 ? 1 : -1
      if (face === 'L' || face === 'D' || face === 'B') {
        direction = -direction
      }
      
      // 180도 회전 처리
      if (Math.abs(rotation) === 2) {
        cubeRef.current.addRotation(face, direction, 200) // 빠른 속도
        cubeRef.current.addRotation(face, direction, 200)
      } else {
        cubeRef.current.addRotation(face, direction, 200) // 빠른 속도
      }
    })
    
    console.log('✅ 모든 이동이 큐에 추가되었습니다.')
  }

  // 큐브 리셋 (초기 상태로 복원)
  const handleResetCube = () => {
    if (cubeRef.current && cubeRef.current.reset) {
      cubeRef.current.reset()
      console.log('🔄 큐브가 초기 상태로 복원되었습니다.')
    }
  }

  // SolutionViewer에서 사용하는 초기화 (섞인 상태로 복원)
  const handleResetToScrambled = () => {
    if (cubeRef.current && cubeRef.current.setPieces && initialCubeState) {
      // 저장된 섞인 상태로 복원
      const restoredPieces = initialCubeState.map(piece => ({
        ...piece,
        position: [...piece.position],
        faceColors: [...piece.faceColors]
      }))
      cubeRef.current.setPieces(restoredPieces)
      console.log('🔄 큐브가 섞인 초기 상태로 복원되었습니다.')
    }
  }

  // 루빅스 큐브 동작 표기법 파싱 및 실행 (임시 주석)
  const handleApplyMove_disabled = (move) => {
    if (!cubeRef.current || !cubeRef.current.addRotation) {
      console.error('큐브 참조가 없습니다.')
      return
    }

    // 동작 표기법 파싱
    // 예: "R", "R'", "R2", "U", "U'", "U2" 등
    const face = move.charAt(0) // 면 (R, L, U, D, F, B)
    const modifier = move.substring(1) // 수식자 (없음, ', 2)

    let direction = -1
    let rotations = 1 // 기본: 1회 회전

    if (modifier === "'") {
      direction = 1
    } else if (modifier === "2") {
      rotations = 2
    }

    console.log(`🔄 동작 실행: ${move} (면: ${face}, 방향: ${direction}, 회전수: ${rotations})`)

    // 회전 실행 (해법 적용은 일반 속도 500ms 사용)
    // 첫 번째 회전만 바로 실행하고, 나머지는 setTimeout으로 큐에 추가
    cubeRef.current.addRotation(face, direction, 500)
    
    if (rotations === 2) {
      // 180도 회전의 경우 두 번째 회전을 약간 지연시켜 큐에 추가되도록
      setTimeout(() => {
        cubeRef.current.addRotation(face, direction, 500)
      }, 50)
    }
  }

  return (
    <div className="app">
      <div className="app-header">
        <Controls cubeRef={cubeRef} />
        <ViewModeSelector viewMode={viewMode} onViewModeChange={setViewMode} />
        
        <ColorPicker 
          selectedColor={selectedColor}
          onColorSelect={handleColorSelect}
          colorEditMode={colorEditMode}
          onColorEditToggle={handleColorEditToggle}
          selectedCell={selectedCell}
        />
        
        {/* 이미지 업로드 버튼 */}
        <button 
          className="image-upload-toggle"
          onClick={handleImageUploadToggle}
          title="이미지 업로드하여 큐브 색상 분석"
        >
          📷 이미지 업로드
        </button>
        
        {/* 해법 생성 버튼 */}
        <button 
          className="generate-solution-btn"
          onClick={handleGenerateSolution}
          disabled={isGeneratingSolution}
          title="현재 큐브 상태로 해법 생성"
        >
          {isGeneratingSolution ? '⏳ 생성 중...' : '🎯 해법 생성'}
        </button>
        
        {/* 사용 안내 */}
        <div className="usage-hint">
          💡 <strong>사용 방법:</strong> 
          <br/>• 📷 이미지 업로드: 큐브 사진으로 자동 분석
          <br/>• 🎨 색상 편집: 직접 색상 선택하여 큐브 설정
          <br/>• 🎯 해법 생성: 설정된 큐브 상태로 해법 찾기
        </div>
        
        {solutionError && (
          <div className="solution-error">
            ✗ 오류: {solutionError}
          </div>
        )}
      </div>
      
      <div className={`content-container view-${viewMode.toLowerCase()}`}>
        <div 
          className="scene-container"
          style={{ 
            width: viewMode === 'BOTH' ? `${sceneWidth}%` : '100%',
            display: (viewMode === '3D' || viewMode === 'BOTH') ? 'flex' : 'none'
          }}
        >
          <Canvas
            camera={{ 
              position: [15, 15, 15], 
              fov: 50,
              near: 0.1,
              far: 1000
            }}
            style={{ 
              background: '#878787ff',
              width: '100%',
              height: '100%'
            }}
            gl={{ 
              antialias: true,
              powerPreference: "high-performance",
              alpha: false,
              depth: true,
              stencil: false,
              logarithmicDepthBuffer: true
            }}
            dpr={[1, 2]}
            onContextMenu={(e) => e.preventDefault()}
          >
            <ambientLight intensity={0.6} />
            <directionalLight 
              position={[10, 10, 10]} 
              intensity={0.8} 
              castShadow 
            />
            <pointLight 
              position={[-10, -10, -10]} 
              intensity={0.3} 
              color="#ffffff"
            />
            
            <RubiksCube 
              ref={cubeRef}
              onDataUpdate={handleCubeDataUpdate}
              colorEditMode={colorEditMode}
              selectedColor={selectedColor}
              selectedCell={selectedCell}
              onFaceColorChange={handleFaceColorChange}
              onCellSelect={handleCellSelect}
            />
            
            <OrbitControls 
              target={[0, 0, 0]}
              enablePan={true}
              enableZoom={true}
              enableRotate={true}
              enableDamping={true}
              dampingFactor={0.05}
              minDistance={8}
              maxDistance={50}
              maxPolarAngle={Math.PI}
              mouseButtons={{
                LEFT: 2,
                MIDDLE: 1,
                RIGHT: 0
              }}
              touches={{
                ONE: 2,
                TWO: 1
              }}
            />
          </Canvas>
        </div>
        
        {viewMode === 'BOTH' && (
          <Resizer onResize={handleResize} initialWidth={sceneWidth} />
        )}
        
        <div 
          className="net-container"
          style={{ 
            width: viewMode === 'BOTH' ? `${100 - sceneWidth}%` : '100%',
            display: (viewMode === 'NET' || viewMode === 'BOTH') ? 'flex' : 'none'
          }}
        >
          <CubeNet 
            pieces={cubeData} 
            colorEditMode={colorEditMode}
            selectedCell={selectedCell}
            onCellSelect={handleNetCellSelect}
          />
        </div>
      </div>

      {/* 이미지 업로드 모달 */}
      {showImageUpload && (
        <div className="modal-overlay" onClick={handleImageUploadToggle}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>이미지 업로드</h2>
              <button 
                className="modal-close"
                onClick={handleImageUploadToggle}
                title="닫기"
              >
                ✕
              </button>
            </div>
            <ImageUpload 
              onImageUpload={handleImageUpload}
              uploadedImages={uploadedImages}
              onAnalysisComplete={handleAnalysisComplete}
            />
          </div>
        </div>
      )}

      {/* 해법 뷰어 사이드 패널 */}
      {showSolution && solution && (
        <div className="solution-panel">
          <button 
            className="solution-close"
            onClick={() => setShowSolution(false)}
            title="닫기"
          >
            ✕
          </button>
          <SolutionViewer
            solution={solution.solution}
            moves={solution.moves}
            onApplyMove={handleApplyMove}
            onReset={handleResetToScrambled}
          />
        </div>
      )}
    </div>
  )
}

export default App
