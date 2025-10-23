import React from 'react';
import './CubeNavigator.css';

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
    korean += " 반시계 방향 90°";
  } else if (modifier === "2") {
    korean += " 180° 회전";
  } else {
    korean += " 시계 방향 90°";
  }
  
  return korean;
};

// 회전 방향 아이콘 가져오기
const getRotationIcon = (move) => {
  const modifier = move.slice(1);
  
  if (modifier === "'") {
    return "↺"; // 반시계
  } else if (modifier === "2") {
    return "↻↻"; // 180도
  } else {
    return "↻"; // 시계
  }
};

function CubeNavigator({ 
  currentStep, 
  totalSteps, 
  currentMove,
  nextMove,
  onNext, 
  onPrev, 
  disabled 
}) {
  const progress = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0;

  return (
    <div className="cube-navigator">
      {/* 이전 버튼 */}
      <button
        className="nav-arrow nav-arrow-left"
        onClick={onPrev}
        disabled={disabled || currentStep === 0}
        title="이전 단계"
      >
        <svg width="40" height="40" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="rgba(255,255,255,0.9)" stroke="#333" strokeWidth="2"/>
          <path d="M 24 12 L 16 20 L 24 28" stroke="#333" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {/* 중앙 정보 영역 */}
      <div className="nav-info">
        {/* 진행 상태 */}
        <div className="nav-progress">
          <div className="progress-text">
            {currentStep} / {totalSteps}
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* 현재 이동 정보 */}
        {currentMove && (
          <div className="current-move-info">
            <div className="move-label">현재 단계:</div>
            <div className="move-notation">
              {currentMove} {getRotationIcon(currentMove)}
            </div>
            <div className="move-description">
              {toKoreanNotation(currentMove)}
            </div>
          </div>
        )}

        {/* 다음 이동 미리보기 */}
        {nextMove && currentStep < totalSteps && (
          <div className="next-move-preview">
            <div className="preview-label">다음 단계:</div>
            <div className="preview-notation">
              {nextMove} {getRotationIcon(nextMove)}
            </div>
            <div className="preview-description">
              {toKoreanNotation(nextMove)}
            </div>
          </div>
        )}

        {/* 완료 메시지 */}
        {currentStep >= totalSteps && totalSteps > 0 && (
          <div className="completion-message">
            ✅ 큐브 해법 완료!
          </div>
        )}
      </div>

      {/* 다음 버튼 */}
      <button
        className="nav-arrow nav-arrow-right"
        onClick={onNext}
        disabled={disabled || currentStep >= totalSteps}
        title="다음 단계"
      >
        <svg width="40" height="40" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="rgba(255,255,255,0.9)" stroke="#333" strokeWidth="2"/>
          <path d="M 16 12 L 24 20 L 16 28" stroke="#333" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
    </div>
  );
}

export default CubeNavigator;
