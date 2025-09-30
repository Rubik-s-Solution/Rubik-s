import React, { useState } from 'react'

const COLOR_INFO = {
  'r': { color: '#C41E3A', name: '빨강' },
  'g': { color: '#009E60', name: '초록' },
  'b': { color: '#0051BA', name: '파랑' },
  'o': { color: '#FF5800', name: '주황' },
  'y': { color: '#FFD500', name: '노랑' },
  'w': { color: '#FFFFFF', name: '하양' }
}

function ColorGuide() {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="color-guide">
      <button 
        onClick={() => setIsVisible(!isVisible)}
        className="color-guide-toggle"
      >
        {isVisible ? '색상 가이드 숨기기' : '색상 가이드 보기'}
      </button>
      
      {isVisible && (
        <div className="color-guide-panel">
          <h4>JSON 색상 문자 매핑</h4>
          <div className="color-mappings">
            {Object.entries(COLOR_INFO).map(([char, info]) => (
              <div key={char} className="color-mapping-item">
                <span className="color-char">'{char}'</span>
                <div 
                  className="color-sample" 
                  style={{ backgroundColor: info.color }}
                  title={info.name}
                />
                <span className="color-name">{info.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default ColorGuide