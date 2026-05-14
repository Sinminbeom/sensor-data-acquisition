# sensor-data-acquisition

차량 탑재 센서 데이터 수집 시스템. uv workspace 기반 monorepo.

## 구조

- `service/` — 센서 데이터 수집 서비스 (gRPC 50051, CPU/VPU 빌드 변형)
- `gateway/` — 센서 게이트웨이 서비스 (gRPC 50050)
- `protos/` — 공유 protobuf 정의 (`service.proto`, `gateway.proto`)
- `utils/` — 보조 도구 (`file2base64`, `lidar-viewer`)
- `docker-compose-*.yml` — 차량/플랫폼별 배포 구성

`python-library`를 git tag 의존성으로 사용한다.

## 사전 요구사항

- Python 3.11 (`.python-version` 고정 — `grpcio-tools==1.62.1`이 3.14에서 빌드 실패)
- [uv](https://docs.astral.sh/uv/)

## 설치

```bash
# 워크스페이스 dev tooling (ruff, pyright, pytest)
uv sync

# service (CPU 빌드용 의존성)
uv sync --package service --extra cpu

# service (VPU 빌드용 의존성)
uv sync --package service --extra vpu

# gateway
uv sync --package gateway
```

## 차량 설정

`service/config/`:

- `VEHICLE_001/` ~ `VEHICLE_005/` — 차량별 CPU 설정 (`cpu.json` + `hesai_params/`, `robo_params/`)
- `T_BENCH_2/` — 테스트 벤치 설정
- `vpu_a.json`, `vpu_b.json`, `vpu_c.json` — VPU 변형

`gateway/config/`:

- `ap500.json`, `test_*.json` — 게이트웨이 설정

각 컨테이너의 설정 파일은 `CONFIG_FILE_PATH` 환경 변수로 지정된다.

## 실행

차량/플랫폼에 맞는 docker-compose 파일을 사용한다.

```bash
docker compose -f docker-compose-cpu-vehicle-001.yml up --build
docker compose -f docker-compose-cpu-t-bench-2.yml up --build
docker compose -f docker-compose-vpu-a.yml up --build
```

| compose 파일 | 대상 |
|--------------|------|
| `docker-compose-cpu-vehicle-001.yml` ~ `005.yml` | VEHICLE-001 ~ VEHICLE-005 (CPU) |
| `docker-compose-cpu-t-bench-2.yml` | 테스트 벤치 (CPU) |
| `docker-compose-vpu-a.yml` ~ `c.yml` | VPU 변형 |

## proto 재생성

`protos/`의 정본을 수정한 뒤 각 서비스에서 pb2를 재생성한다.

```bash
cd service && uv run python -m gen_protos
cd gateway && uv run python -m gen_protos
cd utils/lidar-viewer && uv run python -m gen_protos
```

## 테스트

```bash
uv run --package service pytest
uv run --package gateway pytest
```
