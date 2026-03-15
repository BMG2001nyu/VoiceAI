import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export class VpcStack extends cdk.Stack {
    public readonly vpc: ec2.Vpc;
    public readonly fargateSg: ec2.SecurityGroup;
    public readonly redisSg: ec2.SecurityGroup;
    public readonly rdsSg: ec2.SecurityGroup;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        // 1. Create the VPC
        this.vpc = new ec2.Vpc(this, 'MissionControlVpc', {
            ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
            maxAzs: 2,
            natGateways: 1,
            subnetConfiguration: [
                {
                    cidrMask: 24,
                    name: 'Public',
                    subnetType: ec2.SubnetType.PUBLIC,
                },
                {
                    cidrMask: 24,
                    name: 'Private',
                    subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
                },
            ],
        });

        // 2. Security groups — shared across stacks via public readonly properties
        this.fargateSg = new ec2.SecurityGroup(this, 'FargateSg', {
            vpc: this.vpc,
            description: 'Security group for the Fargate backend service',
            allowAllOutbound: true,
        });

        this.redisSg = new ec2.SecurityGroup(this, 'RedisSg', {
            vpc: this.vpc,
            description: 'Security group for Redis ElastiCache cluster',
            allowAllOutbound: false,
        });
        this.redisSg.addIngressRule(
            this.fargateSg,
            ec2.Port.tcp(6379),
            'Allow inbound from Fargate',
        );

        this.rdsSg = new ec2.SecurityGroup(this, 'RdsSg', {
            vpc: this.vpc,
            description: 'Security group for Postgres RDS instance',
            allowAllOutbound: false,
        });
        this.rdsSg.addIngressRule(
            this.fargateSg,
            ec2.Port.tcp(5432),
            'Allow inbound from Fargate',
        );
    }
}
