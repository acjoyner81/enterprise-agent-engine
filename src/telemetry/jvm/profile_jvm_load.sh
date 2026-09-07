#!/usr/bin/env bash
# ==============================================================================
# JVM Diagnostics & Load Profiling Tool for High-Concurrency Microservices
# Uses OpenJDK utilities: jcmd, jstat, jstack, jmap
# ==============================================================================

set -eo pipefail

PID="$1"

if [ -z "$PID" ]; then
    # Search for running Java / Spring Boot processes
    PID=$(pgrep -f -d ' ' "java" | awk '{print $1}' || true)
fi

echo "======================================================================"
echo "          ENTERPRISE JVM TELEMETRY & PROFILING REPORT"
echo "======================================================================"

if [ -z "$PID" ]; then
    echo "[!] No running Java process detected on host."
    echo "[i] Run your Spring Boot service or pass PID explicitly: ./profile_jvm_load.sh <PID>"
    echo ""
    echo "=== Sample Target Profile (Reference Spec) ==="
    echo "• Heap Strategy: -XX:+UseG1GC -XX:MaxRAMPercentage=75.0"
    echo "• Max Pause Target: 100ms (-XX:MaxGCPauseMillis=100)"
    echo "• Diagnostic Commands:"
    echo "   - jcmd <PID> GC.heap_info"
    echo "   - jstat -gcutil <PID> 1000 5"
    echo "   - jstack -l <PID> > thread_dump.txt"
    exit 0
fi

echo "[✓] Attached to JVM PID: $PID"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

echo "--- [1] Heap Allocation & Region Info (jcmd GC.heap_info) ---"
if command -v jcmd >/dev/null 2>&1; then
    jcmd "$PID" GC.heap_info 2>&1 || echo "Warning: jcmd execution failed or permissions restricted."
else
    echo "jcmd not found in PATH."
fi
echo ""

echo "--- [2] Garbage Collection Utilization (jstat -gcutil) ---"
if command -v jstat >/dev/null 2>&1; then
    jstat -gcutil "$PID" 1000 3 2>&1 || echo "Warning: jstat execution failed."
else
    echo "jstat not found in PATH."
fi
echo ""

echo "--- [3] Thread Pool & Contention Summary (jstack thread states) ---"
if command -v jstack >/dev/null 2>&1; then
    THREAD_DUMP=$(jstack "$PID" 2>/dev/null || true)
    if [ -n "$THREAD_DUMP" ]; then
        echo "Total Threads: $(echo "$THREAD_DUMP" | grep -c "nid=" || echo 0)"
        echo "RUNNABLE:      $(echo "$THREAD_DUMP" | grep -c "java.lang.Thread.State: RUNNABLE" || echo 0)"
        echo "TIMED_WAITING: $(echo "$THREAD_DUMP" | grep -c "java.lang.Thread.State: TIMED_WAITING" || echo 0)"
        echo "WAITING:       $(echo "$THREAD_DUMP" | grep -c "java.lang.Thread.State: WAITING" || echo 0)"
        echo "BLOCKED:       $(echo "$THREAD_DUMP" | grep -c "java.lang.Thread.State: BLOCKED" || echo 0)"
    else
        echo "Unable to capture thread stack."
    fi
else
    echo "jstack not found in PATH."
fi
echo ""
echo "======================================================================"
echo "[✓] JVM Profiling complete."
echo "======================================================================"
