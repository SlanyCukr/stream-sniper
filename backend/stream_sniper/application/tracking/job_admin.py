"""Application operations for processing-job administration."""

from dataclasses import dataclass

from ...database.gateways.tracking.processing_jobs_table_gateway import (
    count_processing_jobs_db,
    request_processing_job_cancellation_db,
    retry_failed_processing_job_db,
    select_processing_job_by_id_db,
    select_processing_jobs_db,
)
from .models import JOB_STATUS_FAILED, JobStatus, ProcessingJob


class ProcessingJobNotFoundError(LookupError):
    pass


class ProcessingJobConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProcessingJobPage:
    jobs: list[ProcessingJob]
    total: int


def list_processing_jobs(
    *,
    limit: int,
    offset: int,
    status: JobStatus | None,
    tracked_streamer_id: int | None,
) -> ProcessingJobPage:
    return ProcessingJobPage(
        jobs=select_processing_jobs_db(
            limit=limit,
            offset=offset,
            status=status,
            tracked_streamer_id=tracked_streamer_id,
        ),
        total=count_processing_jobs_db(status=status, tracked_streamer_id=tracked_streamer_id),
    )


def request_processing_job_cancellation(job_id: int) -> None:
    if select_processing_job_by_id_db(job_id) is None:
        raise ProcessingJobNotFoundError(job_id)
    if not request_processing_job_cancellation_db(job_id):
        raise ProcessingJobConflictError("Job is already terminal")


def retry_processing_job(job_id: int) -> None:
    job = select_processing_job_by_id_db(job_id)
    if job is None:
        raise ProcessingJobNotFoundError(job_id)
    if job.status != JOB_STATUS_FAILED:
        raise ProcessingJobConflictError("Only failed jobs can be retried")
    if not retry_failed_processing_job_db(job_id):
        raise ProcessingJobConflictError("Job state changed before retry")
