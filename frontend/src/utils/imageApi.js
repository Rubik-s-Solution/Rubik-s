// 백엔드 API 기본 URL
// 현재 호스트가 devine.my인 경우 devine.my 사용, 그렇지 않으면 localhost 사용
const API_BASE_URL = window.location.hostname === 'devine.my' 
  ? 'http://devine.my:8000' 
  : 'http://127.0.0.1:8000'

// 세션 ID 관리
const SESSION_STORAGE_KEY = 'rubiks_session_id'

/**
 * 로컬 스토리지에서 세션 ID 가져오기
 * @returns {string|null}
 */
export const getSessionId = () => {
  return localStorage.getItem(SESSION_STORAGE_KEY)
}

/**
 * 로컬 스토리지에 세션 ID 저장
 * @param {string} sessionId
 */
export const setSessionId = (sessionId) => {
  localStorage.setItem(SESSION_STORAGE_KEY, sessionId)
}

/**
 * 세션 ID 삭제
 */
export const clearSessionId = () => {
  localStorage.removeItem(SESSION_STORAGE_KEY)
}

/**
 * 새로운 세션 생성
 * @returns {Promise<Object>}
 */
export const createSession = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/create-session`, {
      method: 'POST',
    })

    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    // 세션 ID 저장
    if (result.session_id) {
      setSessionId(result.session_id)
    }

    return result
  } catch (error) {
    console.error('세션 생성 실패:', error)
    throw error
  }
}

/**
 * 세션 삭제
 * @returns {Promise<Object>}
 */
export const deleteSession = async () => {
  try {
    const sessionId = getSessionId()
    if (!sessionId) {
      return { success: false, message: '세션 ID가 없습니다.' }
    }

    const response = await fetch(`${API_BASE_URL}/delete-session`, {
      method: 'DELETE',
      headers: {
        'X-Session-Id': sessionId
      }
    })

    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    // 로컬에서도 세션 ID 삭제
    clearSessionId()

    return result
  } catch (error) {
    console.error('세션 삭제 실패:', error)
    throw error
  }
}

/**
 * 세션 헤더 생성 (선택적)
 * @returns {Object}
 */
const getSessionHeaders = () => {
  const sessionId = getSessionId()
  return sessionId ? { 'X-Session-Id': sessionId } : {}
}

/**
 * 이미지를 백엔드에 업로드
 * @param {string} face - 큐브 면 (U, D, F, B, L, R)
 * @param {File} file - 업로드할 이미지 파일
 * @returns {Promise<Object>} - 업로드 결과
 */
export const uploadImageToBackend = async (face, file) => {
  try {
    // 첫 이미지 업로드 시 항상 새 세션 생성
    let sessionId = getSessionId()
    if (!sessionId) {
      console.log('🆕 새 세션 생성 중...')
      const sessionResult = await createSession()
      sessionId = sessionResult.session_id
      console.log(`✅ 새 세션 생성 완료: ${sessionId}`)
    }

    const formData = new FormData()
    formData.append('face', face)
    formData.append('file', file)

    const response = await fetch(`${API_BASE_URL}/upload-image`, {
      method: 'POST',
      headers: {
        'X-Session-Id': sessionId
      },
      body: formData,
    })

    const result = await response.json()
    
    if (!response.ok) {
      // 세션이 유효하지 않은 경우 새로 생성하고 재시도
      if (result.detail && (result.detail.includes('유효하지 않은 세션') || result.detail.includes('X-Session-Id'))) {
        console.log('⚠️ 세션이 만료되었습니다. 새 세션을 생성합니다...')
        clearSessionId()
        const sessionResult = await createSession()
        sessionId = sessionResult.session_id
        
        // 새 세션 ID로 다시 업로드
        const retryResponse = await fetch(`${API_BASE_URL}/upload-image`, {
          method: 'POST',
          headers: {
            'X-Session-Id': sessionId
          },
          body: formData,
        })
        
        const retryResult = await retryResponse.json()
        if (!retryResponse.ok) {
          throw new Error(retryResult.detail || `HTTP error! status: ${retryResponse.status}`)
        }
        
        return retryResult
      }
      
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
    const sessionId = getSessionId()
    if (!sessionId) {
      return { success: true, data: {} }
    }

    const response = await fetch(`${API_BASE_URL}/cube-images`, {
      headers: {
        'X-Session-Id': sessionId
      }
    })
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
    const sessionId = getSessionId()
    if (!sessionId) {
      return { success: false, message: '세션 ID가 없습니다.' }
    }

    const response = await fetch(`${API_BASE_URL}/cube-images/${face}`, {
      method: 'DELETE',
      headers: {
        'X-Session-Id': sessionId
      }
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
  const sessionId = getSessionId()
  return sessionId 
    ? `${API_BASE_URL}/images/${sessionId}/${filename}`
    : `${API_BASE_URL}/images/${filename}`
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

/**
 * 업로드된 큐브 이미지들을 분석하여 색상 데이터 추출
 * @returns {Promise<Object>} - 분석 결과 (각 면의 3x3 색상 그리드 및 해법)
 */
export const analyzeCubeImages = async () => {
  try {
    const sessionId = getSessionId()
    if (!sessionId) {
      throw new Error('세션 ID가 없습니다. 먼저 이미지를 업로드하세요.')
    }

    const response = await fetch(`${API_BASE_URL}/analyze-cube-images`, {
      method: 'POST',
      headers: {
        'X-Session-Id': sessionId
      }
    })

    const result = await response.json()
    
    if (!response.ok) {
      // 세션이 유효하지 않은 경우 명확한 에러 메시지
      if (result.detail && (result.detail.includes('유효하지 않은 세션') || result.detail.includes('X-Session-Id'))) {
        clearSessionId()
        throw new Error('세션이 만료되었습니다. 이미지를 다시 업로드해주세요.')
      }
      
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    return result
  } catch (error) {
    console.error('큐브 이미지 분석 실패:', error)
    throw error
  }
}

/**
 * 현재 큐브 상태로부터 해법 생성
 * @param {Object} cubeColors - (선택) 현재 큐브 색상 상태. 없으면 세션의 analyzed_colors 사용
 * @returns {Promise<Object>} - 해법 결과
 */
export const generateSolution = async (cubeColors = null) => {
  try {
    // 세션이 없으면 자동으로 생성 (수동 조작 모드)
    let sessionId = getSessionId()
    if (!sessionId) {
      console.log('🆕 세션이 없습니다. 자동으로 세션 생성 중...')
      const sessionResult = await createSession()
      sessionId = sessionResult.session_id
      console.log('✅ 세션 자동 생성 완료:', sessionId)
    }

    const headers = {
      'X-Session-Id': sessionId,
      'Content-Type': 'application/json'
    }

    const body = cubeColors ? JSON.stringify({ cube_colors: cubeColors }) : null

    const response = await fetch(`${API_BASE_URL}/generate-solution`, {
      method: 'POST',
      headers: headers,
      body: body
    })

    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }

    return result
  } catch (error) {
    console.error('해법 생성 실패:', error)
    throw error
  }
}