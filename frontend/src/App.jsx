import React, { useState, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import RubiksCube from './components/RubiksCube'
import Controls from './components/Controls'
import CubeNet from './components/CubeNet'
import ViewModeSelector from './components/ViewModeSelector'
import Resizer from './components/Resizer'
import ColorPicker, { COLORS } from './components/ColorPicker'
import ColorGuide from './components/ColorGuide'
import ImageUpload from './components/ImageUpload'
import { loadAndConvertCubeData } from './utils/cubeColorLoader'
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
  const cubeRef = useRef()
  const fileInputRef = useRef()

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
  const handleImageUploadToggle = () => {
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

  return (
    <div className="app">
      <div className="app-header">
        <Controls cubeRef={cubeRef} />
        <ViewModeSelector viewMode={viewMode} onViewModeChange={setViewMode} />
        
        {/* JSON 큐브 색상 로드 버튼 */}
        <div className="json-loader">
          <div className="json-buttons">
            <button 
              onClick={handleLoadCubeColorsFromJson}
              disabled={isLoadingJson}
              className="load-json-btn"
            >
              {isLoadingJson ? '로딩 중...' : '기본 JSON 로드'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              disabled={isLoadingJson}
              className="file-input"
              id="json-file-input"
            />
            <label 
              htmlFor="json-file-input" 
              className={`file-input-label ${isLoadingJson ? 'disabled' : ''}`}
            >
              JSON 파일 업로드
            </label>
          </div>
          {jsonLoadSuccess && (
            <div className="json-success">
              ✓ 색상 데이터가 성공적으로 로드되었습니다!
            </div>
          )}
          {jsonLoadError && (
            <div className="json-error">
              ✗ 에러: {jsonLoadError}
            </div>
          )}
        </div>
        
        <ColorGuide />
        
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
          title="이미지 업로드"
        >
          📷 이미지 업로드
        </button>
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
      
      <div className="info">
        <h1>큐브 컨트롤은 개선 예정</h1>
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
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default App
