# First, we package the python function code into a zip file.
data "archive_file" "join_queue_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src/join_queue_function"
  output_path = "${path.module}/dist/join_queue_function.zip"
}

# ------------------------------------------------------------------------------
# IAM ROLE FOR THE LAMBDA FUNCTION
# ------------------------------------------------------------------------------
resource "aws_iam_role" "join_queue_lambda_role" {
  name = "JoinQueueLambdaRole"

  # Trust policy that allows Lambda to assume this role
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy that grants our function necessary permissions
resource "aws_iam_policy" "join_queue_lambda_policy" {
  name        = "JoinQueueLambdaPolicy"
  description = "Policy for the Join Queue Lambda function"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        # Permission to write to the DynamoDB table
        Effect   = "Allow",
        Action   = "dynamodb:PutItem",
        Resource = aws_dynamodb_table.waiting_room_table.arn
      },
      {
        # Permission to send messages to the SQS queue
        Effect   = "Allow",
        Action   = "sqs:SendMessage",
        Resource = aws_sqs_queue.waiting_room_queue.arn
      },
      {
        # Permission to write logs to CloudWatch
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

# Attach the policy to the role
resource "aws_iam_role_policy_attachment" "join_queue_lambda_attachment" {
  role       = aws_iam_role.join_queue_lambda_role.name
  policy_arn = aws_iam_policy.join_queue_lambda_policy.arn
}

# ------------------------------------------------------------------------------
# LAMBDA FUNCTION RESOURCE
# ------------------------------------------------------------------------------
resource "aws_lambda_function" "join_queue_function" {
  function_name = "join-queue-function"
  role          = aws_iam_role.join_queue_lambda_role.arn

  # Reference the zip file we created above
  filename         = data.archive_file.join_queue_lambda_zip.output_path
  source_code_hash = data.archive_file.join_queue_lambda_zip.output_base64sha256

  handler = "main.lambda_handler"
  runtime = "python3.13"

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.waiting_room_table.name
      SQS_QUEUE_URL       = aws_sqs_queue.waiting_room_queue.id # .id is the URL for SQS queues
    }
  }
}
