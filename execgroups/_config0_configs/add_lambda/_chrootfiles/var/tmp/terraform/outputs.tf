output "s3_key" {
  description = "The S3 key of the Lambda function's deployment package"
  value       = aws_lambda_function.default.s3_key
}

output "s3_bucket" {
  description = "The S3 bucket containing the Lambda function's deployment package"
  value       = aws_lambda_function.default.s3_bucket
}

output "memory_size" {
  description = "The memory size allocated to the Lambda function"
  value       = aws_lambda_function.default.memory_size
}

output "role" {
  description = "The IAM role ARN attached to the Lambda function"
  value       = aws_lambda_function.default.role
}

output "runtime" {
  description = "The runtime environment of the Lambda function"
  value       = aws_lambda_function.default.runtime
}

output "handler" {
  description = "The handler of the Lambda function"
  value       = aws_lambda_function.default.handler
}

output "invoke_arn" {
  description = "The ARN to be used for invoking the Lambda function from API Gateway"
  value       = aws_lambda_function.default.invoke_arn
}

output "function_name" {
  description = "The name of the Lambda function"
  value       = aws_lambda_function.default.function_name
}

output "layers" {
  description = "The list of Lambda layer ARNs attached to the function"
  value       = aws_lambda_function.default.layers
}

output "timeout" {
  description = "The function execution timeout in seconds"
  value       = aws_lambda_function.default.timeout
}

output "arn" {
  description = "The ARN of the Lambda function"
  value       = aws_lambda_function.default.arn
}

