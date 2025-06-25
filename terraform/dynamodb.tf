resource "aws_dynamodb_table" "waiting_room_table" {
  name           = "WaitingRoom"
  billing_mode   = "PAY_PER_REQUEST" # Good for unpredictable traffic
  hash_key       = "token"

  attribute {
    name = "token"
    type = "S" # S for String
  }

  # Enable DynamoDB's Time To Live (TTL) feature on the 'expiresAt' attribute
  # This will automatically delete items when the current time exceeds this timestamp
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }
}