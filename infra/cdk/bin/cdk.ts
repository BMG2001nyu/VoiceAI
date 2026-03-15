#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { VpcStack } from '../lib/vpc-stack';
import { EcsStack } from '../lib/ecs-stack';
import { RedisStack } from '../lib/redis-stack';
import { RdsStack } from '../lib/rds-stack';
import { S3Stack } from '../lib/s3-stack';
import { OpenSearchStack } from '../lib/opensearch-stack';
import { IamStack } from '../lib/iam-stack';
import { DashboardsStack } from '../lib/dashboards-stack';

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION,
};

// 1. VPC + security groups (foundation for all networking stacks)
const vpcStack = new VpcStack(app, 'MissionControlVpc', { env });

// 2. ECS Fargate cluster + ALB (depends on VPC + fargate SG)
const ecsStack = new EcsStack(app, 'MissionControlEcs', {
  env,
  vpc: vpcStack.vpc,
  fargateSg: vpcStack.fargateSg,
});

// 3. ElastiCache Redis 7 (depends on VPC + redis SG)
const redisStack = new RedisStack(app, 'MissionControlRedis', {
  env,
  vpc: vpcStack.vpc,
  redisSg: vpcStack.redisSg,
});

// 4. RDS Postgres 16 (depends on VPC + rds SG)
const rdsStack = new RdsStack(app, 'MissionControlRds', {
  env,
  vpc: vpcStack.vpc,
  rdsSg: vpcStack.rdsSg,
});

// 5. S3 evidence bucket (independent)
const s3Stack = new S3Stack(app, 'MissionControlS3', { env });

// 6. OpenSearch Serverless vector collection (independent)
const opensearchStack = new OpenSearchStack(app, 'MissionControlOpenSearch', { env });

// 7. IAM task role (depends on S3, OpenSearch, RDS for resource ARNs)
const iamStack = new IamStack(app, 'MissionControlIam', {
  env,
  evidenceBucketArn: s3Stack.bucketArn,
  opensearchCollectionArn: opensearchStack.collectionArn,
  dbSecretArn: rdsStack.dbSecretArn,
});

// 8. CloudWatch Dashboard + Alarms (independent — reads custom metrics namespace)
new DashboardsStack(app, 'MissionControlDashboards', { env });
