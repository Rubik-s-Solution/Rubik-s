/**
 * 루빅스 큐브 해법 적용 유틸리티
 */

/**
 * Kociemba 해법 문자열을 개별 이동으로 파싱
 * @param {string} solution - 예: "D R2 F2 D' L2 ..."
 * @returns {Array<string>} - 예: ["D", "R2", "F2", "D'", "L2", ...]
 */
export function parseSolution(solution) {
  if (!solution || typeof solution !== 'string') {
    return []
  }
  return solution.trim().split(/\s+/).filter(move => move.length > 0)
}

/**
 * 이동 문자열을 파싱하여 면과 회전 정보 추출
 * @param {string} move - 예: "R2", "U'", "F"
 * @returns {Object} - { face: "R", rotation: 2 } 또는 { face: "U", rotation: -1 }
 */
export function parseMove(move) {
  const face = move[0] // U, D, L, R, F, B
  let rotation = 1 // 기본 시계방향 90도
  
  if (move.includes("2")) {
    rotation = 2 // 180도
  } else if (move.includes("'") || move.includes("'")) {
    rotation = -1 // 반시계방향 90도
  }
  
  return { face, rotation }
}

/**
 * 큐브 상태를 Kociemba 형식으로 변환
 * @param {Object} cubeData - 프론트엔드 큐브 데이터 { U1: "U", U2: "U", ... }
 * @returns {string} - Kociemba 형식 문자열 (54자)
 */
export function cubeToKociembaString(cubeData) {
  const order = ['U', 'R', 'F', 'D', 'L', 'B']
  let result = ''
  
  for (const face of order) {
    for (let i = 1; i <= 9; i++) {
      const key = `${face}${i}`
      result += cubeData[key] || '?'
    }
  }
  
  return result
}

/**
 * Kociemba 문자열을 프론트엔드 큐브 형식으로 변환
 * @param {string} kociembaString - 54자 문자열
 * @returns {Object} - { U1: "U", U2: "U", ... }
 */
export function kociembaStringToCube(kociembaString) {
  if (kociembaString.length !== 54) {
    throw new Error(`잘못된 Kociemba 문자열 길이: ${kociembaString.length}`)
  }
  
  const cubeData = {}
  const faces = ['U', 'R', 'F', 'D', 'L', 'B']
  let index = 0
  
  for (const face of faces) {
    for (let i = 1; i <= 9; i++) {
      cubeData[`${face}${i}`] = kociembaString[index]
      index++
    }
  }
  
  return cubeData
}

/**
 * 큐브 상태가 해결되었는지 확인
 * @param {Object} cubeData - 프론트엔드 큐브 데이터
 * @returns {boolean}
 */
export function isCubeSolved(cubeData) {
  const faces = ['U', 'R', 'F', 'D', 'L', 'B']
  
  for (const face of faces) {
    const firstColor = cubeData[`${face}1`]
    
    for (let i = 1; i <= 9; i++) {
      if (cubeData[`${face}${i}`] !== firstColor) {
        return false
      }
    }
  }
  
  return true
}

/**
 * 해법 통계 계산
 * @param {Array<string>} moves - 이동 배열
 * @returns {Object} - { total: 20, byFace: { U: 5, R: 4, ... } }
 */
export function calculateSolutionStats(moves) {
  const stats = {
    total: moves.length,
    byFace: {}
  }
  
  for (const move of moves) {
    const { face } = parseMove(move)
    stats.byFace[face] = (stats.byFace[face] || 0) + 1
  }
  
  return stats
}

/**
 * 해법을 역순으로 변환 (큐브를 원래 상태로 되돌리기)
 * @param {Array<string>} moves - 원본 이동 배열
 * @returns {Array<string>} - 역순 이동 배열
 */
export function reverseSolution(moves) {
  return moves.reverse().map(move => {
    const { face, rotation } = parseMove(move)
    
    if (rotation === 2) {
      return `${face}2` // 180도는 그대로
    } else if (rotation === 1) {
      return `${face}'` // 시계방향 → 반시계방향
    } else {
      return face // 반시계방향 → 시계방향
    }
  })
}

/**
 * 해법을 단계별로 그룹화
 * @param {Array<string>} moves - 이동 배열
 * @param {number} groupSize - 그룹 크기 (기본 5)
 * @returns {Array<Array<string>>} - 그룹화된 이동 배열
 */
export function groupMoves(moves, groupSize = 5) {
  const groups = []
  
  for (let i = 0; i < moves.length; i += groupSize) {
    groups.push(moves.slice(i, i + groupSize))
  }
  
  return groups
}
