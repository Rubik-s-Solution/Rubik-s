import React, { useState, useRef, useEffect } from 'react';
import './SolutionOverlay.css';

// 회전 표기를 한글로 변환
const toKoreanNotation = (move) => {
  const faceNames = {
    'U': '위 면',
    'D': '아래 면',
    'R': '오른쪽 면',
    'L': '왼쪽 면',
    'F': '앞 면',
    'B': '뒤 면'
  };
  
  const face = move[0];
  const modifier = move.slice(1);
  
  let korean = faceNames[face] || move;
  
  if (modifier === "'") {
    korean += " 반시계 90°";
  } else if (modifier === "2") {
    korean += " 180°";
  } else {
    korean += " 시계 90°";
  }
  
  return korean;
};

function SolutionOverlay({ 
  currentStep, 
  totalSteps, 
  currentMove,
  moves,
  onNext, 
  onPrev,
  onReset,
  onClose,
  disabled 
}) {
  const [showMovesList, setShowMovesList] = useState(false);
  const moveItemsRef = useRef([]);
  const progress = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;

  // 현재 단계로 자동 스크롤
  useEffect(() => {
    if (showMovesList && moveItemsRef.current[currentStep]) {
      moveItemsRef.current[currentStep].scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest'
      });
    }
  }, [currentStep, showMovesList]);

  return (
    <>
      {/* 왼쪽 이전 화살표 */}
      <button
        className="solution-nav-arrow solution-nav-left"
        onClick={onPrev}
        disabled={disabled || currentStep === 0}
        title="이전 단계"
      >
        <svg width="60" height="60" viewBox="0 0 60 60">
          <circle cx="30" cy="30" r="28" fill="rgba(255,255,255,0.85)" stroke="#333" strokeWidth="2"/>
          <path d="M 35 18 L 23 30 L 35 42" stroke="#333" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {/* 오른쪽 다음 화살표 */}
      <button
        className="solution-nav-arrow solution-nav-right"
        onClick={onNext}
        disabled={disabled || currentStep >= totalSteps}
        title="다음 단계"
      >
        <svg width="60" height="60" viewBox="0 0 60 60">
          <circle cx="30" cy="30" r="28" fill="rgba(255,255,255,0.85)" stroke="#333" strokeWidth="2"/>
          <path d="M 25 18 L 37 30 L 25 42" stroke="#333" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {/* 하단 정보 패널 */}
      <div className="solution-info-panel">
        {/* 닫기 버튼 */}
        <button 
          className="solution-overlay-close"
          onClick={onClose}
          title="해법 닫기"
        >
          ✕
        </button>

        {/* 메인 정보 영역 */}
        <div className="solution-main-info">
          <div className="solution-progress-section">
            <span className="progress-text">{currentStep} / {totalSteps}</span>
            <div className="progress-bar-mini">
              <div className="progress-fill-mini" style={{ width: `${progress}%` }} />
            </div>
          </div>

          {currentMove && currentStep <= totalSteps && (
            <div className="solution-current-move">
              <span className="move-notation-large">{currentMove}</span>
              <span className="move-description-text">{toKoreanNotation(currentMove)}</span>
            </div>
          )}

          {currentStep >= totalSteps && totalSteps > 0 && (
            <div className="solution-complete">
              ✅ 큐브 해법 완료!
            </div>
          )}

          {/* 컨트롤 버튼들 */}
          <div className="solution-controls-mini">
            <button
              className="control-mini-btn"
              onClick={() => setShowMovesList(!showMovesList)}
              title="이동 목록 보기"
            >
              📋 목록
            </button>
            <button
              className="control-mini-btn"
              onClick={onReset}
              disabled={disabled}
              title="초기화"
            >
              🔄 초기화
            </button>
          </div>
        </div>

        {/* 이동 목록 패널 (토글) */}
        {showMovesList && (
          <div className="moves-list-panel">
            <div className="moves-list-header">
              <h4>📋 이동 순서</h4>
              <button 
                className="moves-list-close"
                onClick={() => setShowMovesList(false)}
              >
                ▼
              </button>
            </div>
            <div className="moves-list-scroll">
              {moves && moves.map((move, index) => {
                const isActive = index === currentStep;
                const isPast = index < currentStep;
                const isFuture = index > currentStep;
                
                return (
                  <div
                    key={index}
                    ref={el => moveItemsRef.current[index] = el}
                    className={`move-item-mini ${isActive ? 'active' : ''} ${isPast ? 'completed' : ''} ${isFuture ? 'future' : ''}`}
                  >
                    <span className="move-number-mini">{index + 1}.</span>
                    <span className="move-notation-mini">{move}</span>
                    <span className="move-korean-mini">{toKoreanNotation(move)}</span>
                    {isActive && <span className="move-indicator-mini">◀</span>}
                    {isPast && <span className="move-check-mini">✓</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default SolutionOverlay;
