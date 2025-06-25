resource "aws_s3_bucket" "main_website_bucket" {
}

resource "aws_s3_bucket_public_access_block" "main_website_public_access" {
  bucket                  = aws_s3_bucket.main_website_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "main_website_index_html" {
  bucket       = aws_s3_bucket.main_website_bucket.id
  key          = "index.html"
  source       = "${path.module}/../frontend_main/index.html"
  content_type = "text/html"
  etag         = filemd5("${path.module}/../frontend_main/index.html")
}

resource "aws_cloudfront_origin_access_identity" "main_website_oai" {
  comment = "OAI for the main website frontend"
}

resource "aws_s3_bucket_policy" "main_website_bucket_policy" {
  bucket = aws_s3_bucket.main_website_bucket.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { AWS = aws_cloudfront_origin_access_identity.main_website_oai.iam_arn },
      Action    = "s3:GetObject",
      Resource  = "${aws_s3_bucket.main_website_bucket.arn}/*"
    }]
  })
}

resource "aws_cloudfront_distribution" "main_website_distribution" {
  origin {
    domain_name = aws_s3_bucket.main_website_bucket.bucket_regional_domain_name
    origin_id   = "S3-MainWebsite"
    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main_website_oai.cloudfront_access_identity_path
    }
  }

  enabled             = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-MainWebsite"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }

    lambda_function_association {
      event_type   = "viewer-request"
      lambda_arn   = aws_lambda_function.gatekeeper_function.qualified_arn
      include_body = false
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

}

output "main_website_url" {
  description = "The URL for the main website."
  value       = "https://${aws_cloudfront_distribution.main_website_distribution.domain_name}"
}
