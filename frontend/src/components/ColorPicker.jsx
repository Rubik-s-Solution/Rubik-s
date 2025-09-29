import React, { useState } from 'react'

// 루빅스 큐브의 6가지 색상
const COLORS = {
  red: { hex: '#C41E3A', name: '빨강' },
  orange: { hex: '#FF5800', name: '주황' },
  yellow: { hex: '#FFD500', name: '노랑' },
  green: { hex: '#009E60', name: '초록' },
  blue: { hex: '#0051BA', name: '파랑' },
  white: { hex: '#FFFFFF', name: '하양' }
}

function ColorPicker({ colorEditMode, selectedColor, onColorSelect, onColorEditToggle, selectedCell }) {
  return (
    <div className="color-picker-container">
      <button 
        className={`color-picker-toggle ${colorEditMode ? 'active' : ''}`}
        onClick={onColorEditToggle}
        title="색상 편집 모드"
      >
        🎨 색상 편집
      </button>
      
      {colorEditMode && (
        <div className="color-picker-panel">
          <div className="color-picker-title">
            {selectedCell ? '색상을 선택하세요' : '먼저 큐브의 칸을 클릭하세요'}
          </div>
          <div className="color-grid">
            {Object.entries(COLORS).map(([colorKey, colorInfo]) => (
              <button
                key={colorKey}
                className={`color-option ${selectedColor === colorKey ? 'selected' : ''}`}
                style={{ 
                  backgroundColor: colorInfo.hex,
                  border: colorInfo.hex === '#FFFFFF' ? '2px solid #ccc' : '2px solid transparent'
                }}
                onClick={() => onColorSelect(colorKey)}
                title={colorInfo.name}
              >
                {selectedColor === colorKey && (
                  <span className="color-checkmark">✓</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export { COLORS }
export default ColorPicker