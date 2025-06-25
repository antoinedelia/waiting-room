resource "aws_s3_bucket" "waiting_room_bucket" {
}

resource "aws_s3_bucket_public_access_block" "waiting_room_public_access" {
  bucket                  = aws_s3_bucket.waiting_room_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "index_html" {
  bucket       = aws_s3_bucket.waiting_room_bucket.id
  key          = "index.html"
  source       = "${path.module}/../frontend_waiting_room/index.html"
  content_type = "text/html"

  etag = filemd5("${path.module}/../frontend_waiting_room/index.html")
}


resource "aws_cloudfront_origin_access_identity" "waiting_room_oai" {
  comment = "OAI for the virtual waiting room frontend"
}

resource "aws_s3_bucket_policy" "waiting_room_bucket_policy" {
  bucket = aws_s3_bucket.waiting_room_bucket.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        AWS = aws_cloudfront_origin_access_identity.waiting_room_oai.iam_arn
      },
      Action   = "s3:GetObject",
      Resource = "${aws_s3_bucket.waiting_room_bucket.arn}/*"
    }]
  })
}

resource "aws_cloudfront_distribution" "waiting_room_distribution" {
  origin {
    domain_name = aws_s3_bucket.waiting_room_bucket.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.frontend_bucket.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.waiting_room_oai.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend_bucket.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

output "waiting_room_url" {
  description = "The URL for the frontend waiting room website."
  value       = "https://${aws_cloudfront_distribution.waiting_room_distribution.domain_name}"
}
