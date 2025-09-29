import React, { useMemo } from 'react'

// 루빅스 큐브의 6가지 색상
const COLORS = {
  red: '#C41E3A',
  green: '#009E60',
  blue: '#0051BA',
  orange: '#FF5800',
  yellow: '#FFD500',
  white: '#FFFFFF',
  black: '#212121'
}

// 전개도 레이아웃 (십자형)
//     [U]
// [L] [F] [R] [B]
//     [D]
const NET_LAYOUT = [
  { face: 'U', x: 1, y: 0 }, // Top
  { face: 'L', x: 0, y: 1 }, // Left
  { face: 'F', x: 1, y: 1 }, // Front
  { face: 'R', x: 2, y: 1 }, // Right
  { face: 'B', x: 3, y: 1 }, // Back
  { face: 'D', x: 1, y: 2 }  // Bottom
]

function CubeNet({ pieces, cubeSize = 200, colorEditMode = false, selectedCell = null, onCellSelect }) {
  // 각 면의 색상 데이터 생성
  const faceData = useMemo(() => {
    // 각 면별로 3x3 격자 생성
    const faces = {
      U: Array(9).fill(null), // Top (White)
      D: Array(9).fill(null), // Bottom (Yellow)
      F: Array(9).fill(null), // Front (Green)
      B: Array(9).fill(null), // Back (Blue)
      L: Array(9).fill(null), // Left (Orange)
      R: Array(9).fill(null)  // Right (Red)
    }

    // 조각들의 위치와 색상 정보로 면 데이터 채우기
    pieces.forEach(piece => {
      const [x, y, z] = piece.position
      const [rightColor, leftColor, topColor, bottomColor, frontColor, backColor] = piece.faceColors

      // 격자 인덱스 계산 (각 면에서 0-8)
      const getGridIndex = (u, v) => (1 - v) * 3 + (u + 1)

      // 각 면별로 색상 배치
      if (y === 1) { // Top face (U)
        const u = x // -1, 0, 1 -> 0, 1, 2
        const v = -z // -1, 0, 1 -> 1, 0, -1 -> 2, 1, 0
        const index = getGridIndex(u, v)
        faces.U[index] = topColor
      }
      
      if (y === -1) { // Bottom face (D)
        const u = x // -1, 0, 1 -> 0, 1, 2
        const v = z // -1, 0, 1 -> 0, 1, 2
        const index = getGridIndex(u, v)
        faces.D[index] = bottomColor
      }
      
      if (z === 1) { // Front face (F)
        const u = x // -1, 0, 1 -> 0, 1, 2
        const v = y // -1, 0, 1 -> 0, 1, 2
        const index = getGridIndex(u, v)
        faces.F[index] = frontColor
      }
      
      if (z === -1) { // Back face (B)
        const u = -x // 1, 0, -1 -> -1, 0, 1 -> 0, 1, 2
        const v = y // -1, 0, 1 -> 0, 1, 2
        const index = getGridIndex(u, v)
        faces.B[index] = backColor
      }
      
      if (x === -1) { // Left face (L)
        const u = z // -1, 0, 1 -> 0, 1, 2
        const v = y // -1, 0, 1 -> 0, 1, 2
        const index = getGridIndex(u, v)
        faces.L[index] = leftColor
      }
      
      if (x === 1) { // Right face (R)
        const u = -z // 1, 0, -1 -> -1, 0, 1 -> 0, 1, 2
        const v = y // -1, 0, 1 -> 0, 1, 2
        const index = getGridIndex(u, v)
        faces.R[index] = rightColor
      }
    })

    return faces
  }, [pieces])

  const cellSize = cubeSize / 3

  return (
    <div className="cube-net" style={{ padding: '20px' }}>
      <svg 
        width={cubeSize * 4} 
        height={cubeSize * 3} 
        viewBox={`0 0 ${cubeSize * 4} ${cubeSize * 3}`}
        style={{ border: '1px solid #444' }}
      >
        {NET_LAYOUT.map(({ face, x, y }) => (
          <g key={face} transform={`translate(${x * cubeSize}, ${y * cubeSize})`}>
            {/* 면 배경 */}
            <rect 
              width={cubeSize} 
              height={cubeSize} 
              fill="#333" 
              stroke="#666" 
              strokeWidth={2}
            />
            
            {/* 3x3 격자 */}
            {faceData[face].map((color, index) => {
              const row = Math.floor(index / 3)
              const col = index % 3
              
              // 색상 변환: 숫자 -> 헥스 색상
              let displayColor = COLORS.black
              if (color !== null) {
                const hexString = `#${color.toString(16).padStart(6, '0').toUpperCase()}`
                // 알려진 색상과 매칭
                const colorMatch = Object.entries(COLORS).find(([_, value]) => 
                  value.toUpperCase() === hexString
                )
                displayColor = colorMatch ? colorMatch[1] : hexString
              }
              
              // 선택된 셀인지 확인
              const isSelected = selectedCell && 
                selectedCell.face === face && 
                selectedCell.gridIndex === index

              return (
                <rect
                  key={index}
                  x={col * cellSize}
                  y={row * cellSize}
                  width={cellSize}
                  height={cellSize}
                  fill={displayColor}
                  stroke={isSelected ? "#FFD700" : "#222"}
                  strokeWidth={isSelected ? 3 : 1}
                  style={{ 
                    cursor: colorEditMode ? 'pointer' : 'default',
                    filter: isSelected ? 'brightness(1.2)' : 'none'
                  }}
                  onClick={colorEditMode && onCellSelect ? () => {
                    onCellSelect(face, row, col)
                  } : undefined}
                />
              )
            })}
            
            {/* 면 라벨 */}
            <text
              x={cubeSize / 2}
              y={cubeSize - 10}
              textAnchor="middle"
              fill="#ccc"
              fontSize="16"
              fontWeight="bold"
            >
              {face}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

export default CubeNet