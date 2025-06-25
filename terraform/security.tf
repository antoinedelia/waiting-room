resource "random_password" "jwt_secret_key" {
  length           = 48
  special          = true
  override_special = "!#%&()+-="
}