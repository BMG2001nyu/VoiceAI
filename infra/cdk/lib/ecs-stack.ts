import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export interface EcsStackProps extends cdk.StackProps {
    vpc: ec2.Vpc;
    fargateSg: ec2.SecurityGroup;
}

export class EcsStack extends cdk.Stack {
    public readonly cluster: ecs.Cluster;
    public readonly service: ecs.FargateService;

    constructor(scope: Construct, id: string, props: EcsStackProps) {
        super(scope, id, props);

        const { vpc, fargateSg } = props;

        // 1. Create the ECS Cluster
        this.cluster = new ecs.Cluster(this, 'MissionControlCluster', {
            vpc,
            clusterName: 'mission-control-cluster',
        });

        // 2. Task Execution Role
        const taskExecutionRole = new iam.Role(this, 'FargateTaskExecutionRole', {
            assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            managedPolicies: [
                iam.ManagedPolicy.fromAwsManagedPolicyName(
                    'service-role/AmazonECSTaskExecutionRolePolicy',
                ),
            ],
        });

        // 3. Task Definition (placeholder)
        const taskDefinition = new ecs.FargateTaskDefinition(this, 'BackendTaskDef', {
            memoryLimitMiB: 512,
            cpu: 256,
            executionRole: taskExecutionRole,
        });

        taskDefinition.addContainer('BackendContainer', {
            image: ecs.ContainerImage.fromRegistry('amazon/amazon-ecs-sample'),
            logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'MissionControlBackend' }),
            portMappings: [{ containerPort: 8000 }, { containerPort: 80 }],
        });

        // 4. Fargate Service
        this.service = new ecs.FargateService(this, 'BackendFargateService', {
            cluster: this.cluster,
            taskDefinition,
            desiredCount: 1,
            securityGroups: [fargateSg],
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
            assignPublicIp: false,
        });

        // 5. Application Load Balancer
        const albSg = new ec2.SecurityGroup(this, 'AlbSg', {
            vpc,
            description: 'Security group for the Application Load Balancer',
            allowAllOutbound: true,
        });
        albSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow HTTP from anywhere');

        fargateSg.addIngressRule(albSg, ec2.Port.tcp(8000), 'Allow ALB to Backend on 8000');
        fargateSg.addIngressRule(albSg, ec2.Port.tcp(80), 'Allow ALB to Backend on 80');

        const alb = new elbv2.ApplicationLoadBalancer(this, 'MissionControlAlb', {
            vpc,
            internetFacing: true,
            securityGroup: albSg,
            idleTimeout: cdk.Duration.seconds(300),
        });

        // 6. Listener + Target Group
        const listener = alb.addListener('HttpListener', {
            port: 80,
            protocol: elbv2.ApplicationProtocol.HTTP,
        });

        const targetGroup = listener.addTargets('BackendTarget', {
            port: 80,
            targets: [
                this.service.loadBalancerTarget({
                    containerName: 'BackendContainer',
                    containerPort: 80,
                }),
            ],
            healthCheck: {
                path: '/',
                healthyHttpCodes: '200,301',
            },
        });

        targetGroup.setAttribute('stickiness.enabled', 'true');
        targetGroup.setAttribute('stickiness.lb_cookie.duration_seconds', '86400');

        // 7. Outputs
        const albDns = alb.loadBalancerDnsName;
        new cdk.CfnOutput(this, 'AlbDnsOutput', { value: albDns });
        new ssm.StringParameter(this, 'AlbDnsSsm', {
            parameterName: '/mission-control/alb-dns',
            stringValue: albDns,
        });

        new cdk.CfnOutput(this, 'ClusterArnOutput', { value: this.cluster.clusterArn });
        new cdk.CfnOutput(this, 'FargateServiceNameOutput', {
            value: this.service.serviceName,
        });
    }
}
