from __future__ import annotations

from aws_cdk import Duration, Stack
from aws_cdk.aws_sqs import DeadLetterQueue, Queue


class SQSCreator:
    def __init__(
        self,
        scope: Stack,
        queue_prefix: str,
        *,
        visibility_timeout_sec: int | None,
    ) -> None:
        self.scope = scope
        self.dead_queue = Queue(
            self.scope,
            queue_prefix + "_dead",
            queue_name=queue_prefix + "_dead",
        )

        self.queue = Queue(
            self.scope,
            queue_prefix + "_waiting",
            queue_name=queue_prefix + "_waiting",
            visibility_timeout=(
                Duration.seconds(visibility_timeout_sec)
                if visibility_timeout_sec is not None
                else None
            ),
            dead_letter_queue=DeadLetterQueue(
                queue=self.dead_queue, max_receive_count=3
            ),
        )
