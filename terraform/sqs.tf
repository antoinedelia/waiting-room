resource "aws_sqs_queue" "waiting_room_queue" {
  # FIFO queue names MUST end with the .fifo suffix.
  name = "waiting-room-queue.fifo"

  fifo_queue = true

  content_based_deduplication = true

  visibility_timeout_seconds = 60
  message_retention_seconds  = 345600
}
