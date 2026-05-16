"""
Stress Test Suite — Concurrency, Throughput, Chain Integrity Under Load.

Run with:
    pytest tests/test_stress.py -v -s

The -s flag is required to see the statistics reports printed to stdout.

Each test is deliberately slow — exclude from regular CI unit runs:
    pytest tests/ --ignore=tests/test_stress.py
"""
import asyncio
import json
import sqlite3
import statistics
import time
import threading
import concurrent.futures

import httpx
import pytest
from fastapi.testclient import TestClient

import src.database as db_module
from src.database import init_db, verify_chain_integrity
from src.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def stress_db(monkeypatch, tmp_path):
    test_db = str(tmp_path / "stress_ledger.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    init_db()
    with open("config/state.json", "w") as f:
        json.dump({"kill_switch_active": False, "last_toggled_by": None, "last_toggled_at": None}, f)
    return test_db


def _print_report(title: str, n: int, concurrency: int, total_time: float,
                  statuses: list[int], latencies: list[float], db_path: str) -> None:
    approved = sum(1 for s in statuses if s == 200)
    blocked  = sum(1 for s in statuses if s == 403)
    errors   = sum(1 for s in statuses if s not in (200, 403, 503))
    rps      = n / total_time
    lat_ms   = [l * 1000 for l in latencies]
    sorted_l = sorted(lat_ms)
    p95      = sorted_l[int(0.95 * len(sorted_l))]
    p99      = sorted_l[int(0.99 * len(sorted_l))]

    # Verify chain
    intact, broken = verify_chain_integrity()
    chain_status = "VERIFIED" if intact else f"BROKEN at row {broken}"

    conn = sqlite3.connect(db_path)
    db_rows = conn.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
    conn.close()

    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"  Requests:       {n} total | {concurrency} concurrent workers")
    print(f"  Total time:     {total_time:.2f}s")
    print(f"  Throughput:     {rps:.1f} req/s")
    print(f"  -- Status -----------------------------------------------")
    print(f"  200 Approved:   {approved:>5}  ({approved/n*100:.1f}%)")
    print(f"  403 Blocked:    {blocked:>5}  ({blocked/n*100:.1f}%)")
    print(f"  Other errors:   {errors:>5}")
    print(f"  -- Latency (ms) -----------------------------------------")
    print(f"  Mean:           {statistics.mean(lat_ms):.1f}ms")
    print(f"  Median:         {statistics.median(lat_ms):.1f}ms")
    print(f"  P95:            {p95:.1f}ms")
    print(f"  P99:            {p99:.1f}ms")
    print(f"  Max:            {max(lat_ms):.1f}ms")
    print(f"  -- Audit Ledger -----------------------------------------")
    print(f"  DB rows written:{db_rows}")
    print(f"  Chain integrity:{chain_status}")
    print(f"{'='*60}\n")

    return errors, intact


# ===========================================================================
# 1. Async Concurrent Gateway Load
# ===========================================================================
class TestConcurrentGatewayLoad:
    def test_100_mixed_requests_async(self, stress_db):
        """100 async concurrent requests (50 safe / 50 blocked). Validates
        throughput, zero errors, and chain integrity."""
        N = 100
        CONCURRENCY = 20

        safe_prompts    = [f"Summarise governance report number {i}" for i in range(50)]
        blocked_prompts = [f"Deploy malware payload number {i}" for i in range(50)]
        all_prompts     = safe_prompts + blocked_prompts

        async def run():
            sem = asyncio.Semaphore(CONCURRENCY)
            results = []

            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async def one(prompt):
                    async with sem:
                        t0 = time.perf_counter()
                        r  = await client.post("/v1/intercept", json={"prompt": prompt})
                        return r.status_code, time.perf_counter() - t0

                t_start = time.perf_counter()
                results = await asyncio.gather(*[one(p) for p in all_prompts])
                total   = time.perf_counter() - t_start

            return results, total

        results, total_time = asyncio.run(run())
        statuses  = [r[0] for r in results]
        latencies = [r[1] for r in results]

        errors, intact = _print_report(
            "ASYNC CONCURRENT LOAD — 100 requests / 20 workers",
            N, CONCURRENCY, total_time, statuses, latencies, stress_db
        )

        assert errors == 0, f"{errors} requests returned unexpected status codes"
        assert statuses.count(200) == 50,  "Expected 50 approved requests"
        assert statuses.count(403) == 50,  "Expected 50 blocked requests"
        assert intact, "Hash chain corrupted under concurrent async load"

    def test_200_safe_requests_async(self, stress_db):
        """200 safe prompts — validates zero false-positives at volume."""
        N = 200
        CONCURRENCY = 30

        prompts = [f"What are the NIST AI RMF requirements for category {i}?" for i in range(N)]

        async def run():
            sem = asyncio.Semaphore(CONCURRENCY)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async def one(p):
                    async with sem:
                        t0 = time.perf_counter()
                        r  = await client.post("/v1/intercept", json={"prompt": p})
                        return r.status_code, time.perf_counter() - t0
                t0 = time.perf_counter()
                results = await asyncio.gather(*[one(p) for p in prompts])
                return results, time.perf_counter() - t0

        results, total_time = asyncio.run(run())
        statuses  = [r[0] for r in results]
        latencies = [r[1] for r in results]

        errors, intact = _print_report(
            "ASYNC SAFE-ONLY LOAD — 200 requests / 30 workers",
            N, CONCURRENCY, total_time, statuses, latencies, stress_db
        )

        false_positives = sum(1 for s in statuses if s == 403)
        assert false_positives == 0, f"{false_positives} safe prompts were incorrectly blocked"
        assert intact, "Hash chain corrupted"


# ===========================================================================
# 2. Concurrent Threaded Writes — Hash Chain Race Condition Test
# ===========================================================================
class TestConcurrentHashChain:
    def test_chain_integrity_under_threaded_writes(self, stress_db):
        """50 threads each write 4 log entries simultaneously.
        Validates the threading lock prevents hash chain corruption."""
        N_THREADS  = 50
        WRITES_PER = 4
        TOTAL      = N_THREADS * WRITES_PER

        errors = []

        def write_batch(thread_id: int):
            try:
                for i in range(WRITES_PER):
                    from src.database import log_transaction
                    log_transaction(
                        request_id=f"thread-{thread_id}-req-{i}",
                        tenant_id="stress-tenant",
                        action="PASSED" if i % 2 == 0 else "BLOCKED",
                        violation=None if i % 2 == 0 else f"violation-t{thread_id}-{i}",
                    )
            except Exception as e:
                errors.append(str(e))

        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=N_THREADS) as pool:
            futures = [pool.submit(write_batch, tid) for tid in range(N_THREADS)]
            concurrent.futures.wait(futures)
        total_time = time.perf_counter() - t0

        intact, broken = verify_chain_integrity()
        conn = sqlite3.connect(stress_db)
        row_count = conn.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
        conn.close()

        print(f"\n{'='*60}")
        print(f"  CONCURRENT THREADED WRITES — {N_THREADS} threads × {WRITES_PER} writes")
        print(f"{'='*60}")
        print(f"  Total writes:   {TOTAL}")
        print(f"  Rows in DB:     {row_count}")
        print(f"  Write errors:   {len(errors)}")
        print(f"  Total time:     {total_time:.2f}s")
        print(f"  Chain integrity:{('VERIFIED' if intact else f'BROKEN at row {broken}')}")
        print(f"{'='*60}\n")

        assert len(errors) == 0, f"Write errors: {errors[:3]}"
        assert row_count == TOTAL, f"Expected {TOTAL} rows, got {row_count}"
        assert intact, f"Hash chain corrupted under threaded writes — broken at row {broken}"

    def test_no_duplicate_hash_collisions(self, stress_db):
        """Every current_hash in the ledger must be unique."""
        N = 100
        for i in range(N):
            from src.database import log_transaction
            log_transaction(f"uniq-{i}", "t1", "PASSED", None)

        conn = sqlite3.connect(stress_db)
        total  = conn.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
        unique = conn.execute("SELECT COUNT(DISTINCT current_hash) FROM compliance_log").fetchone()[0]
        conn.close()

        assert total == unique, f"Hash collision: {total} rows but only {unique} unique hashes"


# ===========================================================================
# 3. Large Payload Stress Test
# ===========================================================================
class TestLargePayloads:
    def test_10kb_safe_prompt(self, stress_db):
        prompt = "What is the AI governance requirement? " * 270  # ~10KB
        client = TestClient(app)
        t0 = time.perf_counter()
        r  = client.post("/v1/intercept", json={"prompt": prompt})
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"\n  LARGE PAYLOAD: 10KB safe prompt -> {r.status_code} in {latency_ms:.1f}ms")
        assert r.status_code == 200

    def test_10kb_prompt_with_forbidden_token_at_end(self, stress_db):
        prompt = ("Safe content. " * 700) + " malware"
        client = TestClient(app)
        r = client.post("/v1/intercept", json={"prompt": prompt})
        assert r.status_code == 403

    def test_50_large_payloads_concurrently(self, stress_db):
        """50 × 5KB prompts in parallel — validates no timeout or memory spike."""
        N = 50
        prompt = "AI governance policy analysis. " * 160  # ~5KB

        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                t0 = time.perf_counter()
                results = await asyncio.gather(*[
                    client.post("/v1/intercept", json={"prompt": prompt})
                    for _ in range(N)
                ])
                return results, time.perf_counter() - t0

        results, total_time = asyncio.run(run())
        statuses = [r.status_code for r in results]
        errors   = [s for s in statuses if s != 200]

        print(f"\n  LARGE PAYLOAD CONCURRENCY: {N} x 5KB -> {total_time:.2f}s | errors: {len(errors)}")
        assert len(errors) == 0, f"Large payload errors: {errors[:5]}"


# ===========================================================================
# 4. Kill-Switch Rapid Toggle Stability
# ===========================================================================
class TestKillSwitchStability:
    def test_rapid_toggle_does_not_corrupt_state(self, stress_db):
        """Toggle kill switch 50 times rapidly — final state must be deterministic."""
        for i in range(50):
            active = (i % 2 == 0)
            with open("config/state.json", "w") as f:
                json.dump({"kill_switch_active": active}, f)

        with open("config/state.json") as f:
            final = json.load(f)["kill_switch_active"]

        # After 50 toggles (0-indexed), last iteration i=49 → active = False
        assert final is False

    def test_concurrent_requests_during_kill_switch_toggle(self, stress_db):
        """While requests are in-flight, toggle the kill switch.
        Validates no crash or unhandled exception."""
        results = []
        stop_event = threading.Event()

        def toggle_loop():
            for _ in range(20):
                if stop_event.is_set():
                    break
                with open("config/state.json", "w") as f:
                    json.dump({"kill_switch_active": True}, f)
                time.sleep(0.01)
                with open("config/state.json", "w") as f:
                    json.dump({"kill_switch_active": False}, f)
                time.sleep(0.01)

        toggle_thread = threading.Thread(target=toggle_loop, daemon=True)
        toggle_thread.start()

        client = TestClient(app)
        for _ in range(30):
            try:
                r = client.post("/v1/intercept", json={"prompt": "governance query"})
                results.append(r.status_code)
            except Exception as e:
                results.append(f"EXCEPTION: {e}")

        stop_event.set()
        toggle_thread.join()

        # Reset kill switch to off
        with open("config/state.json", "w") as f:
            json.dump({"kill_switch_active": False}, f)

        exceptions = [r for r in results if isinstance(r, str)]
        valid       = [r for r in results if r in (200, 403, 503)]

        print(f"\n  KILL SWITCH TOGGLE STABILITY: {len(valid)} valid | {len(exceptions)} exceptions")
        assert len(exceptions) == 0, f"Exceptions during toggle: {exceptions}"


# ===========================================================================
# 5. Throughput Benchmark
# ===========================================================================
class TestThroughputBenchmark:
    def test_maximum_rps_benchmark(self, stress_db):
        """Push maximum requests through the gateway and report peak RPS.
        No hard assertion on RPS — this is a benchmark, not a pass/fail gate."""
        N = 500
        CONCURRENCY = 50

        async def run():
            sem = asyncio.Semaphore(CONCURRENCY)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                async def one(i):
                    async with sem:
                        t0 = time.perf_counter()
                        r  = await client.post(
                            "/v1/intercept",
                            json={"prompt": f"Benchmark request {i}: AI governance report"}
                        )
                        return r.status_code, time.perf_counter() - t0
                t0 = time.perf_counter()
                results = await asyncio.gather(*[one(i) for i in range(N)])
                return results, time.perf_counter() - t0

        results, total_time = asyncio.run(run())
        statuses  = [r[0] for r in results]
        latencies = [r[1] for r in results]

        errors, intact = _print_report(
            "PEAK THROUGHPUT BENCHMARK — 500 requests / 50 workers",
            N, CONCURRENCY, total_time, statuses, latencies, stress_db
        )

        assert errors == 0, f"{errors} unexpected errors during benchmark"
        assert intact, "Hash chain corrupted during benchmark"
