#!/usr/bin/env bash
# 노트북 환경에서 USBCamera → NetCamera 통해 pcap 저장하는 흐름을
# 한 스크립트로 묶은 헬퍼.
#
# 사용:
#   ./scripts/laptop_record.sh [duration_seconds]
#
# 예:
#   ./scripts/laptop_record.sh 30        # 30초 캡처
#   ./scripts/laptop_record.sh           # Enter 누를 때까지 캡처
#
# 사전 조건:
#   - ssh-add ~/.ssh/id_ed25519-personal (python-library private repo clone)
#   - mkdir -p ./pcap/disk0 (Storage 드라이버가 disk sub-dir 인식)
set -euo pipefail

DURATION="${1:-}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose-laptop.yml"
PCAP_DIR="$REPO_ROOT/pcap/disk0"
GRPC_HOST="localhost:50061"

cd "$REPO_ROOT"

# 사전 조건 확인
mkdir -p "$PCAP_DIR"
if ! ssh-add -l >/dev/null 2>&1; then
  echo "[!] ssh-agent에 키가 없음. 'ssh-add ~/.ssh/id_ed25519-personal' 먼저 실행" >&2
  exit 1
fi

call_grpc() {
  # $1 = method, $2 = sensor name
  cd "$REPO_ROOT/apps/service"
  uv run --extra cpu python -c "
import sys; sys.path.insert(0, 'src/protos')
import grpc, service_pb2 as pb, service_pb2_grpc as pb_grpc
ch = grpc.insecure_channel('$GRPC_HOST')
client = pb_grpc.ServiceStub(ch)
r = getattr(client, '$1')(pb.Sensor(name='$2'))
print(f'$1 $2:', r.state, r.reason or '')
"
  cd "$REPO_ROOT"
}

cleanup() {
  echo "[*] 중지 (역순)"
  call_grpc stop_acquisition webcam     || true
  call_grpc stop_acquisition webcam_sniff || true
  echo "[*] 컨테이너 종료"
  docker compose -f "$COMPOSE_FILE" down >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

echo "[*] 컨테이너 빌드 + 기동"
docker compose -f "$COMPOSE_FILE" up --build -d

echo "[*] 부팅 대기 (gRPC 50061 LISTEN 확인)"
for i in {1..30}; do
  if ss -tln 2>/dev/null | grep -q ":50061 "; then
    echo "[*] 부팅 완료"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[!] 30초 안에 50061 LISTEN 안 됨. 컨테이너 로그 확인:" >&2
    docker compose -f "$COMPOSE_FILE" logs service | tail -20 >&2
    exit 1
  fi
  sleep 1
done

echo "[*] gRPC 캡처 시작 (sniff 먼저, 카메라 다음)"
call_grpc start_acquisition webcam_sniff
call_grpc start_acquisition webcam

if [ -n "$DURATION" ]; then
  echo "[*] ${DURATION}초 동안 캡처..."
  sleep "$DURATION"
else
  echo "[*] 캡처 중. 종료하려면 Enter."
  read -r
fi

# cleanup이 trap으로 호출됨. 종료 후 pcap 위치 안내:
trap - EXIT INT TERM
cleanup

echo
echo "[✓] 완료. pcap 파일:"
ls -lh "$PCAP_DIR/$(date +%Y%m%d)/LAPTOP/" 2>/dev/null || echo "  (저장된 파일 없음)"
echo
echo "참고: 파일 소유자가 root/messagebus라 삭제는 sudo 필요:"
echo "  sudo rm -rf $PCAP_DIR/$(date +%Y%m%d)/LAPTOP/*"
