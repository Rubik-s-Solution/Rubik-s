import React, { useState } from 'react'

function Controls() {
  const [isMoving, setIsMoving] = useState(false)

  // 큐브 컨트롤 함수들 호출
  const handleShuffle = () => {
    if (window.rubiksCube && !window.rubiksCube.isMoving) {
      window.rubiksCube.shuffle()
    }
  }

  const handleSolve = () => {
    if (window.rubiksCube && !window.rubiksCube.isMoving) {
      window.rubiksCube.solve()
    }
  }

  const handleUndo = () => {
    if (window.rubiksCube && !window.rubiksCube.isMoving) {
      window.rubiksCube.undo()
    }
  }

  const handleReset = () => {
    if (window.rubiksCube && !window.rubiksCube.isMoving) {
      window.rubiksCube.reset()
    }
  }

  // 이동 상태 체크
  React.useEffect(() => {
    const checkMovingState = () => {
      if (window.rubiksCube) {
        setIsMoving(window.rubiksCube.isMoving)
      }
    }
    
    const interval = setInterval(checkMovingState, 100)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="controls">
      <button 
        onClick={handleShuffle}
        disabled={isMoving}
      >
        Shuffle
      </button>
      
      <button 
        onClick={handleSolve}
        disabled={isMoving}
      >
        Solve
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