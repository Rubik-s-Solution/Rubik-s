import React, { useState, useRef, useEffect } from 'react'
import { uploadImageToBackend, getCubeImages, deleteCubeImage, getImageUrl, checkApiHealth, analyzeCubeImages } from '../utils/imageApi'
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

function ImageUpload({ onImageUpload, uploadedImages = {}, onAnalysisComplete }) {
  const [selectedFace, setSelectedFace] = useState(null)
  const [dragOver, setDragOver] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [uploadStatus, setUploadStatus] = useState({ type: null, message: '' })
  const [backendImages, setBackendImages] = useState({})
  const [apiHealthy, setApiHealthy] = useState(false)
  const fileInputRef = useRef()

  // 컴포넌트 마운트 시 백엔드 상태 확인 및 이미지 로드
  useEffect(() => {
    checkBackendHealth()
    loadBackendImages()
  }, [])

  // 백엔드 API 상태 확인
  const checkBackendHealth = async () => {
    try {
      await checkApiHealth()
      setApiHealthy(true)
      setUploadStatus({ type: 'success', message: '백엔드 서버가 연결되었습니다.' })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
    } catch (error) {
      setApiHealthy(false)
      setUploadStatus({ type: 'error', message: '백엔드 서버에 연결할 수 없습니다. (로컬 업로드만 가능)' })
    }
  }

  // 백엔드에서 이미지 정보 로드
  const loadBackendImages = async () => {
    try {
      const result = await getCubeImages()
      setBackendImages(result.data || {})
    } catch (error) {
      console.log('백엔드 이미지 로드 실패 (정상 - 서버가 없을 수 있음):', error.message)
    }
  }

  // 면 클릭 핸들러
  const handleFaceClick = (face) => {
    if (uploading) return
    
    setSelectedFace(face)
    // 파일 선택 다이얼로그 열기
    if (fileInputRef.current) {
      fileInputRef.current.setAttribute('data-face', face)
      fileInputRef.current.click()
    }
  }

  // 파일 선택 핸들러
  const handleFileSelect = async (event) => {
    const file = event.target.files[0]
    const face = event.target.getAttribute('data-face')
    
    if (file && face) {
      await processImageUpload(file, face)
    }

    // 파일 입력 초기화
    event.target.value = ''
  }

  // 이미지 업로드 처리
  const processImageUpload = async (file, face) => {
    // 이미지 파일 유효성 검사
    if (!file.type.startsWith('image/')) {
      setUploadStatus({ type: 'error', message: '이미지 파일만 업로드할 수 있습니다.' })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
      return
    }

    // 파일 크기 제한 (5MB)
    if (file.size > 10 * 1024 * 1024) {
      setUploadStatus({ type: 'error', message: '파일 크기는 5MB 이하여야 합니다.' })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
      return
    }

    setUploading(true)
    setUploadStatus({ type: 'info', message: `${face} 면에 이미지를 업로드 중입니다...` })

    try {
      // 백엔드가 연결된 경우 서버에 업로드
      if (apiHealthy) {
        const result = await uploadImageToBackend(face, file)
        
        // 백엔드 이미지 정보 업데이트
        setBackendImages(prev => ({
          ...prev,
          [face]: result.data
        }))

        setUploadStatus({ type: 'success', message: result.message })
      } else {
        // 백엔드가 없는 경우 로컬만 처리
        setUploadStatus({ type: 'warning', message: '백엔드 서버가 없어서 로컬에만 저장됩니다.' })
      }

      // 이미지 미리보기를 위한 URL 생성 (로컬 사용)
      const imageUrl = URL.createObjectURL(file)
      
      // 부모 컴포넌트에 이미지 정보 전달
      onImageUpload(face, {
        file,
        url: imageUrl,
        name: file.name,
        size: file.size,
        type: file.type
      })

      setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
      
    } catch (error) {
      console.error('이미지 업로드 실패:', error)
      setUploadStatus({ 
        type: 'error', 
        message: `업로드 실패: ${error.message}` 
      })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 5000)
    } finally {
      setUploading(false)
    }
  }

  // 드래그 앤 드롭 핸들러
  const handleDragOver = (event, face) => {
    event.preventDefault()
    setDragOver(face)
  }

  const handleDragLeave = () => {
    setDragOver(null)
  }

  const handleDrop = async (event, face) => {
    event.preventDefault()
    setDragOver(null)

    if (uploading) return

    const files = event.dataTransfer.files
    if (files.length > 0) {
      const file = files[0]
      await processImageUpload(file, face)
    }
  }

  // 이미지 제거 핸들러
  const handleRemoveImage = async (face, event) => {
    event.stopPropagation()
    
    if (uploading) return

    try {
      // 백엔드가 연결된 경우 서버에서도 삭제
      if (apiHealthy && backendImages[face]) {
        await deleteCubeImage(face)
        
        // 백엔드 이미지 정보에서 제거
        setBackendImages(prev => {
          const newImages = { ...prev }
          delete newImages[face]
          return newImages
        })
        
        setUploadStatus({ type: 'success', message: `${face} 면의 이미지가 삭제되었습니다.` })
        setTimeout(() => setUploadStatus({ type: null, message: '' }), 2000)
      }
      
      // 로컬에서 제거
      onImageUpload(face, null)
      
    } catch (error) {
      console.error('이미지 삭제 실패:', error)
      setUploadStatus({ 
        type: 'error', 
        message: `삭제 실패: ${error.message}` 
      })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
    }
  }

  // 큐브 이미지 색상 분석 핸들러
  const handleAnalyzeCube = async () => {
    if (!apiHealthy) {
      setUploadStatus({ 
        type: 'error', 
        message: '백엔드 서버에 연결되지 않았습니다.' 
      })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
      return
    }

    if (Object.keys(uploadedImages).length < 6) {
      setUploadStatus({ 
        type: 'warning', 
        message: '모든 6개 면의 이미지를 업로드해주세요.' 
      })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
      return
    }

    setAnalyzing(true)
    setUploadStatus({ type: 'info', message: '큐브 이미지를 분석하는 중입니다...' })

    try {
      const result = await analyzeCubeImages()
      
      if (result.success) {
        setUploadStatus({ 
          type: 'success', 
          message: '✅ 색상 분석 완료! 큐브에 색상을 적용합니다.' 
        })
        
        // 분석 결과를 부모 컴포넌트로 전달
        if (onAnalysisComplete) {
          onAnalysisComplete(result.data.cube_colors, result.data.analysis_results)
        }
        
        setTimeout(() => setUploadStatus({ type: null, message: '' }), 3000)
      }
      
    } catch (error) {
      console.error('큐브 이미지 분석 실패:', error)
      setUploadStatus({ 
        type: 'error', 
        message: `분석 실패: ${error.message}` 
      })
      setTimeout(() => setUploadStatus({ type: null, message: '' }), 5000)
    } finally {
      setAnalyzing(false)
    }
  }

  const faceSize = 120

  return (
    <div className="image-upload-container">
      <h2>이미지 업로드</h2>
      <p className="upload-instruction">
        각 면을 클릭하거나 드래그 앤 드롭으로 이미지를 업로드하세요
      </p>
      
      {/* 업로드 상태 표시 */}
      {uploadStatus.message && (
        <div className={`upload-status ${uploadStatus.type}`}>
          {uploading && <span className="loading-spinner">⏳</span>}
          {uploadStatus.message}
        </div>
      )}
      
      {/* 백엔드 연결 상태 및 분석 버튼 */}
      <div className="backend-status">
        <div className="status-info">
          <span className={`status-indicator ${apiHealthy ? 'connected' : 'disconnected'}`}>
            {apiHealthy ? '🟢' : '🔴'}
          </span>
          백엔드 서버: {apiHealthy ? '연결됨' : '연결 안됨'}
          {!apiHealthy && (
            <button 
              className="retry-button" 
              onClick={checkBackendHealth}
              disabled={uploading}
            >
              재연결 시도
            </button>
          )}
        </div>
        
        {/* 색상 분석 버튼 */}
        {apiHealthy && Object.keys(uploadedImages).length > 0 && (
          <button 
            className="analyze-button"
            onClick={handleAnalyzeCube}
            disabled={analyzing || uploading}
          >
            {analyzing ? '🔄 분석 중...' : '🎨 색상 분석 및 큐브에 적용'}
          </button>
        )}
      </div>
      
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
                  className={`face-area ${isSelected ? 'selected' : ''} ${isDragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
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