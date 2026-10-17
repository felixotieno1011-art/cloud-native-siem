#!/data/data/com.termux/files/usr/bin/bash
# dev.sh — bring up Redis + PostgreSQL + backend in one shot.
# Usage: ./dev.sh
set -u

REPO="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$REPO/backend"
LOGDIR="$REPO/.dev-logs"
mkdir -p "$LOGDIR"

say() { printf "\033[1;36m[dev]\033[0m %s\n" "$*"; }
die() { printf "\033[1;31m[dev]\033[0m %s\n" "$*" >&2; exit 1; }

say "cleaning up stale processes"
pkill -f "siem_backend" 2>/dev/null && say "  killed stale backend" || true
pkill -f "redis-server.*6379" 2>/dev/null && say "  killed stale redis" || true
sleep 1

command -v redis-server >/dev/null || die "redis-server not found (pkg install redis)"
command -v pg_ctl >/dev/null || die "pg_ctl not found (pkg install postgresql)"
[ -d "$BACKEND/.venv" ] || die "backend venv missing: cd backend && uv venv .venv && uv pip install -e '.[dev]'"

say "checking postgresql"
if ! pg_isready >/dev/null 2>&1; then
    say "  starting postgresql"
    pg_ctl -D "$PREFIX/var/lib/postgresql" start >/dev/null 2>&1 || \
        pg_ctl -D "$PREFIX/var/lib/postgresql" -l "$LOGDIR/pg.log" start >/dev/null 2>&1
    for _ in 1 2 3 4 5; do
        pg_isready >/dev/null 2>&1 && break
        sleep 1
    done
fi
pg_isready >/dev/null 2>&1 || die "postgresql failed to start (see $LOGDIR/pg.log)"
say "  postgresql ready"

say "starting redis"
redis-server --daemonize yes --save "" --appendonly no --logfile "$LOGDIR/redis.log"
for _ in 1 2 3 4 5; do
    redis-cli ping >/dev/null 2>&1 && break
    sleep 1
done
redis-cli ping >/dev/null 2>&1 || die "redis failed to start (see $LOGDIR/redis.log)"
say "  redis ready"

say "starting backend on http://127.0.0.1:8080"
cd "$BACKEND"
source .venv/bin/activate
nohup python -m siem_backend > "$LOGDIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$LOGDIR/backend.pid"

for _ in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
        say "  backend ready (pid $BACKEND_PID)"
        break
    fi
    sleep 0.5
done
curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1 || die "backend failed to start (see $LOGDIR/backend.log)"

say "tailing backend log (Ctrl+C to stop watching; services keep running)"
say "  pid file: $LOGDIR/backend.pid"
say "  stop with: pkill -f siem_backend && pkill -f redis-server"
tail -f "$LOGDIR/backend.log"
