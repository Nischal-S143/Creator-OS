"""Runs a real worker against the local Redis-compatible broker, without Docker."""

import uuid

from celery.contrib.testing.worker import start_worker

from app.workers.celery_app import celery_app, ping


def test_worker_runs_a_task_through_the_broker():
    queue = f"test-{uuid.uuid4().hex[:8]}"
    with start_worker(celery_app, pool="solo", queues=[queue], perform_ping_check=False):
        result = ping.apply_async(queue=queue)
        assert result.get(timeout=20) == "pong"
