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
            maxAzs: 2, // Spanning 2 Availability Zones for high availability
            natGateways: 1, // Single NAT Gateway for cost savings
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

        // Security groups are defined in their respective stacks (e.g., EcsStack) to prevent cyclic dependencies.
    }
}
