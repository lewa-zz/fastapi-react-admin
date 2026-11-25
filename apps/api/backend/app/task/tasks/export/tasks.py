"""后台导出（#11 · v0.4）。行数超过 `EXPORT_SYNC_MAX_ROWS` 时，导出接口投递 `export.run`。

**完成通知不在这里发。** `export_service.execute()` 是同步（小批量，请求里跑）和异步（大批量，worker 里跑）
唯一共同的完成出口，它结束时统一给发起人发一条站内消息（成功 / 失败都发）——
这一层只负责在 worker 里把任务跑起来、记日志。在这里再发一次的话，大批量的人会收到两条一模一样的消息。

🔴 **worker 不走 FastAPI 的路由装载**：各资源的导出定义（`app/admin/dataio.py`、`plugin/*/dataio.py`）
在 web 进程里是路由模块 import 时登记的，worker 里没人 import 它们 —— 不在这里显式加载，
任务一跑就是「资源不可用」。
"""

from backend.app.admin.service.export_service import export_service
from backend.app.task.celery import celery_app
from backend.app.task.tasks.base import with_timeout
from backend.common.dataio.exporting import load_dataio_modules
from backend.common.enums import ExportJobStatus
from backend.common.log import log

load_dataio_modules()


@celery_app.task(name='export.run')
@with_timeout()
async def run_export(job_id: str) -> str:
    """生成一份导出。`job_id` 用字符串传：雪花 ID 过 JSON 序列化，别让任何一环有机会把它当数字（硬纪律 6）"""
    job = await export_service.execute(int(job_id))
    if job is None:
        msg = f'导出 {job_id}：没抢到（别的 worker 在做，或已经结束）'
        log.info(msg)
        return msg

    msg = f'导出 {job_id}：{ExportJobStatus(job.status).name}，{job.row_count or 0} 行'
    log.info(msg)
    return msg
