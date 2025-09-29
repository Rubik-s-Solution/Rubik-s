import React from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import RubiksCube from './components/RubiksCube'
import Controls from './components/Controls'
import './App.css'

function App() {
  return (
    <div className="app">
      <Controls />
      
      <div className="scene-container">
        <Canvas
          camera={{ 
            position: [-20, 20, 30], 
            fov: 45 
          }}
          style={{ 
            background: '#878787ff' 
          }}
          gl={{ 
            antialias: true,
            powerPreference: "high-performance",
            alpha: false,
            depth: true,
            stencil: false,
            logarithmicDepthBuffer: true // Z-fighting 방지
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
          
          <RubiksCube />
          
          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            enableDamping={true}
            dampingFactor={0.05}
            mouseButtons={{
              LEFT: 2,    // 왼쪽 클릭으로 팬
              MIDDLE: 1,  // 중간 클릭으로 줌
              RIGHT: 0    // 우클릭으로 회전
            }}
            touches={{
              ONE: 2,     // 한 손가락으로 팬
              TWO: 1      // 두 손가락으로 줌
            }}
          />
        </Canvas>
      </div>
      
      <div className="info">
        Built with <a href="https://threejs.org">Three.js</a> and{' '}
        <a href="https://docs.pmnd.rs/react-three-fiber">React Three Fiber</a>
      </div>
    </div>
  )
}

export default App
