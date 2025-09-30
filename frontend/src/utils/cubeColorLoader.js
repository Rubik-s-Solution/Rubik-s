// 큐브 색상 데이터를 로드하고 처리하는 유틸리티

// 색상 문자 매핑 (cube_colors.json의 문자를 실제 색상으로 변환)
const COLOR_MAPPING = {
  'r': 0xC41E3A, // red
  'g': 0x009E60, // green  
  'b': 0x0051BA, // blue
  'o': 0xFF5800, // orange
  'y': 0xFFD500, // yellow
  'w': 0xFFFFFF, // white
  'black': 0x212121 // 기본 검정색
}

// 면 매핑 (JSON의 면 이름을 3D 좌표계로 변환)
// JSON 형식: F(Front), B(Back), L(Left), R(Right), U(Up), D(Down)
// 3D 좌표계: x축(Left/Right), y축(Down/Up), z축(Back/Front)
const FACE_MAPPING = {
  'F': { axis: 'z', value: 1 },  // Front face (+Z)
  'B': { axis: 'z', value: -1 }, // Back face (-Z)
  'L': { axis: 'x', value: -1 }, // Left face (-X)
  'R': { axis: 'x', value: 1 },  // Right face (+X)
  'U': { axis: 'y', value: 1 },  // Up face (+Y)
  'D': { axis: 'y', value: -1 }  // Down face (-Y)
}

// 면 인덱스 매핑 (RubiksCube 컴포넌트의 faceColors 배열 인덱스)
const FACE_INDEX_MAPPING = {
  'R': 0, // Right face
  'L': 1, // Left face  
  'U': 2, // Up face
  'D': 3, // Down face
  'F': 4, // Front face
  'B': 5  // Back face
}

/**
 * 큐브 색상 JSON 파일을 로드합니다
 * @param {string} filePath - JSON 파일 경로
 * @returns {Promise<Object>} 큐브 색상 데이터
 */
export const loadCubeColors = async (filePath = '/cube_debug/cube_colors.json') => {
  try {
    const response = await fetch(filePath)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const cubeData = await response.json()
    return cubeData
  } catch (error) {
    console.error('큐브 색상 데이터를 로드하는데 실패했습니다:', error)
    throw error
  }
}

/**
 * JSON 면 좌표를 3D 큐브 조각 좌표로 변환
 * @param {string} face - 면 이름 (F, B, L, R, U, D)
 * @param {number} row - 행 인덱스 (0-2)
 * @param {number} col - 열 인덱스 (0-2)
 * @returns {Object} 3D 좌표 {x, y, z}
 */
export const convertFaceCoordTo3D = (face, row, col) => {
  // 면 중심을 기준으로 한 좌표계 변환
  // row, col: 0-2 범위를 -1~1 범위로 변환
  
  const faceInfo = FACE_MAPPING[face]
  if (!faceInfo) {
    throw new Error(`Unknown face: ${face}`)
  }

  let x, y, z
  
  switch (face) {
    case 'F': // Front face (+Z)
      x = col - 1    // 0,1,2 -> -1,0,1
      y = 1 - row    // 0,1,2 -> 1,0,-1 (Y축 뒤집기)
      z = 1
      break
      
    case 'B': // Back face (-Z)  
      x = 1 - col    // 0,1,2 -> 1,0,-1 (X축 뒤집기)
      y = 1 - row    // 0,1,2 -> 1,0,-1 (Y축 뒤집기)
      z = -1
      break
      
    case 'L': // Left face (-X)
      x = -1
      y = 1 - row    // 0,1,2 -> 1,0,-1 (Y축 뒤집기)
      z = 1 - col    // 0,1,2 -> 1,0,-1 (Z축 뒤집기)
      break
      
    case 'R': // Right face (+X)
      x = 1
      y = 1 - row    // 0,1,2 -> 1,0,-1 (Y축 뒤집기)  
      z = col - 1    // 0,1,2 -> -1,0,1
      break
      
    case 'U': // Up face (+Y)
      x = col - 1    // 0,1,2 -> -1,0,1
      y = 1
      z = row - 1    // 0,1,2 -> -1,0,1
      break
      
    case 'D': // Down face (-Y)
      x = col - 1    // 0,1,2 -> -1,0,1
      y = -1  
      z = 1 - row    // 0,1,2 -> 1,0,-1 (Z축 뒤집기)
      break
      
    default:
      throw new Error(`Unsupported face: ${face}`)
  }
  
  return { x, y, z }
}

/**
 * 색상 문자를 16진수 색상 값으로 변환
 * @param {string} colorChar - 색상 문자 (r, g, b, o, y, w)
 * @returns {number} 16진수 색상 값
 */
export const convertColorCharToHex = (colorChar) => {
  return COLOR_MAPPING[colorChar] || COLOR_MAPPING['black']
}

/**
 * JSON 큐브 데이터를 3D 큐브 조각 배열로 변환
 * @param {Object} cubeData - JSON 큐브 색상 데이터
 * @returns {Array} 변환된 큐브 조각 배열
 */
export const convertJsonToCubePieces = (cubeData) => {
  const pieces = []
  
  // 26개의 큐브 조각 생성 (중앙 조각 제외)
  for (let x = -1; x <= 1; x++) {
    for (let y = -1; y <= 1; y++) {
      for (let z = -1; z <= 1; z++) {
        // 중앙 조각 제외
        if (x === 0 && y === 0 && z === 0) continue
        
        // 기본 검정색으로 초기화
        const faceColors = [
          COLOR_MAPPING['black'], // Right (+X)
          COLOR_MAPPING['black'], // Left (-X)
          COLOR_MAPPING['black'], // Top (+Y)
          COLOR_MAPPING['black'], // Bottom (-Y)
          COLOR_MAPPING['black'], // Front (+Z)
          COLOR_MAPPING['black']  // Back (-Z)
        ]
        
        pieces.push({
          id: `${x}_${y}_${z}`,
          position: [x, y, z],
          faceColors: faceColors
        })
      }
    }
  }
  
  // JSON 데이터로부터 각 면의 색상 적용
  Object.keys(cubeData).forEach(face => {
    const faceIndex = FACE_INDEX_MAPPING[face]
    if (faceIndex === undefined) return
    
    const faceData = cubeData[face]
    
    // 각 면의 3x3 격자 처리
    for (let row = 0; row < 3; row++) {
      for (let col = 0; col < 3; col++) {
        const colorChar = faceData[row][col]
        const color = convertColorCharToHex(colorChar)
        const coord3D = convertFaceCoordTo3D(face, row, col)
        
        // 해당 위치의 큐브 조각 찾기
        const piece = pieces.find(p => 
          p.position[0] === coord3D.x && 
          p.position[1] === coord3D.y && 
          p.position[2] === coord3D.z
        )
        
        if (piece) {
          piece.faceColors[faceIndex] = color
        }
      }
    }
  })
  
  return pieces
}

/**
 * 큐브 색상 데이터를 로드하여 적용 가능한 형태로 변환
 * @param {string} filePath - JSON 파일 경로  
 * @returns {Promise<Array>} 변환된 큐브 조각 배열
 */
export const loadAndConvertCubeData = async (filePath) => {
  try {
    const cubeData = await loadCubeColors(filePath)
    const pieces = convertJsonToCubePieces(cubeData)
    return pieces
  } catch (error) {
    console.error('큐브 데이터 변환 실패:', error)
    throw error
  }
}

export default {
  loadCubeColors,
  convertFaceCoordTo3D,
  convertColorCharToHex,
  convertJsonToCubePieces,
  loadAndConvertCubeData,
  COLOR_MAPPING,
  FACE_MAPPING,
  FACE_INDEX_MAPPING
}