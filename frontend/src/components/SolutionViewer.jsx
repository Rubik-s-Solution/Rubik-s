import React, { useState, useEffect } from 'react';
import './SolutionViewer.css';
import { 
  parseSolution, 
  parseMove, 
  calculateSolutionStats,
  groupMoves 
} from '../utils/cubeSolver';

// 회전 표기를 한글로 변환
const toKoreanNotation = (move) => {
  const faceNames = {
    'U': '위',
    'D': '아래',
    'R': '오른쪽',
    'L': '왼쪽',
    'F': '앞',
    'B': '뒤'
  };
  
  const face = move[0];
  const modifier = move.slice(1);
  
  let korean = faceNames[face] || move;
  
  if (modifier === "'") {
    korean += " 반시계";
  } else if (modifier === "2") {
    korean += " 180°";
  } else {
    korean += " 시계";
  }
  
  return korean;
};

function SolutionViewer({ solution, moves, onApplyMove, onReset }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [moveQueue, setMoveQueue] = useState([]); // 회전 요청 큐
  const [isProcessing, setIsProcessing] = useState(false); // 큐 처리 중 상태
  const [autoPlaySpeed, setAutoPlaySpeed] = useState(1000); // ms
  const autoPlayTimerRef = React.useRef(null);
  const isPendingRef = React.useRef(false); // 동기적 플래그 - 큐 추가 중인지 확인
  const moveItemsRef = React.useRef([]); // 각 move item에 대한 ref 배열
  
  // solution 문자열 또는 moves 배열 처리
  const moveList = moves || parseSolution(solution);
  const stats = calculateSolutionStats(moveList);
  const groups = groupMoves(moveList, 5);

  // 현재 단계로 자동 스크롤
  useEffect(() => {
    if (moveItemsRef.current[currentStep]) {
      moveItemsRef.current[currentStep].scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest'
      });
    }
  }, [currentStep]);

  // 큐 처리 useEffect - 회전 완료 후 다음 처리
  useEffect(() => {
    if (moveQueue.length > 0 && !isProcessing) {
      setIsProcessing(true);
      const nextMove = moveQueue[0];
      
      // 회전 실행
      const { face, rotation, stepUpdate } = nextMove;
      onApplyMove(face, rotation);
      
      // stepUpdate 실행 (currentStep 업데이트)
      if (stepUpdate) {
        stepUpdate();
      }
      
      // 회전 완료 대기 시간 계산
      // rotation = 2 (180도)는 90도 2번 = 1000ms (500ms × 2)
      // rotation = 1/-1 (90도)는 500ms
      const rotationTime = Math.abs(rotation) === 2 ? 1000 : 500;
      const waitTime = rotationTime + 100; // 여유 시간 추가
      
      console.log(`⏱️ [SolutionViewer] 회전 대기: ${waitTime}ms (rotation=${rotation})`);
      
      setTimeout(() => {
        setMoveQueue(prev => prev.slice(1)); // 큐에서 제거
        setIsProcessing(false);
        isPendingRef.current = false; // 플래그 해제
      }, waitTime);
    }
  }, [moveQueue, isProcessing, onApplyMove]);

  const handleNextStep = () => {
    if (currentStep >= moveList.length || isPendingRef.current) return; // 동기적 체크!
    
    isPendingRef.current = true; // 즉시 플래그 설정
    
    const move = moveList[currentStep];
    const { face, rotation } = parseMove(move);
    const nextStep = currentStep + 1;
    
    // 큐에 회전 요청 추가
    setMoveQueue(prev => [...prev, {
      face,
      rotation,
      targetStep: nextStep,
      stepUpdate: () => setCurrentStep(nextStep)
    }]);
  };

  const handlePrevStep = () => {
    if (currentStep <= 0 || isPendingRef.current) return; // 동기적 체크!
    
    isPendingRef.current = true; // 즉시 플래그 설정
    
    const move = moveList[currentStep - 1];
    const { face, rotation } = parseMove(move);
    const prevStep = currentStep - 1;
    
    // 큐에 회전 요청 추가 (역방향)
    setMoveQueue(prev => [...prev, {
      face,
      rotation: rotation === 2 ? 2 : -rotation,
      targetStep: prevStep,
      stepUpdate: () => setCurrentStep(prevStep)
    }]);
  };

  const handleAutoPlay = () => {
    if (autoPlayTimerRef.current) {
      // 자동 재생 중지
      autoPlayTimerRef.current = null;
      setMoveQueue([]); // 큐 비우기
      isPendingRef.current = false; // 플래그 해제
      return;
    }
    
    // 이미 끝까지 갔으면 처음부터
    if (currentStep >= moveList.length) {
      setCurrentStep(0);
      onReset();
      return;
    }
    
    if (isPendingRef.current) return; // 이미 처리 중이면 무시
    
    // 자동 재생 시작 - 모든 남은 이동을 큐에 추가
    const remainingMoves = moveList.slice(currentStep);
    if (remainingMoves.length === 0) return;
    
    isPendingRef.current = true; // 플래그 설정
    
    setMoveQueue(prev => {
      const newMoves = remainingMoves.map((move, index) => {
        const { face, rotation } = parseMove(move);
        const targetStep = currentStep + index + 1;
        
        return {
          face,
          rotation,
          targetStep,
          stepUpdate: () => setCurrentStep(targetStep)
        };
      });
      
      return [...prev, ...newMoves];
    });
    
    autoPlayTimerRef.current = true; // 자동 재생 활성화 플래그
  };

  const handleReset = () => {
    if (autoPlayTimerRef.current) {
      autoPlayTimerRef.current = null;
    }
    setCurrentStep(0);
    setMoveQueue([]); // 큐 초기화
    isPendingRef.current = false; // 플래그 해제
    onReset();
  };
  
  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      if (autoPlayTimerRef.current) {
        autoPlayTimerRef.current = null;
      }
    };
  }, []);

  return (
    <div className="solution-viewer">
      <div className="solution-header">
        <h3>🎯 큐브 해법</h3>
        <div className="solution-stats">
          <span className="stat-badge">총 {stats.total}회 이동</span>
          <span className="stat-badge">현재: {currentStep}/{moveList.length}</span>
        </div>
      </div>

      <div className="solution-progress">
        <div 
          className="progress-bar"
          style={{ width: `${(currentStep / moveList.length) * 100}%` }}
        />
      </div>

      <div className="solution-controls">
        <button 
          className="control-btn"
          onClick={handlePrevStep}
          disabled={currentStep === 0 || isProcessing}
          title="이전 단계"
        >
          ⏮️ 이전
        </button>

        <button 
          className="control-btn primary"
          onClick={handleAutoPlay}
          disabled={isProcessing && !autoPlayTimerRef.current}
          title={autoPlayTimerRef.current ? "일시정지" : "자동 실행"}
        >
          {autoPlayTimerRef.current ? "⏸️ 정지" : "▶️ 자동"}
        </button>

        <button 
          className="control-btn"
          onClick={handleNextStep}
          disabled={currentStep >= moveList.length || isProcessing}
          title="다음 단계"
        >
          다음 ⏭️
        </button>

        <button 
          className="control-btn danger"
          onClick={handleReset}
          disabled={isProcessing}
          title="초기화"
        >
          🔄 초기화
        </button>
      </div>

      <div className="solution-moves">
        <h4>📋 이동 순서</h4>
        <div className="moves-list">
          {moveList.map((move, index) => {
            const isActive = index === currentStep;
            const isPast = index < currentStep;
            const isFuture = index > currentStep;
            
            return (
              <div
                key={index}
                ref={el => moveItemsRef.current[index] = el}
                className={`move-item ${isActive ? 'active' : ''} ${isPast ? 'completed' : ''} ${isFuture ? 'future' : ''}`}
              >
                <span className="move-number">{index + 1}.</span>
                <span className="move-notation">{toKoreanNotation(move)}</span>
                <span className="move-original">({move})</span>
                {isActive && <span className="move-indicator">← 현재</span>}
                {isPast && <span className="move-check">✓</span>}
              </div>
            );
          })}
        </div>
      </div>

      <div className="solution-stats-detail">
        <h4>면별 이동 횟수</h4>
        <div className="stats-grid">
          {Object.entries(stats.byFace).map(([face, count]) => {
            const faceNames = {
              'U': '위',
              'D': '아래',
              'R': '오른쪽',
              'L': '왼쪽',
              'F': '앞',
              'B': '뒤'
            };
            return (
              <div key={face} className="stat-item">
                <span className="stat-face">{faceNames[face] || face}</span>
                <span className="stat-count">{count}회</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default SolutionViewer;