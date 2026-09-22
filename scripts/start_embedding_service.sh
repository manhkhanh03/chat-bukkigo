#!/usr/bin/env bash
set -e

# Thư mục gốc dự án
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

PID_FILE="$ROOT_DIR/.embedding_service.pid"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/embedding_service.log"
PORT=8008

mkdir -p "$LOG_DIR"

# Kiểm tra nếu service đang chạy
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "[INFO] BGE-M3 Embedding Service đang chạy (PID: $PID trên cổng $PORT)."
        curl -s "http://localhost:$PORT/health" || true
        echo ""
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# Kiểm tra cổng 8008
if lsof -i :"$PORT" -sTCP:LISTEN > /dev/null 2>&1; then
    echo "[LỖI] Cổng $PORT đã có tiến trình khác lắng nghe."
    lsof -i :"$PORT"
    exit 1
fi

# Kiểm tra venv
VENV_DIR="$ROOT_DIR/.venv_embedding"
if [ ! -d "$VENV_DIR" ]; then
    echo "[LỖI] Thư mục virtualenv '$VENV_DIR' không tồn tại."
    exit 1
fi

echo "================================================================="
echo "=== KHỞI ĐỘNG BAAI/bge-m3 EMBEDDING SERVICE (APPLE SILICON GPU) ==="
echo "================================================================="
echo "Thư mục cache model: $ROOT_DIR/models_cache"
echo "File nhật ký log:    $LOG_FILE"
echo "Cổng lắng nghe:      $PORT"

# Khởi chạy ngầm với Metal GPU (MPS)
export PYTHONPATH="$ROOT_DIR:$ROOT_DIR/docker/embedding:$PYTHONPATH"
export HF_HOME="$ROOT_DIR/models_cache"
export DEVICE="mps"

nohup "$VENV_DIR/bin/python" -m uvicorn docker.embedding.app:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    > "$LOG_FILE" 2>&1 &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
echo "Đã khởi chạy tiến trình ngầm (PID: $NEW_PID). Đang kiểm tra trạng thái..."

# Chờ đợi healthcheck sẵn sàng (kiểm tra HTTP 200 OK)
MAX_WAIT=45
COUNT=0
while [ $COUNT -lt $MAX_WAIT ]; do
    if curl -s -f "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo ""
        echo "[THÀNH CÔNG] Service BGE-M3 đã sẵn sàng!"
        curl -s "http://localhost:$PORT/health"
        echo ""
        echo "================================================================="
        exit 0
    fi
    sleep 1
    COUNT=$((COUNT + 1))
    printf "."
done

echo ""
echo "[CẢNH BÁO] Quá thời gian chờ ($MAX_WAIT s). Vui lòng kiểm tra log: $LOG_FILE"
tail -n 20 "$LOG_FILE"
exit 1
