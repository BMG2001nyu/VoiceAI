#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { VpcStack } from '../lib/vpc-stack';
import { EcsStack } from '../lib/ecs-stack';

const app = new cdk.App();

const vpcStack = new VpcStack(app, 'MissionControlVpc', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
});

new EcsStack(app, 'MissionControlEcs', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  vpc: vpcStack.vpc,
});
