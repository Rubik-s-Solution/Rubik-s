from cube_solver import solve

# 1) 단일 상태 문자열
state1 = "DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD"
try:
    print(f"입력된 문자열: {state1}")
    solution = solve(state1)  # kociemba 있으면 그걸, 없으면 RubikTwoPhase
    print(f"✅ 계산된 해법: {solution}")
except Exception as e:
    print(f"❌ 오류: {e}")

# 2) 문자열 2개 넣는 형태는 지원하지 않음.
#    만약 '목표 패턴'을 쓰고 싶다면 kociemba의 pattern 문법을 써야 하는데,
#    임의의 두 완전 상태문자열을 직접 2개 넣는 방식은 API 대상이 아니다.
state2 = "FLBUULFFLFDURRDBUBUUDDFFBRDDBLRDRFLLRLRULFUDRRBDBBBUFL"
try:
    print(f"입력된 문자열: {state2}")
    solution = solve(state2)
    print(f"✅ 계산된 해법: {solution}")
except Exception as e:
    print(f"❌ 오류: {e}")
