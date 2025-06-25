data "archive_file" "process_queue_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src/process_queue_function"
  output_path = "${path.module}/dist/process_queue_function.zip"
}

resource "aws_iam_role" "process_queue_lambda_role" {
  name = "ProcessQueueLambdaRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "process_queue_lambda_policy" {
  name        = "ProcessQueueLambdaPolicy"
  description = "Policy for the Process Queue Lambda function"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        # Permission to read and delete messages from the SQS queue
        Effect = "Allow",
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:DeleteMessageBatch",
          "sqs:GetQueueAttributes"
        ],
        Resource = aws_sqs_queue.waiting_room_queue.arn
      },
      {
        Effect   = "Allow",
        Action   = "dynamodb:UpdateItem",
        Resource = aws_dynamodb_table.waiting_room_table.arn
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "process_queue_lambda_attachment" {
  role       = aws_iam_role.process_queue_lambda_role.name
  policy_arn = aws_iam_policy.process_queue_lambda_policy.arn
}

resource "aws_lambda_function" "process_queue_function" {
  function_name = "process-queue-function"
  role          = aws_iam_role.process_queue_lambda_role.arn

  filename         = data.archive_file.process_queue_lambda_zip.output_path
  source_code_hash = data.archive_file.process_queue_lambda_zip.output_base64sha256

  handler = "main.lambda_handler"
  runtime = "python3.13"
  timeout = 30

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.waiting_room_table.name
      SQS_QUEUE_URL       = aws_sqs_queue.waiting_room_queue.id
      USERS_TO_PROCESS    = "100" # Let in 100 users per minute
    }
  }
}

resource "aws_cloudwatch_event_rule" "process_queue_schedule" {
  name                = "every-one-minute"
  description         = "Fires every minute to process the waiting room queue"
  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "process_queue_lambda_target" {
  rule      = aws_cloudwatch_event_rule.process_queue_schedule.name
  target_id = "TriggerProcessQueueLambda"
  arn       = aws_lambda_function.process_queue_function.arn
}

resource "aws_lambda_permission" "eventbridge_invoke_permission" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_queue_function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.process_queue_schedule.arn
}

