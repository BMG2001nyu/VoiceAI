import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export interface RedisStackProps extends cdk.StackProps {
    vpc: ec2.Vpc;
    redisSg: ec2.SecurityGroup;
}

export class RedisStack extends cdk.Stack {
    public readonly redisEndpoint: string;

    constructor(scope: Construct, id: string, props: RedisStackProps) {
        super(scope, id, props);

        const { vpc, redisSg } = props;

        // 1. Subnet group — place Redis in private subnets
        const privateSubnetIds = vpc.privateSubnets.map((s) => s.subnetId);

        const subnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
            description: 'Private subnets for Mission Control Redis',
            subnetIds: privateSubnetIds,
            cacheSubnetGroupName: 'mission-control-redis-subnets',
        });

        // 2. Single-node Redis 7 cluster (cost-optimised)
        const redisCluster = new elasticache.CfnCacheCluster(this, 'RedisCluster', {
            engine: 'redis',
            engineVersion: '7.1',
            cacheNodeType: 'cache.t3.micro',
            numCacheNodes: 1,
            clusterName: 'mission-control-redis',
            cacheSubnetGroupName: subnetGroup.cacheSubnetGroupName,
            vpcSecurityGroupIds: [redisSg.securityGroupId],
        });

        redisCluster.addDependency(subnetGroup);

        // 3. Derive endpoint (single-node cluster uses redisEndpointAddress)
        this.redisEndpoint = redisCluster.attrRedisEndpointAddress;

        // 4. Outputs
        new cdk.CfnOutput(this, 'RedisEndpointOutput', {
            value: this.redisEndpoint,
            description: 'Redis primary endpoint address',
        });

        new cdk.CfnOutput(this, 'RedisPortOutput', {
            value: redisCluster.attrRedisEndpointPort,
            description: 'Redis port',
        });

        new ssm.StringParameter(this, 'RedisEndpointSsm', {
            parameterName: '/mission-control/redis-endpoint',
            stringValue: this.redisEndpoint,
            description: 'Redis primary endpoint for Mission Control',
        });
    }
}
