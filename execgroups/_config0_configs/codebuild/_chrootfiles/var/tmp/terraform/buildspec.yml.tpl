version: 0.2

env:
  variables:
    code_dir: /tmp/code/src
    AWS_DEFAULT_REGION: ${aws_default_region}
    AWS_ACCOUNT_ID: ${aws_account_id}
    GIT_URL: ${git_url}
    S3_BUCKET: ${s3_bucket}
  parameter-store:
    ssh_key: ${ssm_ssh_key}
phases:
  pre_build:
    on-failure: ABORT
    commands:   
      - export COMMIT_HASH=$${COMMIT_HASH:=$CODEBUILD_RESOLVED_SOURCE_VERSION}
      - mkdir -p ~/.ssh
      - echo $ssh_key | base64 -d > ~/.ssh/id_rsa   
      - chmod 600 ~/.ssh/id_rsa
      - eval "$(ssh-agent -s)"
      - mkdir -p $code_dir
      - cd $code_dir
      - git init
      - git remote add origin $GIT_URL
      - git fetch --quiet origin 
      - git checkout --quiet -f $COMMIT_HASH
      - rm -rf .git
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com

  build:
    on-failure: ABORT
    commands:   
      - docker build -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$COMMIT_HASH . -f Dockerfile
      - docker tag $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$COMMIT_HASH $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:latest

  post_build:
    commands:
      - echo "export CODEBUILD_BUILD_ARN=$CODEBUILD_BUILD_ARN" > /tmp/codebuild.env ; echo "export CODEBUILD_BUILD_ID=$CODEBUILD_BUILD_ID" >> /tmp/codebuild.env ; echo "export CODEBUILD_BUILD_NUMBER=$CODEBUILD_BUILD_NUMBER" >> /tmp/codebuild.env
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME --all-tags
      - echo "" ; cat /tmp/codebuild.env ; echo ""

