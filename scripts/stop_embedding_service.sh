#!/usr/bin/env bash
set -e

# Thư mục gốc dự án
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$ROOT_DIR/.embedding_service.pid"
PORT=8008

echo "================================================================="
echo "=== DỪNG BAAI/bge-m3 EMBEDDING SERVICE ==="
echo "================================================================="

STOPPED=0

# 1. Dừng qua PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Đang gửi tín hiệu dừng tiến trình PID: $PID..."
        kill "$PID" 2>/dev/null || true
        sleep 2
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Tiến trình chưa tắt, buộc dừng (kill -9)..."
            kill -9 "$PID" 2>/dev/null || true
        fi
        echo "Đã dừng tiến trình PID: $PID."
        STOPPED=1
    fi
    rm -f "$PID_FILE"
fi

# 2. Dọn dẹp nếu còn tiến trình chiếm cổng 8008
LISTEN_PID=$(lsof -ti :"$PORT" -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$LISTEN_PID" ]; then
    echo "Phát hiện tiến trình PID $LISTEN_PID đang chiếm cổng $PORT. Đang dừng..."
    kill -9 "$LISTEN_PID" 2>/dev/null || true
    STOPPED=1
fi

if [ $STOPPED -eq 1 ]; then
    echo "[THÀNH CÔNG] BGE-M3 Embedding Service đã được tắt hoàn toàn."
else
    echo "[INFO] Không có tiến trình BGE-M3 nào đang chạy trên cổng $PORT."
fi
echo "================================================================="
