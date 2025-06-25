resource "aws_apigatewayv2_api" "waiting_room_api" {
  name          = "WaitingRoomAPI"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["*"]
  }
}

resource "aws_apigatewayv2_integration" "join_queue_lambda_integration" {
  api_id           = aws_apigatewayv2_api.waiting_room_api.id
  integration_type = "AWS_PROXY"

  integration_uri = aws_lambda_function.join_queue_function.invoke_arn

  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "join_queue_route" {
  api_id    = aws_apigatewayv2_api.waiting_room_api.id
  route_key = "POST /join"
  target    = "integrations/${aws_apigatewayv2_integration.join_queue_lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "api_stage" {
  api_id      = aws_apigatewayv2_api.waiting_room_api.id
  name        = "v1"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway_invoke_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.join_queue_function.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.waiting_room_api.execution_arn}/*/${aws_apigatewayv2_route.join_queue_route.route_key}"
}

output "api_endpoint" {
  description = "The base URL for the Waiting Room API."
  value       = aws_apigatewayv2_stage.api_stage.invoke_url
}

