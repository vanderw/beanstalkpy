import pytest
import asyncio
import uuid
from beanstalkpy import Client, Job, exceptions
from beanstalkpy.pool import Pool

def get_tube():
    return f"tube_{uuid.uuid4().hex[:8]}"

@pytest.fixture
async def client():
    try:
        async with Client() as c:
            yield c
    except (ConnectionRefusedError, exceptions.ConnectionError):
        pytest.skip("beanstalkd not running")

@pytest.mark.asyncio
async def test_basic_workflow(client):
    tube = get_tube()
    await client.use(tube)
    assert await client.list_tube_used() == tube
    
    await client.watch(tube)
    assert tube in await client.list_tubes_watched()
    
    body = b"test_job_body"
    job_id = await client.put(body)
    assert job_id > 0
    
    job = await client.reserve(timeout=0)
    assert job.id == job_id
    assert job.body == body
    
    await client.delete(job.id)
    
    with pytest.raises(exceptions.NotFoundError):
        await client.delete(job.id)

@pytest.mark.asyncio
async def test_release_and_bury(client):
    tube = get_tube()
    await client.use(tube)
    await client.watch(tube)
    
    job_id = await client.put(b"release me")
    job = await client.reserve(timeout=0)
    await client.release(job.id, priority=10, delay=0)
    
    # Reserve again
    job2 = await client.reserve(timeout=0)
    assert job2.id == job_id
    
    await client.bury(job2.id, priority=20)
    
    # In beanstalkd, reserve(timeout=0) with no ready jobs returns TIMED_OUT
    with pytest.raises(exceptions.TimedOutError):
        await client.reserve(timeout=0)
        
    # Peek buried (only works on used tube)
    peeked = await client.peek_buried()
    assert peeked.id == job_id
    
    # Kick
    kicked_count = await client.kick(1)
    assert kicked_count == 1
    
    # Now it should be ready
    job3 = await client.reserve(timeout=0)
    assert job3.id == job_id
    await client.delete(job3.id)

@pytest.mark.asyncio
async def test_touch_and_ttr(client):
    tube = get_tube()
    await client.use(tube)
    await client.watch(tube)
    
    # Put job with small TTR
    job_id = await client.put(b"touch me", ttr=2)
    job = await client.reserve(timeout=0)
    
    await client.touch(job.id)
    # Check stats to see if time-left increased
    stats = await client.stats_job(job.id)
    assert stats["time-left"] > 0
    
    await client.delete(job.id)

@pytest.mark.asyncio
async def test_peek_variations(client):
    tube = get_tube()
    await client.use(tube)
    await client.watch(tube)
    
    # Ready job
    jid_ready = await client.put(b"ready", delay=0)
    # Delayed job
    jid_delayed = await client.put(b"delayed", delay=3600)
    
    p_ready = await client.peek_ready()
    assert p_ready.id == jid_ready
    
    p_delayed = await client.peek_delayed()
    assert p_delayed.id == jid_delayed
    
    # Bury one to test peek_buried
    job = await client.reserve(timeout=0)
    await client.bury(job.id)
    p_buried = await client.peek_buried()
    assert p_buried.id == jid_ready
    
    await client.kick_job(jid_ready)
    await client.delete(jid_ready)
    await client.delete(jid_delayed)

@pytest.mark.asyncio
async def test_watch_ignore(client):
    tube1 = get_tube()
    tube2 = get_tube()
    
    await client.watch(tube1)
    await client.watch(tube2)
    
    # Ignore everything except one to test last tube protection
    watched = await client.list_tubes_watched()
    for tube in watched:
        if tube != tube2:
            await client.ignore(tube)
    
    # Now tube2 is the only one left
    watched = await client.list_tubes_watched()
    assert watched == [tube2]
    
    # Cannot ignore the last tube
    with pytest.raises(exceptions.NotIgnoredError):
        await client.ignore(tube2)

@pytest.mark.asyncio
async def test_pool():
    try:
        tube = get_tube()
        async with Pool(maxsize=2) as pool:
            c1 = await pool.acquire()
            c2 = await pool.acquire()
            
            await c1.use(tube)
            await c1.put(b"job1")
            
            await pool.release(c1)
            await pool.release(c2)
            
            # Re-acquire
            c3 = await pool.acquire()
            await c3.watch(tube)
            job = await c3.reserve(timeout=0)
            assert job.body == b"job1"
            await c3.delete(job.id)
            await pool.release(c3)
    except (ConnectionRefusedError, exceptions.ConnectionError):
        pytest.skip("beanstalkd not running")

@pytest.mark.asyncio
async def test_stats_commands(client):
    stats = await client.stats()
    assert "pid" in stats
    
    tube = get_tube()
    await client.use(tube)
    tstats = await client.stats_tube(tube)
    assert tstats["name"] == tube
    
    jid = await client.put(b"stats")
    jstats = await client.stats_job(jid)
    assert jstats["id"] == jid
    assert jstats["tube"] == tube
    await client.delete(jid)

@pytest.mark.asyncio
async def test_pause_tube(client):
    tube = get_tube()
    await client.use(tube)
    await client.pause_tube(tube, 1)
    
@pytest.mark.asyncio
async def test_reserve_job(client):
    # reserve-job was added in 1.12. Check version.
    stats = await client.stats()
    version = str(stats.get("version", "0.0"))
    parts = version.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    if major < 1 or (major == 1 and minor < 12):
        pytest.skip(f"reserve-job not supported in version {version}")

    tube = get_tube()
    await client.use(tube)
    jid = await client.put(b"reserve me")
    
    job = await client.reserve_job(jid)
    assert job.id == jid
    assert job.body == b"reserve me"
    await client.delete(jid)
