import React, { useState, useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import RubiksCube from './components/RubiksCube'
import Controls from './components/Controls'
import CubeNet from './components/CubeNet'
import ViewModeSelector from './components/ViewModeSelector'
import Resizer from './components/Resizer'
import './App.css'

function App() {
  const [viewMode, setViewMode] = useState('3D')
  const [cubeData, setCubeData] = useState([])
  const [sceneWidth, setSceneWidth] = useState(60) // 3D 씬의 너비 (%)
  const cubeRef = useRef()

  // 큐브 데이터 업데이트 핸들러
  const handleCubeDataUpdate = (pieces) => {
    setCubeData(pieces)
  }

  // 리사이저 핸들러
  const handleResize = (newWidth) => {
    setSceneWidth(newWidth)
  }

  return (
    <div className="app">
      <div className="app-header">
        <Controls cubeRef={cubeRef} />
        <ViewModeSelector 
          currentMode={viewMode} 
          onModeChange={setViewMode} 
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
          <CubeNet pieces={cubeData} />
        </div>
      </div>
      
      <div className="info">
        Built with <a href="https://threejs.org">Three.js</a> and{' '}
        <a href="https://docs.pmnd.rs/react-three-fiber">React Three Fiber</a>
      </div>
    </div>
  )
}

export default App
