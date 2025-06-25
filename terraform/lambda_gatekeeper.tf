# This resource creates a config.json file on the local filesystem where
# terraform is being run. This file will be included in the Lambda zip.
# This is to overcome the limitation of Lambda@Edge that cannot have environment variables.
resource "local_file" "gatekeeper_lambda_config" {
  content = jsonencode({
    ssm_parameter_name = aws_ssm_parameter.waiting_room_enabled.name
    waiting_room_url   = "https://${aws_cloudfront_distribution.waiting_room_distribution.domain_name}"
  })
  filename = "${path.module}/src/gatekeeper_function/config.json"
}

data "archive_file" "gatekeeper_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src/gatekeeper_function"
  output_path = "${path.module}/dist/gatekeeper_function.zip"

  depends_on = [
    local_file.gatekeeper_lambda_config
  ]
}

resource "aws_iam_role" "gatekeeper_lambda_role" {
  name = "GatekeeperLambdaEdgeRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = [
          "lambda.amazonaws.com",
          "edgelambda.amazonaws.com"
        ]
      },
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "gatekeeper_lambda_policy" {
  name = "GatekeeperLambdaEdgePolicy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        # Permission to write logs to CloudWatch in different regions
        Effect   = "Allow",
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        # Permission to read the SSM Parameter
        Effect   = "Allow",
        Action   = "ssm:GetParameter",
        Resource = aws_ssm_parameter.waiting_room_enabled.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "gatekeeper_lambda_attachment" {
  role       = aws_iam_role.gatekeeper_lambda_role.name
  policy_arn = aws_iam_policy.gatekeeper_lambda_policy.arn
}

# The Lambda@Edge function itself
resource "aws_lambda_function" "gatekeeper_function" {
  region        = "us-east-1"
  function_name = "gatekeeper-function"
  role          = aws_iam_role.gatekeeper_lambda_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.13"
  publish       = true # MUST publish a version to use with Lambda@Edge

  environment {
    variables = {
      SSM_PARAMETER_NAME          = aws_ssm_parameter.waiting_room_enabled.name
      CLOUDFRONT_WAITING_ROOM_URL = "https://${aws_cloudfront_distribution.waiting_room_distribution.domain_name}"
    }
  }

  filename         = data.archive_file.gatekeeper_lambda_zip.output_path
  source_code_hash = data.archive_file.gatekeeper_lambda_zip.output_base64sha256
}
