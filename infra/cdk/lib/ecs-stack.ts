import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export interface EcsStackProps extends cdk.StackProps {
    vpc: ec2.Vpc;
}

export class EcsStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: EcsStackProps) {
        super(scope, id, props);

        const { vpc } = props;

        // 1. Create the ECS Cluster
        const cluster = new ecs.Cluster(this, 'MissionControlCluster', {
            vpc,
            clusterName: 'mission-control-cluster',
        });

        // 1.5 Create Security Groups (Moved from VpcStack to prevent cyclic dependency)
        const fargateSg = new ec2.SecurityGroup(this, 'FargateSg', {
            vpc: vpc,
            description: 'Security group for the Fargate backend service',
            allowAllOutbound: true,
        });

        const redisSg = new ec2.SecurityGroup(this, 'RedisSg', {
            vpc: vpc,
            description: 'Security group for Redis ElastiCache cluster',
            allowAllOutbound: false,
        });
        redisSg.addIngressRule(fargateSg, ec2.Port.tcp(6379), 'Allow inbound from Fargate');

        const rdsSg = new ec2.SecurityGroup(this, 'RdsSg', {
            vpc: vpc,
            description: 'Security group for Postgres RDS instance',
            allowAllOutbound: false,
        });
        rdsSg.addIngressRule(fargateSg, ec2.Port.tcp(5432), 'Allow inbound from Fargate');


        // 2. Define the Fargate Task Execution Role
        const taskExecutionRole = new iam.Role(this, 'FargateTaskExecutionRole', {
            assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
            ],
        });

        // 3. Define the Fargate Task Definition (placeholder for backend)
        const taskDefinition = new ecs.FargateTaskDefinition(this, 'BackendTaskDef', {
            memoryLimitMiB: 512, // Smallest size for demo cost savings
            cpu: 256,
            executionRole: taskExecutionRole,
        });

        // Use a simple sample image for the placeholder
        const container = taskDefinition.addContainer('BackendContainer', {
            image: ecs.ContainerImage.fromRegistry('amazon/amazon-ecs-sample'),
            logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'MissionControlBackend' }),
            portMappings: [{ containerPort: 8000 }, { containerPort: 80 }],
        });

        // 4. Create the Fargate Service
        const fargateService = new ecs.FargateService(this, 'BackendFargateService', {
            cluster,
            taskDefinition,
            desiredCount: 1,
            securityGroups: [fargateSg],
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS }, // Run in private subnets
            assignPublicIp: false,
        });

        // 5. Create the Application Load Balancer
        const albSg = new ec2.SecurityGroup(this, 'AlbSg', {
            vpc,
            description: 'Security group for the Application Load Balancer',
            allowAllOutbound: true,
        });
        // Allow internet to access ALB on port 80
        albSg.addIngressRule(
            ec2.Peer.anyIpv4(),
            ec2.Port.tcp(80),
            'Allow HTTP from anywhere'
        );

        // Allow ALB to access Fargate on port 8000 (Backend) and port 80 (Placeholder)
        // The placeholder amazon-ecs-sample uses port 80, but our backend will use 8000.
        fargateSg.addIngressRule(albSg, ec2.Port.tcp(8000), 'Allow ALB to access Backend on 8000');
        fargateSg.addIngressRule(albSg, ec2.Port.tcp(80), 'Allow ALB to access Backend on 80');

        const alb = new elbv2.ApplicationLoadBalancer(this, 'MissionControlAlb', {
            vpc,
            internetFacing: true, // Needs to be accessible from public
            securityGroup: albSg,
            idleTimeout: cdk.Duration.seconds(300), // CRITICAL: 300s timeout for WebSocket support
        });

        // 6. Connect ALB to the Fargate Service via Target Group / Listener
        const listener = alb.addListener('HttpListener', {
            port: 80,
            protocol: elbv2.ApplicationProtocol.HTTP,
        });

        const targetGroup = listener.addTargets('BackendTarget', {
            port: 80, // Target the placeholder container port
            targets: [
                fargateService.loadBalancerTarget({
                    containerName: 'BackendContainer',
                    containerPort: 80, // Matches port of the amazon-ecs-sample image
                }),
            ],
            healthCheck: {
                path: '/',
                healthyHttpCodes: '200,301',
            },
        });

        // CRITICAL: Enable stickiness for WebSocket session affinity
        targetGroup.setAttribute('stickiness.enabled', 'true');
        targetGroup.setAttribute('stickiness.lb_cookie.duration_seconds', '86400');

        // 7. Outputs and SSM Parameters
        const albDns = alb.loadBalancerDnsName;
        new cdk.CfnOutput(this, 'AlbDnsOutput', { value: albDns });
        new ssm.StringParameter(this, 'AlbDnsSsm', {
            parameterName: '/mission-control/alb-dns',
            stringValue: albDns,
        });

        new cdk.CfnOutput(this, 'ClusterArnOutput', { value: cluster.clusterArn });
        new cdk.CfnOutput(this, 'FargateServiceNameOutput', { value: fargateService.serviceName });
    }
}
