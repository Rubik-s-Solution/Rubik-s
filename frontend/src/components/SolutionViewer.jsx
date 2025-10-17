import React, { useState, useEffect } from 'react'
import './SolutionViewer.css'

// 루빅스 큐브 동작 설명
const MOVE_DESCRIPTIONS = {
  'U': '윗면 시계방향',
  "U'": '윗면 반시계방향',
  'U2': '윗면 180도',
  'D': '아랫면 시계방향',
  "D'": '아랫면 반시계방향',
  'D2': '아랫면 180도',
  'F': '앞면 시계방향',
  "F'": '앞면 반시계방향',
  'F2': '앞면 180도',
  'B': '뒷면 시계방향',
  "B'": '뒷면 반시계방향',
  'B2': '뒷면 180도',
  'L': '왼쪽 시계방향',
  "L'": '왼쪽 반시계방향',
  'L2': '왼쪽 180도',
  'R': '오른쪽 시계방향',
  "R'": '오른쪽 반시계방향',
  'R2': '오른쪽 180도',
}

function SolutionViewer({ solution, onClose, onApplyMove, onRestoreCube }) {
  const [currentStep, setCurrentStep] = useState(-1) // -1: 시작 전
  const [isAutoPlay, setIsAutoPlay] = useState(false)
  const [autoPlaySpeed, setAutoPlaySpeed] = useState(1000) // ms

  // 자동 재생 효과
  useEffect(() => {
    if (!isAutoPlay || !solution?.moves) return
    
    if (currentStep < solution.moves.length - 1) {
      const timer = setTimeout(() => {
        const nextStep = currentStep + 1
        setCurrentStep(nextStep)
        if (onApplyMove && solution.moves[nextStep]) {
          onApplyMove(solution.moves[nextStep])
        }
      }, autoPlaySpeed)
      
      return () => clearTimeout(timer)
    } else {
      setIsAutoPlay(false)
    }
  }, [isAutoPlay, currentStep, solution, autoPlaySpeed, onApplyMove])

  // 다음 단계
  const handleNext = () => {
    if (currentStep < solution.moves.length - 1) {
      const nextStep = currentStep + 1
      setCurrentStep(nextStep)
      if (onApplyMove) {
        onApplyMove(solution.moves[nextStep])
      }
    }
  }

  // 이전 단계
  const handlePrevious = () => {
    if (currentStep >= 0) {
      setCurrentStep(currentStep - 1)
      // 이전 단계는 큐브를 리셋해야 하므로 구현이 복잡할 수 있음
      // 현재는 단순히 인덱스만 조정
    }
  }

  // 리셋
  const handleReset = () => {
    setCurrentStep(-1)
    setIsAutoPlay(false)
  }

  // 자동 재생 토글
  const handleAutoPlayToggle = () => {
    if (currentStep >= solution.moves.length - 1) {
      // 끝까지 갔으면 리셋하고 시작
      setCurrentStep(-1)
    }
    setIsAutoPlay(!isAutoPlay)
  }

  if (!solution) {
    return (
      <div className="solution-viewer">
        <div className="solution-header">
          <h2>큐브 해법</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="solution-content">
          <div className="no-solution">
            <p>해법이 없습니다.</p>
            <p>모든 6개 면의 이미지를 업로드하거나 색상을 설정한 후 "해법 생성" 버튼을 눌러주세요.</p>
          </div>
        </div>
      </div>
    )
  }

  const { status, moves, move_count, missing_faces, error } = solution

  if (status !== 'success') {
    return (
      <div className="solution-viewer">
        <div className="solution-header">
          <h2>큐브 해법</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="solution-content">
          <div className="solution-error">
            {status === 'incomplete_cube' && (
              <>
                <h3>⚠️ 불완전한 큐브</h3>
                <p>모든 6개 면이 필요합니다.</p>
                {missing_faces && missing_faces.length > 0 && (
                  <p className="missing-faces">
                    누락된 면: <strong>{missing_faces.join(', ')}</strong>
                  </p>
                )}
              </>
            )}
            {status === 'kociemba_not_installed' && (
              <>
                <h3>❌ Kociemba 미설치</h3>
                <p>백엔드에 kociemba 패키지가 설치되지 않았습니다.</p>
              </>
            )}
            {status === 'solve_failed' && (
              <>
                <h3>❌ 해법 생성 실패</h3>
                <p>잘못된 큐브 상태입니다. 색상을 확인해주세요.</p>
                {error && <p className="error-detail">{error}</p>}
              </>
            )}
            {status === 'conversion_failed' && (
              <>
                <h3>❌ 변환 실패</h3>
                <p>큐브 색상 데이터를 변환할 수 없습니다.</p>
                {error && <p className="error-detail">{error}</p>}
              </>
            )}
            {status === 'error' && (
              <>
                <h3>❌ 오류 발생</h3>
                <p>해법 생성 중 오류가 발생했습니다.</p>
                {error && <p className="error-detail">{error}</p>}
              </>
            )}
            {error && !['incomplete_cube', 'kociemba_not_installed', 'solve_failed', 'conversion_failed', 'error'].includes(status) && (
              <>
                <h3>❌ 오류</h3>
                <p className="error-detail">{error}</p>
              </>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="solution-viewer">
      <div className="solution-header">
        <h2>🎯 큐브 해법</h2>
        <div className="solution-stats">
          <span className="move-count">{move_count}개 동작</span>
        </div>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>
      
      <div className="solution-content">
        {/* 컨트롤 패널 */}
        <div className="solution-controls">
          {onRestoreCube && (
            <button 
              className="control-btn restore-btn"
              onClick={() => {
                onRestoreCube()
                handleReset()
              }}
              title="해법 생성 시점의 큐브 상태로 복원"
            >
              🔄 큐브 복원
            </button>
          )}
          <button 
            className="control-btn"
            onClick={handleReset}
            disabled={currentStep === -1}
          >
            ⏮️ 리셋
          </button>
          <button 
            className="control-btn"
            onClick={handlePrevious}
            disabled={currentStep <= 0 || isAutoPlay}
          >
            ⏪ 이전
          </button>
          <button 
            className="control-btn play-btn"
            onClick={handleAutoPlayToggle}
          >
            {isAutoPlay ? '⏸️ 일시정지' : '▶️ 자동재생'}
          </button>
          <button 
            className="control-btn"
            onClick={handleNext}
            disabled={currentStep >= moves.length - 1 || isAutoPlay}
          >
            다음 ⏩
          </button>
          
          <div className="speed-control">
            <label>속도:</label>
            <select 
              value={autoPlaySpeed} 
              onChange={(e) => setAutoPlaySpeed(Number(e.target.value))}
            >
              <option value={2000}>느림 (2초)</option>
              <option value={1000}>보통 (1초)</option>
              <option value={500}>빠름 (0.5초)</option>
            </select>
          </div>
        </div>

        {/* 현재 단계 표시 */}
        <div className="current-step">
          <div className="step-info">
            {currentStep === -1 ? (
              <div className="step-waiting">
                <p>👆 "다음" 또는 "자동재생" 버튼을 눌러 시작하세요</p>
              </div>
            ) : (
              <>
                <div className="step-number">
                  단계 {currentStep + 1} / {moves.length}
                </div>
                <div className="step-move">
                  <span className="move-notation">{moves[currentStep]}</span>
                  <span className="move-description">
                    {MOVE_DESCRIPTIONS[moves[currentStep]] || moves[currentStep]}
                  </span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${((currentStep + 1) / moves.length) * 100}%` }}
                  />
                </div>
              </>
            )}
          </div>
        </div>

        {/* 전체 동작 리스트 */}
        <div className="solution-moves">
          <h3>전체 동작 순서</h3>
          <div className="moves-list">
            {moves.map((move, index) => (
              <div 
                key={index}
                className={`move-item ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
                onClick={() => {
                  if (!isAutoPlay) {
                    // 다음 동작으로만 이동 가능 (순차적 실행)
                    if (index === currentStep + 1) {
                      setCurrentStep(index)
                      if (onApplyMove) {
                        onApplyMove(move)
                      }
                    }
                  }
                }}
                style={{ cursor: !isAutoPlay && index === currentStep + 1 ? 'pointer' : 'default' }}
              >
                <span className="move-index">{index + 1}</span>
                <span className="move-text">{move}</span>
                <span className="move-desc">{MOVE_DESCRIPTIONS[move]}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 동작 표기법 설명 */}
        <div className="notation-guide">
          <h3>📝 표기법 가이드</h3>
          <div className="notation-grid">
            <div className="notation-item">
              <strong>U, D, F, B, L, R</strong>
              <span>각 면을 시계방향으로 90° 회전</span>
            </div>
            <div className="notation-item">
              <strong>U', D', F', B', L', R'</strong>
              <span>각 면을 반시계방향으로 90° 회전</span>
            </div>
            <div className="notation-item">
              <strong>U2, D2, F2, B2, L2, R2</strong>
              <span>각 면을 180° 회전</span>
            </div>
          </div>
          <div className="face-legend">
            <strong>면 약어:</strong> U=윗면, D=아랫면, F=앞면, B=뒷면, L=왼쪽, R=오른쪽
          </div>
        </div>
      </div>
    </div>
  )
}

export default SolutionViewer
