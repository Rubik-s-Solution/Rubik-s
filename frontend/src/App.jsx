import React, { useState, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import RubiksCube from './components/RubiksCube'
import Controls from './components/Controls'
import CubeNet from './components/CubeNet'
import ViewModeSelector from './components/ViewModeSelector'
import Resizer from './components/Resizer'
import ColorPicker, { COLORS } from './components/ColorPicker'
import './App.css'

function App() {
  const [viewMode, setViewMode] = useState('3D')
  const [cubeData, setCubeData] = useState([])
  const [sceneWidth, setSceneWidth] = useState(60) // 3D 씬의 너비 (%)
  const [colorEditMode, setColorEditMode] = useState(false)
  const [selectedColor, setSelectedColor] = useState('red')
  const [selectedCell, setSelectedCell] = useState(null) // 선택된 칸 {pieceId, faceIndex}
  const cubeRef = useRef()

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

  // 면 색상 변경 (구버전 호환)
  const handleFaceColorChange = (pieceId, faceIndex) => {
    if (!selectedColor) return
    
    const colorHex = COLORS[selectedColor].hex
    const colorNumber = parseInt(colorHex.replace('#', ''), 16)
    
    if (cubeRef.current.updatePieceFaceColor) {
      cubeRef.current.updatePieceFaceColor(pieceId, faceIndex, colorNumber)
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
    </div>
  )
}

export default App
