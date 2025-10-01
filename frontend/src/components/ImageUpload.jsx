import React, { useState, useRef } from 'react'
import './ImageUpload.css'

// 전개도 레이아웃 (십자형)
//     [U]
// [L] [F] [R] [B]
//     [D]
const NET_LAYOUT = [
  { face: 'U', x: 1, y: 0, name: '윗면' }, // Top
  { face: 'L', x: 0, y: 1, name: '왼면' }, // Left
  { face: 'F', x: 1, y: 1, name: '앞면' }, // Front
  { face: 'R', x: 2, y: 1, name: '오른면' }, // Right
  { face: 'B', x: 3, y: 1, name: '뒷면' }, // Back
  { face: 'D', x: 1, y: 2, name: '아랫면' }  // Bottom
]

function ImageUpload({ onImageUpload, uploadedImages = {} }) {
  const [selectedFace, setSelectedFace] = useState(null)
  const [dragOver, setDragOver] = useState(null)
  const fileInputRef = useRef()

  // 면 클릭 핸들러
  const handleFaceClick = (face) => {
    setSelectedFace(face)
    // 파일 선택 다이얼로그 열기
    if (fileInputRef.current) {
      fileInputRef.current.setAttribute('data-face', face)
      fileInputRef.current.click()
    }
  }

  // 파일 선택 핸들러
  const handleFileSelect = (event) => {
    const file = event.target.files[0]
    const face = event.target.getAttribute('data-face')
    
    if (file && face) {
      // 이미지 파일 유효성 검사
      if (!file.type.startsWith('image/')) {
        alert('이미지 파일만 업로드할 수 있습니다.')
        return
      }

      // 파일 크기 제한 (5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('파일 크기는 5MB 이하여야 합니다.')
        return
      }

      // 이미지 미리보기를 위한 URL 생성
      const imageUrl = URL.createObjectURL(file)
      
      // 부모 컴포넌트에 이미지 정보 전달
      onImageUpload(face, {
        file,
        url: imageUrl,
        name: file.name,
        size: file.size,
        type: file.type
      })
    }

    // 파일 입력 초기화
    event.target.value = ''
  }

  // 드래그 앤 드롭 핸들러
  const handleDragOver = (event, face) => {
    event.preventDefault()
    setDragOver(face)
  }

  const handleDragLeave = () => {
    setDragOver(null)
  }

  const handleDrop = (event, face) => {
    event.preventDefault()
    setDragOver(null)

    const files = event.dataTransfer.files
    if (files.length > 0) {
      const file = files[0]
      
      if (!file.type.startsWith('image/')) {
        alert('이미지 파일만 업로드할 수 있습니다.')
        return
      }

      if (file.size > 5 * 1024 * 1024) {
        alert('파일 크기는 5MB 이하여야 합니다.')
        return
      }

      const imageUrl = URL.createObjectURL(file)
      
      onImageUpload(face, {
        file,
        url: imageUrl,
        name: file.name,
        size: file.size,
        type: file.type
      })
    }
  }

  // 이미지 제거 핸들러
  const handleRemoveImage = (face, event) => {
    event.stopPropagation()
    onImageUpload(face, null)
  }

  const faceSize = 120

  return (
    <div className="image-upload-container">
      <h2>이미지 업로드</h2>
      <p className="upload-instruction">
        각 면을 클릭하거나 드래그 앤 드롭으로 이미지를 업로드하세요
      </p>
      
      <div className="cube-net-upload">
        <svg 
          width={faceSize * 4} 
          height={faceSize * 3}
          className="net-svg"
        >
          {NET_LAYOUT.map(({ face, x, y, name }) => {
            const uploadedImage = uploadedImages[face]
            const isSelected = selectedFace === face
            const isDragOver = dragOver === face

            return (
              <g key={face}>
                {/* 면 배경 */}
                <rect
                  x={x * faceSize}
                  y={y * faceSize}
                  width={faceSize}
                  height={faceSize}
                  className={`face-area ${isSelected ? 'selected' : ''} ${isDragOver ? 'drag-over' : ''}`}
                  onClick={() => handleFaceClick(face)}
                  onDragOver={(e) => handleDragOver(e, face)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, face)}
                />
                
                {/* 이미지 미리보기 */}
                {uploadedImage && (
                  <>
                    <defs>
                      <clipPath id={`clip-${face}`}>
                        <rect
                          x={x * faceSize + 2}
                          y={y * faceSize + 2}
                          width={faceSize - 4}
                          height={faceSize - 4}
                        />
                      </clipPath>
                    </defs>
                    <image
                      x={x * faceSize + 2}
                      y={y * faceSize + 2}
                      width={faceSize - 4}
                      height={faceSize - 4}
                      href={uploadedImage.url}
                      clipPath={`url(#clip-${face})`}
                      className="face-image"
                    />
                    {/* 제거 버튼 */}
                    <circle
                      cx={x * faceSize + faceSize - 15}
                      cy={y * faceSize + 15}
                      r="10"
                      className="remove-button"
                      onClick={(e) => handleRemoveImage(face, e)}
                    />
                    <text
                      x={x * faceSize + faceSize - 15}
                      y={y * faceSize + 20}
                      className="remove-icon"
                      onClick={(e) => handleRemoveImage(face, e)}
                    >
                      ✕
                    </text>
                  </>
                )}
                
                {/* 면 라벨 */}
                <text
                  x={x * faceSize + faceSize / 2}
                  y={y * faceSize + (uploadedImage ? faceSize - 10 : faceSize / 2)}
                  className="face-label"
                  textAnchor="middle"
                  dominantBaseline="middle"
                >
                  {uploadedImage ? name : `${face} - ${name}`}
                </text>
                
                {/* 업로드 아이콘 (이미지가 없을 때) */}
                {!uploadedImage && (
                  <text
                    x={x * faceSize + faceSize / 2}
                    y={y * faceSize + faceSize / 2 - 20}
                    className="upload-icon"
                    textAnchor="middle"
                    dominantBaseline="middle"
                  >
                    📁
                  </text>
                )}
              </g>
            )
          })}
        </svg>
      </div>

      {/* 업로드된 이미지 정보 */}
      {Object.keys(uploadedImages).length > 0 && (
        <div className="uploaded-images-info">
          <h3>업로드된 이미지</h3>
          <div className="image-list">
            {Object.entries(uploadedImages).map(([face, imageData]) => (
              <div key={face} className="image-info-item">
                <span className="face-name">{face}면:</span>
                <span className="image-name">{imageData.name}</span>
                <span className="image-size">({(imageData.size / 1024).toFixed(1)}KB)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 숨겨진 파일 입력 */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />
    </div>
  )
}

export default ImageUpload