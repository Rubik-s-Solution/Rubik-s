import React from 'react'

const VIEW_MODES = {
  '3D': '3D 뷰',
  'NET': '전개도',
  'BOTH': '3D + 전개도'
}

function ViewModeSelector({ viewMode, onViewModeChange }) {
  return (
    <div className="view-mode-selector">
      <span className="view-mode-label">뷰 모드:</span>
      <div className="view-mode-buttons">
        {Object.entries(VIEW_MODES).map(([key, label]) => (
          <button
            key={key}
            className={`view-mode-button ${viewMode === key ? 'active' : ''}`}
            onClick={() => onViewModeChange(key)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default ViewModeSelector