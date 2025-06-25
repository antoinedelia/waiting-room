data "archive_file" "check_status_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src/check_status_function"
  output_path = "${path.module}/dist/check_status_function.zip"
}

resource "aws_iam_role" "check_status_lambda_role" {
  name = "CheckStatusLambdaRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "check_status_lambda_policy" {
  name        = "CheckStatusLambdaPolicy"
  description = "Policy for the Check Status Lambda function"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "dynamodb:GetItem",
        Resource = aws_dynamodb_table.waiting_room_table.arn
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

resource "aws_iam_role_policy_attachment" "check_status_lambda_attachment" {
  role       = aws_iam_role.check_status_lambda_role.name
  policy_arn = aws_iam_policy.check_status_lambda_policy.arn
}

resource "aws_lambda_function" "check_status_function" {
  function_name = "check-status-function"
  role          = aws_iam_role.check_status_lambda_role.arn

  filename         = data.archive_file.check_status_lambda_zip.output_path
  source_code_hash = data.archive_file.check_status_lambda_zip.output_base64sha256

  handler = "main.lambda_handler"
  runtime = "python3.12"

  layers = ["arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p312-PyJWT:1"]

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.waiting_room_table.name
      JWT_SECRET_KEY      = random_password.jwt_secret_key.result
    }
  }
}


resource "aws_apigatewayv2_integration" "check_status_lambda_integration" {
  api_id                 = aws_apigatewayv2_api.waiting_room_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.check_status_function.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "check_status_route" {
  api_id    = aws_apigatewayv2_api.waiting_room_api.id
  route_key = "GET /status"
  target    = "integrations/${aws_apigatewayv2_integration.check_status_lambda_integration.id}"
}

resource "aws_lambda_permission" "api_gateway_invoke_check_status_permission" {
  statement_id  = "AllowAPIGatewayInvokeCheckStatus"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.check_status_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.waiting_room_api.execution_arn}/*/${replace(aws_apigatewayv2_route.check_status_route.route_key, " ", "")}"
}
