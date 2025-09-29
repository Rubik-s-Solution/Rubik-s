import React, { useState, useCallback, useRef, useEffect } from 'react'

function Resizer({ onResize, initialWidth = 60 }) {
  const [isResizing, setIsResizing] = useState(false)
  const [currentWidth, setCurrentWidth] = useState(initialWidth)
  const resizerRef = useRef()

  const startResizing = useCallback((mouseDownEvent) => {
    setIsResizing(true)
    
    const startX = mouseDownEvent.clientX
    const startWidth = currentWidth

    const handleMouseMove = (mouseMoveEvent) => {
      const deltaX = mouseMoveEvent.clientX - startX
      const containerWidth = window.innerWidth
      const newWidthPercent = Math.max(20, Math.min(80, startWidth + (deltaX / containerWidth) * 100))
      
      setCurrentWidth(newWidthPercent)
      onResize?.(newWidthPercent)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [currentWidth, onResize])

  // 터치 이벤트 지원
  const startResizingTouch = useCallback((touchStartEvent) => {
    setIsResizing(true)
    
    const startX = touchStartEvent.touches[0].clientX
    const startWidth = currentWidth

    const handleTouchMove = (touchMoveEvent) => {
      const deltaX = touchMoveEvent.touches[0].clientX - startX
      const containerWidth = window.innerWidth
      const newWidthPercent = Math.max(20, Math.min(80, startWidth + (deltaX / containerWidth) * 100))
      
      setCurrentWidth(newWidthPercent)
      onResize?.(newWidthPercent)
    }

    const handleTouchEnd = () => {
      setIsResizing(false)
      document.removeEventListener('touchmove', handleTouchMove)
      document.removeEventListener('touchend', handleTouchEnd)
    }

    document.addEventListener('touchmove', handleTouchMove)
    document.addEventListener('touchend', handleTouchEnd)
  }, [currentWidth, onResize])

  // 초기 너비 설정
  useEffect(() => {
    onResize?.(currentWidth)
  }, [])

  return (
    <div 
      ref={resizerRef}
      className={`resizer ${isResizing ? 'resizing' : ''}`}
      onMouseDown={startResizing}
      onTouchStart={startResizingTouch}
      title="드래그하여 크기 조절"
    >
      <div className="resizer-handle">
        <div className="resizer-line"></div>
        <div className="resizer-line"></div>
        <div className="resizer-line"></div>
      </div>
    </div>
  )
}

export default Resizer