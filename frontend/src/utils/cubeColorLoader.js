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

/**
 * 16진수 색상 값을 색상 문자로 변환 (역변환)
 * @param {number} hexColor - 16진수 색상 값
 * @returns {string} 색상 문자 (r, g, b, o, y, w)
 */
export const convertHexToColorChar = (hexColor) => {
  const colorEntry = Object.entries(COLOR_MAPPING).find(([, hex]) => hex === hexColor)
  return colorEntry ? colorEntry[0] : 'black'
}

/**
 * 3D 좌표에서 면 이름과 면 내 좌표를 찾기
 * 
 * 3D 큐브 좌표계: x(좌-1우+1), y(하-1상+1), z(뒤-1앞+1)
 * 백엔드 큐브: 각 면을 정면에서 봤을 때의 2D 배열 [row][col]
 * 
 * @param {number} x - X 좌표 (-1: 왼쪽, 0: 중간, 1: 오른쪽)
 * @param {number} y - Y 좌표 (-1: 아래, 0: 중간, 1: 위)
 * @param {number} z - Z 좌표 (-1: 뒤, 0: 중간, 1: 앞)
 * @returns {Array<{face: string, row: number, col: number}>} 해당 좌표가 속한 면들
 */
const get3DCoordFaceInfo = (x, y, z) => {
  const faceInfos = []
  
  // U면 (위쪽, y=1): 위에서 내려다본 시점
  // row: z축 (-1→0→1 = 뒤→중→앞 = row 0→1→2)
  // col: x축 (-1→0→1 = 좌→중→우 = col 0→1→2)
  if (y === 1) {
    faceInfos.push({
      face: 'U',
      row: z + 1,     // z: -1,0,1 -> row: 0,1,2
      col: x + 1      // x: -1,0,1 -> col: 0,1,2
    })
  }
  
  // D면 (아래쪽, y=-1): 아래에서 올려다본 시점
  // row: z축 (1→0→-1 = 앞→중→뒤 = row 0→1→2)
  // col: x축 (-1→0→1 = 좌→중→우 = col 0→1→2)
  if (y === -1) {
    faceInfos.push({
      face: 'D',
      row: -z + 1,    // z: 1,0,-1 -> row: 0,1,2
      col: x + 1      // x: -1,0,1 -> col: 0,1,2
    })
  }
  
  // R면 (오른쪽, x=1): 오른쪽에서 왼쪽으로 본 시점
  // row: y축 (1→0→-1 = 위→중→아래 = row 0→1→2)
  // col: z축 (1→0→-1 = 앞→중→뒤 = col 0→1→2)
  if (x === 1) {
    faceInfos.push({
      face: 'R',
      row: -y + 1,    // y: 1,0,-1 -> row: 0,1,2
      col: -z + 1     // z: 1,0,-1 -> col: 0,1,2
    })
  }
  
  // L면 (왼쪽, x=-1): 왼쪽에서 오른쪽으로 본 시점
  // row: y축 (1→0→-1 = 위→중→아래 = row 0→1→2)
  // col: z축 (-1→0→1 = 뒤→중→앞 = col 0→1→2)
  if (x === -1) {
    faceInfos.push({
      face: 'L',
      row: -y + 1,    // y: 1,0,-1 -> row: 0,1,2
      col: z + 1      // z: -1,0,1 -> col: 0,1,2
    })
  }
  
  // F면 (앞쪽, z=1): 정면에서 본 시점
  // row: y축 (1→0→-1 = 위→중→아래 = row 0→1→2)
  // col: x축 (-1→0→1 = 좌→중→우 = col 0→1→2)
  if (z === 1) {
    faceInfos.push({
      face: 'F',
      row: -y + 1,    // y: 1,0,-1 -> row: 0,1,2
      col: x + 1      // x: -1,0,1 -> col: 0,1,2
    })
  }
  
  // B면 (뒤쪽, z=-1): 뒤에서 앞으로 본 시점
  // row: y축 (1→0→-1 = 위→중→아래 = row 0→1→2)
  // col: x축 (1→0→-1 = 우→중→좌 = col 0→1→2) [거울상]
  if (z === -1) {
    faceInfos.push({
      face: 'B',
      row: -y + 1,    // y: 1,0,-1 -> row: 0,1,2
      col: -x + 1     // x: 1,0,-1 -> col: 0,1,2
    })
  }
  
  return faceInfos
}

/**
 * 3D 큐브 조각 배열을 백엔드 JSON 형식으로 변환
 * @param {Array} pieces - 큐브 조각 배열
 * @returns {Object} 백엔드 형식 큐브 데이터 {U: [[...]], R: [[...]], F: [[...]], D: [[...]], L: [[...]], B: [[...]]}
 */
export const convertCubePiecesToJson = (pieces) => {
  // 6개 면 초기화 (Kociemba 순서: URFDLB)
  const cubeData = {
    U: [['', '', ''], ['', '', ''], ['', '', '']],
    R: [['', '', ''], ['', '', ''], ['', '', '']],
    F: [['', '', ''], ['', '', ''], ['', '', '']],
    D: [['', '', ''], ['', '', ''], ['', '', '']],
    L: [['', '', ''], ['', '', ''], ['', '', '']],
    B: [['', '', ''], ['', '', ''], ['', '', '']]
  }
  
  console.log('🔄 큐브 조각 → JSON 변환 시작 (총', pieces.length, '개 조각)')
  
  // 중심 조각 먼저 확인 (0,0,0 제외한 면 중심)
  console.log('🎯 3D 큐브 면 중심 조각 색상:')
  const centerPieces = [
    { pos: [0, 1, 0], name: 'U (위)', faceIndex: FACE_INDEX_MAPPING['U'] },
    { pos: [0, -1, 0], name: 'D (아래)', faceIndex: FACE_INDEX_MAPPING['D'] },
    { pos: [1, 0, 0], name: 'R (오른쪽)', faceIndex: FACE_INDEX_MAPPING['R'] },
    { pos: [-1, 0, 0], name: 'L (왼쪽)', faceIndex: FACE_INDEX_MAPPING['L'] },
    { pos: [0, 0, 1], name: 'F (앞)', faceIndex: FACE_INDEX_MAPPING['F'] },
    { pos: [0, 0, -1], name: 'B (뒤)', faceIndex: FACE_INDEX_MAPPING['B'] }
  ]
  
  centerPieces.forEach(({ pos, name, faceIndex }) => {
    const piece = pieces.find(p => 
      p.position[0] === pos[0] && 
      p.position[1] === pos[1] && 
      p.position[2] === pos[2]
    )
    if (piece) {
      const hexColor = piece.faceColors[faceIndex]
      const colorChar = convertHexToColorChar(hexColor)
      console.log(`  ${name} [${pos}]: ${colorChar} (hex: 0x${hexColor.toString(16).toUpperCase()})`)
    }
  })
  
  // 각 조각의 색상을 해당 면에 배치
  pieces.forEach(piece => {
    const [x, y, z] = piece.position
    const faceInfos = get3DCoordFaceInfo(x, y, z)
    
    // R면 전체 엣지 조각들의 상세 정보 출력
    if (x === 1 && (Math.abs(y) === 1 || Math.abs(z) === 1) && !(Math.abs(y) === 1 && Math.abs(z) === 1)) {
      const colors = piece.faceColors.map((hex, idx) => {
        const char = convertHexToColorChar(hex)
        const names = ['R', 'L', 'U', 'D', 'F', 'B']
        return `${names[idx]}:${char}`
      })
      console.log(`  🔍 [${x},${y},${z}] (R면 엣지) faceColors: [${colors.join(', ')}]`)
    }
    
    // F면 전체 엣지 조각들도 출력
    if (z === 1 && (Math.abs(x) === 1 || Math.abs(y) === 1) && !(Math.abs(x) === 1 && Math.abs(y) === 1)) {
      const colors = piece.faceColors.map((hex, idx) => {
        const char = convertHexToColorChar(hex)
        const names = ['R', 'L', 'U', 'D', 'F', 'B']
        return `${names[idx]}:${char}`
      })
      console.log(`  🔍 [${x},${y},${z}] (F면 엣지) faceColors: [${colors.join(', ')}]`)
    }
    
    faceInfos.forEach(({ face, row, col }) => {
      const faceIndex = FACE_INDEX_MAPPING[face]
      const hexColor = piece.faceColors[faceIndex]
      const colorChar = convertHexToColorChar(hexColor)
      
      // 'black'은 제외 (내부 면)
      if (colorChar !== 'black') {
        cubeData[face][row][col] = colorChar
        // console.log(`  [${x},${y},${z}] → ${face}[${row}][${col}] = ${colorChar} (faceIndex=${faceIndex})`)
      }
    })
  })
  
  // 중심 색상 확인
  console.log('📊 변환된 큐브 중심 색상:')
  console.log(`  U 중심: ${cubeData.U[1][1]} (예상: w)`)
  console.log(`  R 중심: ${cubeData.R[1][1]} (예상: r)`)
  console.log(`  F 중심: ${cubeData.F[1][1]} (예상: g)`)
  console.log(`  D 중심: ${cubeData.D[1][1]} (예상: y)`)
  console.log(`  L 중심: ${cubeData.L[1][1]} (예상: o)`)
  console.log(`  B 중심: ${cubeData.B[1][1]} (예상: b)`)
  
  return cubeData
}

export default {
  loadCubeColors,
  convertFaceCoordTo3D,
  convertColorCharToHex,
  convertHexToColorChar,
  convertJsonToCubePieces,
  convertCubePiecesToJson,
  loadAndConvertCubeData,
  COLOR_MAPPING,
  FACE_MAPPING,
  FACE_INDEX_MAPPING
}