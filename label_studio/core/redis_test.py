import redis
from rq import Queue, Retry
from rq.job import Job
from rq.worker import Worker
import time


def test_1():
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.set('foo', 'bar')
    r.get('foo')

    r.hset('user-session:123', mapping={
        'name': 'John',
        "surname": 'Smith',
        "company": 'Redis',
        "age": 29
    })

    r.hgetall('user-session:123')


# =====================
# 模拟后台任务（LS里导出、预标注、ml任务都是这类函数）
# =====================
def sample_background_task(x: int):
    print(f"[TASK] running, x = {x}")
    if x < 0:
        raise RuntimeError("模拟任务失败，触发重试")
    return x * 2



def test_rq():
    # =====================
    # Label Studio 风格：全局redis连接，和LS settings里REDIS_URL对应
    # =====================
    redis_conn = redis.Redis(host="localhost", port=6379, db=0)

    # 任务队列，LS里很多任务用 default 队列
    task_queue = Queue("default", connection=redis_conn)
    # 重试配置：最多重试2次，间隔 [3,5] 秒，LS源码大量这样写
    retry_policy = Retry(max=2, interval=[3, 5])

    # 入队任务，携带重试策略
    job: Job = task_queue.enqueue(
        sample_background_task,
        -1,  # 传负数，让它抛异常，触发重试
        retry=retry_policy,
        job_timeout=60,
    )
    job_id = job.id

    print(f"Job enqueued, job_id: {job.id}")
    print("=== 现在新开终端启动 worker 消费任务 ===")
    print("rq worker default --with-scheduler")

    # 在文件末尾追加
    # worker = Worker([task_queue], connection=redis_conn)
    # worker.work()


    # --------------------------
    # LS 风格：轮询查询任务状态
    # LS 前端轮询、后端接口就是这套逻辑
    # --------------------------
    for _ in range(20):
        # 重点：fetch 从redis拉取最新job（和LS源码一致）
        job = Job.fetch(job_id, connection=redis_conn)
        status = job.get_status()

        print(f"job status: {status}")

        if status == "finished":
            print(f"✅ 任务成功，result = {job.result}")
            break
        elif status == "failed":
            print(f"❌ 任务失败，异常信息：{job.exc_info}")
            break
        elif status in ("queued", "started", "deferred"):
            # queued：排队；started：正在执行；deferred：等待重试
            time.sleep(1)
        else:
            print(f"未知状态：{status}")
            time.sleep(1)



if __name__ == "__main__":
    pass

