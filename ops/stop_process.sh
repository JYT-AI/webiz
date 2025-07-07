#!/bin/bash

# Frappe Bench 강제 종료 스크립트
echo "🔍 Frappe Bench 프로세스 검색 중..."

# 1. honcho로 실행된 bench start 프로세스 종료
echo "📋 Honcho 프로세스 종료 중..."
pkill -f "honcho start" 2>/dev/null

# 2. Redis 프로세스 종료 (포트 기반)
echo "🔴 Redis 프로세스 종료 중..."
pkill -f "redis-server.*:11000" 2>/dev/null  # redis_queue
pkill -f "redis-server.*:13000" 2>/dev/null  # redis_cache

# 3. Frappe 관련 프로세스들 종료
echo "🐍 Frappe 프로세스 종료 중..."
pkill -f "frappe.*serve" 2>/dev/null          # web server
pkill -f "frappe.*socketio" 2>/dev/null       # socketio
pkill -f "frappe.*worker" 2>/dev/null         # worker
pkill -f "frappe.*schedule" 2>/dev/null       # scheduler
pkill -f "frappe.*watch" 2>/dev/null          # watch

# 4. 포트 기반으로 프로세스 종료
echo "🔌 포트 기반 프로세스 종료 중..."
for port in 8000 9000 11000 13000; do
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo "  포트 $port 에서 실행 중인 프로세스 $pid 종료"
        kill -9 $pid 2>/dev/null
    fi
done

# 5. 남은 프로세스 강제 종료
echo "💀 남은 프로세스 강제 종료 중..."
pkill -9 -f "bench.*start" 2>/dev/null
pkill -9 -f "honcho" 2>/dev/null

# 6. 결과 확인
sleep 1
echo ""
echo "✅ 정리 완료!"

# 남은 프로세스 확인
remaining=$(ps aux | grep -E "(frappe|honcho|redis)" | grep -v grep | wc -l)
if [ $remaining -gt 0 ]; then
    echo "⚠️  아직 실행 중인 관련 프로세스가 있습니다:"
    ps aux | grep -E "(frappe|honcho|redis)" | grep -v grep
else
    echo "🎉 모든 Bench 프로세스가 정리되었습니다!"
fi

echo ""
echo "이제 'bench start'를 다시 실행할 수 있습니다."
