#!/bin/bash

# Reely AWS Production Deployment Script
set -e

# Configuration
PROJECT_NAME="reely"
ENVIRONMENT="production"
REGION="us-east-1"
STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}-infrastructure"

echo "🚀 Starting AWS deployment for Reely..."

# Check AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install and configure AWS CLI first."
    exit 1
fi

# Check if logged in to AWS
aws sts get-caller-identity > /dev/null 2>&1 || {
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
}

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}"

echo "📋 Deployment Configuration:"
echo "   - Project: ${PROJECT_NAME}"
echo "   - Environment: ${ENVIRONMENT}"
echo "   - Region: ${REGION}"
echo "   - Account: ${ACCOUNT_ID}"
echo ""

# Collect deployment parameters
read -p "🔐 Enter domain name (e.g., api.reely.com): " DOMAIN_NAME
read -p "🔑 Enter EC2 Key Pair name: " KEY_PAIR_NAME
read -s -p "🔒 Enter database password: " DB_PASSWORD
echo ""

# Create ECR repository if it doesn't exist
echo "📦 Setting up ECR repository..."
aws ecr describe-repositories --repository-names ${PROJECT_NAME} --region ${REGION} 2>/dev/null || {
    echo "Creating ECR repository..."
    aws ecr create-repository --repository-name ${PROJECT_NAME} --region ${REGION}
}

# Build and push Docker image
echo "🏗️ Building Docker image..."
docker build -t ${PROJECT_NAME}:latest .

echo "🏷️ Tagging image for ECR..."
docker tag ${PROJECT_NAME}:latest ${ECR_REPOSITORY}:latest

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY}

echo "⬆️ Pushing image to ECR..."
docker push ${ECR_REPOSITORY}:latest

# Deploy CloudFormation stack
echo "☁️ Deploying CloudFormation infrastructure..."
aws cloudformation deploy \
    --template-file aws-infrastructure.yml \
    --stack-name ${STACK_NAME} \
    --parameter-overrides \
        ProjectName=${PROJECT_NAME} \
        Environment=${ENVIRONMENT} \
        DomainName=${DOMAIN_NAME} \
        KeyPairName=${KEY_PAIR_NAME} \
        DBPassword=${DB_PASSWORD} \
    --capabilities CAPABILITY_IAM \
    --region ${REGION}

# Get stack outputs
echo "📊 Getting infrastructure details..."
DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
    --output text \
    --region ${REGION})

REDIS_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`RedisEndpoint`].OutputValue' \
    --output text \
    --region ${REGION})

S3_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
    --output text \
    --region ${REGION})

ECS_CLUSTER=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' \
    --output text \
    --region ${REGION})

# Create CloudWatch Log Group
echo "📝 Creating CloudWatch log group..."
aws logs create-log-group --log-group-name "/ecs/${PROJECT_NAME}-${ENVIRONMENT}" --region ${REGION} 2>/dev/null || echo "Log group already exists"

# Store secrets in Parameter Store
echo "🔐 Storing secrets in AWS Parameter Store..."
echo "Please manually set the following parameters in AWS Systems Manager Parameter Store:"
echo "   - /reely/production/database_url"
echo "   - /reely/production/redis_url" 
echo "   - /reely/production/jwt_secret_key"
echo "   - /reely/production/openai_api_key"
echo "   - /reely/production/anthropic_api_key"
echo "   - /reely/production/stripe_secret_key"
echo "   - /reely/production/stripe_webhook_secret"
echo "   - /reely/production/aws_access_key_id"
echo "   - /reely/production/aws_secret_access_key"
echo "   - /reely/production/s3_bucket_name"

echo ""
echo "💡 Example parameter creation:"
echo "aws ssm put-parameter --name '/reely/production/database_url' --value 'postgresql://reely_user:${DB_PASSWORD}@${DB_ENDPOINT}:5432/reely' --type SecureString"
echo "aws ssm put-parameter --name '/reely/production/redis_url' --value 'redis://${REDIS_ENDPOINT}:6379/0' --type SecureString"
echo "aws ssm put-parameter --name '/reely/production/s3_bucket_name' --value '${S3_BUCKET}' --type String"

# Update ECS task definition
echo "📝 Updating ECS task definition..."
sed -e "s/ACCOUNT_ID/${ACCOUNT_ID}/g" \
    -e "s/REGION/${REGION}/g" \
    ecs-task-definition.json > ecs-task-definition-updated.json

# Register task definition
echo "📋 Registering ECS task definition..."
aws ecs register-task-definition \
    --cli-input-json file://ecs-task-definition-updated.json \
    --region ${REGION}

# Create ECS service
echo "🚀 Creating ECS service..."
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names "${PROJECT_NAME}-${ENVIRONMENT}-tg" \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text \
    --region ${REGION})

SUBNETS=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnet1`].OutputValue' \
    --output text \
    --region ${REGION}),$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`PublicSubnet2`].OutputValue' \
    --output text \
    --region ${REGION})

SECURITY_GROUP=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroup`].OutputValue' \
    --output text \
    --region ${REGION})

aws ecs create-service \
    --cluster ${ECS_CLUSTER} \
    --service-name "${PROJECT_NAME}-${ENVIRONMENT}-api" \
    --task-definition "${PROJECT_NAME}-${ENVIRONMENT}-api:1" \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNETS}],securityGroups=[${SECURITY_GROUP}],assignPublicIp=ENABLED}" \
    --load-balancers "targetGroupArn=${TARGET_GROUP_ARN},containerName=reely-api,containerPort=8000" \
    --region ${REGION} || echo "Service may already exist"

echo ""
echo "✅ AWS deployment completed!"
echo ""
echo "📋 Deployment Summary:"
echo "   - Domain: ${DOMAIN_NAME}"
echo "   - Database: ${DB_ENDPOINT}"
echo "   - Redis: ${REDIS_ENDPOINT}"
echo "   - S3 Bucket: ${S3_BUCKET}"
echo "   - ECS Cluster: ${ECS_CLUSTER}"
echo ""
echo "🔧 Next Steps:"
echo "1. Set up DNS records to point ${DOMAIN_NAME} to the ALB"
echo "2. Configure the Parameter Store secrets (see above)"
echo "3. Update Stripe webhook endpoints to point to your domain"
echo "4. Set up monitoring and alerting"
echo "5. Configure backup and disaster recovery"
echo ""
echo "🌐 Your Reely API will be available at: https://${DOMAIN_NAME}"

# Cleanup temporary files
rm -f ecs-task-definition-updated.json