resource "aws_sqs_queue" "waiting_room_queue" {
  name = "waiting-room-queue"

  # The visibility timeout determines how long a message is hidden from other
  # consumers after it has been read by one. This should be longer than the
  # expected processing time of the Lambda function.
  visibility_timeout_seconds = 60

  # The maximum time a message will be retained in the queue before being deleted.
  message_retention_seconds = 345600 # 4 days, a safe upper limit

}
