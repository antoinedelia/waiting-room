resource "aws_apigatewayv2_api" "waiting_room_api" {
  name          = "WaitingRoomAPI"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["*"]
  }
}


resource "aws_apigatewayv2_stage" "api_stage" {
  api_id      = aws_apigatewayv2_api.waiting_room_api.id
  name        = "v1"
  auto_deploy = true
}

output "api_endpoint" {
  description = "The base URL for the Waiting Room API."
  value       = aws_apigatewayv2_stage.api_stage.invoke_url
}
