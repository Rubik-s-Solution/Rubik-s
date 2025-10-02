// 백엔드 API 기본 URL
const API_BASE_URL = 'http://127.0.0.1:8000'

/**
 * 이미지를 백엔드에 업로드
 * @param {string} face - 큐브 면 (U, D, F, B, L, R)
 * @param {File} file - 업로드할 이미지 파일
 * @returns {Promise<Object>} - 업로드 결과
 */
export const uploadImageToBackend = async (face, file) => {
  try {
    const formData = new FormData()
    formData.append('face', face)
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/upload-image`, {
      method: 'POST',
      body: formData,
    })

    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    return result
  } catch (error) {
    console.error('이미지 업로드 실패:', error)
    throw error
  }
}

/**
 * 백엔드에서 큐브 이미지 정보 조회
 * @returns {Promise<Object>} - 큐브 이미지 정보
 */
export const getCubeImages = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/cube-images`)
    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    return result
  } catch (error) {
    console.error('큐브 이미지 정보 조회 실패:', error)
    throw error
  }
}

/**
 * 백엔드에서 특정 면의 이미지 삭제
 * @param {string} face - 삭제할 큐브 면
 * @returns {Promise<Object>} - 삭제 결과
 */
export const deleteCubeImage = async (face) => {
  try {
    const response = await fetch(`${API_BASE_URL}/cube-images/${face}`, {
      method: 'DELETE',
    })

    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    return result
  } catch (error) {
    console.error('이미지 삭제 실패:', error)
    throw error
  }
}

/**
 * 백엔드 이미지 URL 생성
 * @param {string} filename - 이미지 파일명
 * @returns {string} - 완전한 이미지 URL
 */
export const getImageUrl = (filename) => {
  return `${API_BASE_URL}/images/${filename}`
}

/**
 * 백엔드 API 상태 확인
 * @returns {Promise<Object>} - API 상태 정보
 */
export const checkApiHealth = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    return result
  } catch (error) {
    console.error('API 상태 확인 실패:', error)
    throw error
  }
}