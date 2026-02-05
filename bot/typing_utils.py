from typing import Any, TypeAlias, cast

from telegram.ext import Application, BaseHandler, JobQueue, ContextTypes

App: TypeAlias = Application[Any, Any, Any, Any, Any, Any]
JobQueueT: TypeAlias = JobQueue[Any]
BaseHandlerT: TypeAlias = BaseHandler[Any, Any, Any]


def get_job_queue(context: ContextTypes.DEFAULT_TYPE) -> JobQueueT | None:
    return cast(JobQueueT | None, getattr(context, "job_queue", None))
