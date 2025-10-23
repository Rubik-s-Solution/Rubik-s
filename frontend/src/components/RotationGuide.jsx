import React, { useMemo, useRef } from 'react';
import { Text } from '@react-three/drei';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

/**
 * 3D 큐브에 회전 가이드 화살표를 표시하는 컴포넌트
 * @param {string} move - 회전 표기법 (예: "R", "U'", "F2")
 */
function RotationGuide({ move, visible = true }) {
  const groupRef = useRef();
  
  if (!visible || !move) return null;

  const face = move[0];
  const modifier = move.slice(1);
  const isCounterClockwise = modifier === "'";
  const is180 = modifier === "2";

  // 면에 따른 위치와 회전 설정
  const guideConfig = useMemo(() => {
    const configs = {
      'U': {
        position: [0, 3, 0],
        rotation: [-Math.PI / 2, 0, 0], // 위 면에 평평하게
        color: '#FFD700'
      },
      'D': {
        position: [0, -3, 0],
        rotation: [Math.PI / 2, 0, 0], // 아래 면에 평평하게
        color: '#FFA500'
      },
      'R': {
        position: [3, 0, 0],
        rotation: [0, Math.PI / 2, 0], // 오른쪽 면에 평평하게
        color: '#FF4444'
      },
      'L': {
        position: [-3, 0, 0],
        rotation: [0, -Math.PI / 2, 0], // 왼쪽 면에 평평하게
        color: '#FF8800'
      },
      'F': {
        position: [0, 0, 3],
        rotation: [0, 0, 0], // 앞 면에 평평하게
        color: '#00FF00'
      },
      'B': {
        position: [0, 0, -3],
        rotation: [0, Math.PI, 0], // 뒤 면에 평평하게
        color: '#4444FF'
      }
    };

    return configs[face] || configs['U'];
  }, [face]);

  // 원형 화살표 경로를 Tube 대신 평면 Shape으로 생성
  const arrowPathShape = useMemo(() => {
    const shape = new THREE.Shape();
    const radius = 1.4;
    const thickness = 0.12;
    const startAngle = 0;
    const endAngle = Math.PI * 1.6;
    const segments = 50;
    
    // 바깥 원호
    for (let i = 0; i <= segments; i++) {
      const angle = startAngle + (endAngle - startAngle) * (i / segments);
      const actualAngle = isCounterClockwise ? -angle : angle;
      const x = Math.cos(actualAngle) * radius;
      const y = Math.sin(actualAngle) * radius;
      
      if (i === 0) {
        shape.moveTo(x, y);
      } else {
        shape.lineTo(x, y);
      }
    }
    
    // 안쪽 원호 (역방향)
    for (let i = segments; i >= 0; i--) {
      const angle = startAngle + (endAngle - startAngle) * (i / segments);
      const actualAngle = isCounterClockwise ? -angle : angle;
      const x = Math.cos(actualAngle) * (radius - thickness);
      const y = Math.sin(actualAngle) * (radius - thickness);
      shape.lineTo(x, y);
    }
    
    shape.closePath();
    return shape;
  }, [isCounterClockwise]);

  // 평면 화살표 머리 Shape 생성 (더 큰 삼각형)
  const arrowHeadShape = useMemo(() => {
    const shape = new THREE.Shape();
    
    // 삼각형 화살촉 (더 크고 명확하게)
    shape.moveTo(0, 0.5);      // 위 꼭지점
    shape.lineTo(-0.35, -0.25);  // 왼쪽 아래
    shape.lineTo(0.35, -0.25);   // 오른쪽 아래
    shape.lineTo(0, 0.5);      // 닫기
    
    return shape;
  }, []);

  // 화살표 머리 위치 계산 (경로 끝 지점에 배치)
  const arrowHeadData = useMemo(() => {
    const startAngle = 0; // 0도 (오른쪽)
    const radius = 1.4;
    const x = Math.cos(startAngle) * radius; // x = 1.4
    const y = Math.sin(startAngle) * radius; // y = 0
    
    // 0도 위치(오른쪽)에서의 원 접선 방향으로 화살표 향하게 하기
    // 반시계방향: 위로 향함 (90도)
    // 시계방향: 아래로 향함 (270도 = -90도)
    const rotation = isCounterClockwise ? Math.PI / 2 : (Math.PI * 3 / 1);
    
    return { x, y, rotation };
  }, [isCounterClockwise]);

  // 180도일 경우 두 번째 화살표 (반대편 끝)
  const arrowHead2Data = useMemo(() => {
    if (!is180) return null;
    
    const angle = Math.PI; // 180도 (왼쪽)
    const radius = 1.4;
    const x = Math.cos(angle) * radius; // x = -1.4
    const y = Math.sin(angle) * radius; // y = 0
    
    // 180도 위치에서의 접선 방향 (반대편)
    const rotation = isCounterClockwise ? (Math.PI * 3 / 2) : Math.PI / 2;
    
    return { x, y, rotation };
  }, [is180, isCounterClockwise]);

  return (
    <group 
      ref={groupRef}
      position={guideConfig.position} 
      rotation={guideConfig.rotation}
    >
      {/* 배경 원판 (반투명) */}
      <mesh position={[0, 0, -0.01]}>
        <circleGeometry args={[1.8, 32]} />
        <meshBasicMaterial 
          color={guideConfig.color} 
          transparent 
          opacity={0.15} 
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 원형 화살표 경로 (평면) */}
      <mesh position={[0, 0, 0]}>
        <shapeGeometry args={[arrowPathShape]} />
        <meshBasicMaterial 
          color={guideConfig.color} 
          transparent
          opacity={0.9}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 화살표 머리 1 (평면) - 항상 표시 */}
      <group position={[arrowHeadData.x, arrowHeadData.y, 0.01]} rotation={[0, 0, arrowHeadData.rotation]}>
        <mesh>
          <shapeGeometry args={[arrowHeadShape]} />
          <meshBasicMaterial 
            color={guideConfig.color}
            transparent
            opacity={0.9}
            side={THREE.DoubleSide}
          />
        </mesh>
      </group>

      {/* 화살표 머리 2 (180도일 때, 평면) - 숨김 */}
      {false && is180 && arrowHead2Data && (
        <group position={[arrowHead2Data.x, arrowHead2Data.y, 0.01]} rotation={[0, 0, arrowHead2Data.rotation]}>
          <mesh>
            <shapeGeometry args={[arrowHeadShape]} />
            <meshBasicMaterial 
              color={guideConfig.color}
              transparent
              opacity={0.9}
              side={THREE.DoubleSide}
            />
          </mesh>
        </group>
      )}

      {/* 중앙 원형 배경 */}
      <mesh position={[0, 0, 0.05]}>
        <circleGeometry args={[0.6, 32]} />
        <meshBasicMaterial 
          color="#000000"
          transparent
          opacity={0.7}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 중앙 텍스트 레이블 */}
      <Text
        position={[0, 0, 0.1]}
        fontSize={0.6}
        color={guideConfig.color}
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.05}
        outlineColor="#000000"
        fontWeight="bold"
      >
        {move}
      </Text>

      {/* 180도 표시 */}
      {is180 && (
        <Text
          position={[0, -0.75, 0.1]}
          fontSize={0.35}
          color="#FFFFFF"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.03}
          outlineColor="#000000"
        >
          180°
        </Text>
      )}
    </group>
  );
}

export default RotationGuide;

