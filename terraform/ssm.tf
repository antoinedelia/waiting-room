resource "aws_ssm_parameter" "waiting_room_enabled" {
  name  = "/waiting-room/config/enabled"
  type  = "String"
  value = "true"
}
