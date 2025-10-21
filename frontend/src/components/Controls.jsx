import React, { useState } from 'react'

function Controls({ cubeRef }) {
  const [isMoving, setIsMoving] = useState(false)

  // 큐브 컨트롤 함수들 호출
  const handleShuffle = () => {
    console.log('🎲 Shuffle 버튼 클릭됨')
    console.log('cubeRef:', cubeRef)
    console.log('cubeRef.current:', cubeRef?.current)
    console.log('window.rubiksCube:', window.rubiksCube)
    
    const cube = cubeRef?.current || window.rubiksCube
    
    if (cube && cube.shuffle && !cube.isMoving) {
      console.log('✅ shuffle 함수 호출')
      cube.shuffle()
    } else {
      console.error('❌ shuffle 실행 불가:', {
        hasCube: !!cube,
        hasShuffle: !!cube?.shuffle,
        isMoving: cube?.isMoving
      })
    }
  }

  const handleUndo = () => {
    console.log('↩️ Undo 버튼 클릭됨')
    const cube = cubeRef?.current || window.rubiksCube
    
    if (cube && cube.undo && !cube.isMoving) {
      console.log('✅ undo 함수 호출')
      cube.undo()
    } else {
      console.error('❌ undo 실행 불가')
    }
  }

  const handleReset = () => {
    console.log('🔄 Reset 버튼 클릭됨')
    const cube = cubeRef?.current || window.rubiksCube
    
    if (cube && cube.reset && !cube.isMoving) {
      console.log('✅ reset 함수 호출')
      cube.reset()
    } else {
      console.error('❌ reset 실행 불가')
    }
  }

  // 이동 상태 체크
  React.useEffect(() => {
    const checkMovingState = () => {
      const cube = cubeRef?.current || window.rubiksCube
      if (cube) {
        setIsMoving(cube.isMoving)
      }
    }
    
    const interval = setInterval(checkMovingState, 100)
    return () => clearInterval(interval)
  }, [cubeRef])

  return (
    <div className="controls">
      <button 
        onClick={handleShuffle}
        disabled={isMoving}
      >
        Shuffle
      </button>
      
      <button 
        onClick={handleUndo}
        disabled={isMoving}
      >
        Undo
      </button>
      
      <button 
        onClick={handleReset}
        disabled={isMoving}
      >
        Reset
      </button>
      
      <select defaultValue="3" disabled>
        <option value="3">3x3</option>
      </select>
      
      <div className="keyboard-help">
        <div>키보드: R/L (좌우), U/D (상하), F/B (앞뒤) | Shift+키 = 반시계방향</div>
        <div>마우스: 좌클릭 = 시계방향, 우클릭 = 반시계방향</div>
      </div>
    </div>
  )
}

export default Controls