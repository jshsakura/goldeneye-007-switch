# GoldenEye 007 - Nintendo Switch Native Port (한국어 자막 & 자이로 조준)

1997년 닌텐도 64(N64) 명작 FPS **골든아이 007(GoldenEye 007)**의 닌텐도 스위치(Nintendo Switch) 네이티브 홈브루 포트입니다.

에뮬레이터를 통한 구동이 아닌, N64 디컴파일 소스코드를 기반으로 스위치(AArch64) 환경에 맞추어 네이티브 컴파일한 버전입니다.

---

## 🎮 주요 기능 및 특징

1. **완벽한 한국어 자막 지원 (v1.0)**
   - N64용 골든아이 007 한국어화 패치(v1.0)를 완벽하게 이식.
   - Fast3D 렌더러의 동적 일본어/한국어 폰트 텍스처 캐시 충돌 버그를 수정하여 텍스트 깨짐 및 글자 중복("제임임 본드" 등) 현상 100% 해결.
2. **젤다의 전설 / 스플래툰 스타일 1:1 자이로 조준 (Motion Controls)**
   - 조이콘(Joy-Con) 및 프로콘의 6축 모션 센서를 연동하여 정밀 조준 지원.
   - 가상 스틱 에뮬레이션 방식이 아닌, 카메라 회전 각도(Theta/Verta)를 1:1로 직접 누적하는 최신 콘솔 방식 적용 (스프링백 회귀 없음, 360도 자유 조준).
   - 휴대 모드(Handheld: Yaw + Roll 복합 축 보정) 및 독 모드/테이블탑 모드(Pure Yaw) 자동 감지 및 적용.
   - 스나이퍼 라이플/조준경 줌 배율(FOV) 연동 감도 자동 보정.
3. **고해상도 커스텀 홈브루 아이콘 적용**
   - 스위치 홈브루 메뉴(HBL)에 최적화된 고화질 아이콘 및 NACP 메타데이터 내장.

---

## 🛠️ 빌드 및 설치 방법 (All-in-One Automated Builder)

저작권 법적 보호(Clean-room)를 위해 ROM 파일은 저장소에 포함되어 있지 않습니다. 일본판 N64 롬 파일 하나만 준비하면 파이썬 빌더가 모든 과정을 자동으로 처리합니다.

### 1. 준비물
- **Docker** (또는 로컬 `devkitA64` 툴체인)
- **Python 3**
- **일본판 골든아이 007 ROM** (`GoldenEye 007 (Japan).z64` 또는 `baserom.j.z64`)
  - *순정 일본판 롬을 넣으면 빌더가 내장된 BPS 패치를 통해 한글 롬으로 자동 변환합니다.*

### 2. 원클릭 빌드 실행

```bash
# 1. 저장소 클론
git clone https://github.com/<your-username>/goldeneye-switch-port.git
cd goldeneye-switch-port

# 2. 일본판 롬 복사 (또는 --rom 옵션 지정)
cp /path/to/GoldenEye007_Japan.z64 baserom.j.z64

# 3. 원클릭 빌드 스크립트 실행
python3 build_switch.py --zip
# 또는
./build-switch.sh --zip
```

스크립트가 자동으로 수행하는 작업:
1. ROM SHA-1 해시 자동 검증
2. 순정 일본판 롬 감지 시 `patches/ge007_korean.bps` 자동 적용
3. 텍스처/3D 모델 사이드카(`pccg`, `pcmodels`) 오프라인 변환 생성
4. Docker(`devkitpro/devkita64`)를 통한 스위치용 `ge007.nro` 컴파일
5. SD카드 배포용 `dist/switch/ge007/` 및 `dist/ge007-switch-korean.zip` 패키징

---

## 💾 닌텐도 스위치에 설치하기

1. 닌텐도 스위치 SD 카드를 PC에 연결합니다.
2. 빌드 결과물인 `dist/switch/ge007/` 폴더를 SD 카드의 `/switch/` 디렉토리로 복사합니다.
   ```text
   SD카드:/
   └── switch/
       └── ge007/
           ├── ge007.nro
           └── data/
               ├── ge007.ini
               ├── ge007.jpn-final.z64
               ├── pccg-jpn-final/
               └── pcmodels-jpn-final/
   ```
3. 스위치 본체에서 홈브루 메뉴(HBL)를 열고 **007 GoldenEye**를 실행합니다.

---

## 📜 크레딧 및 출처 (Credits & Attributions)

본 프로젝트는 수많은 오픈소스 기여자들과 팬 번역가들의 노력 덕분에 완성되었습니다.

* **원작 게임 (GoldenEye 007, 1997)**: Rare Ltd. / Nintendo
* **N64 소스코드 디컴파일 프로젝트**: [n64decomp/007](https://github.com/n64decomp/007)
* **PC 포트 프로젝트**: [jkdansereau/goldeneye-pc-port](https://github.com/jkdansereau/goldeneye-pc-port)
* **N64 한국어 패치 (v1.0)**: **retrace** 님 ([RetroDB](https://retrodb.info))
* **닌텐도 스위치 포트 & 모션 조준 (Gyro Aiming)**: **jshsakura**

---

## ⚖️ 라이선스 및 저작권 (Legal Notice)

* 이 리포지토리는 닌텐도, 마이크로소프트, 레어(Rare), EON Productions 또는 MGM의 어떠한 상표나 저작물(ROM, 추출된 음원, 텍스처 바이너리)도 직접 배포하지 않는 **클린룸(Clean-room)** 원칙을 준수합니다.
* 사용자는 자신이 합법적으로 덤프한 정품 게임 롬(ROM)을 직접 제공해야 합니다.
