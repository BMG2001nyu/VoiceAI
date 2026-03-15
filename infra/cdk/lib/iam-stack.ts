import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export interface IamStackProps extends cdk.StackProps {
    evidenceBucketArn: string;
    opensearchCollectionArn: string;
    dbSecretArn: string;
}

export class IamStack extends cdk.Stack {
    public readonly taskRole: iam.Role;

    constructor(scope: Construct, id: string, props: IamStackProps) {
        super(scope, id, props);

        const { evidenceBucketArn, opensearchCollectionArn, dbSecretArn } = props;

        // ECS Task Role with least-privilege policies
        this.taskRole = new iam.Role(this, 'EcsTaskRole', {
            assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
            description: 'Task role for Mission Control ECS containers',
        });

        // 1. Bedrock — invoke Nova models
        this.taskRole.addToPolicy(
            new iam.PolicyStatement({
                sid: 'BedrockInvoke',
                effect: iam.Effect.ALLOW,
                actions: [
                    'bedrock:InvokeModel',
                    'bedrock:InvokeModelWithResponseStream',
                ],
                resources: [
                    `arn:aws:bedrock:${this.region}::foundation-model/amazon.nova-*`,
                ],
            }),
        );

        // 2. S3 — read/write evidence objects
        this.taskRole.addToPolicy(
            new iam.PolicyStatement({
                sid: 'S3Evidence',
                effect: iam.Effect.ALLOW,
                actions: ['s3:PutObject', 's3:GetObject'],
                resources: [`${evidenceBucketArn}/*`],
            }),
        );

        // 3. OpenSearch Serverless — API access to vector collection
        this.taskRole.addToPolicy(
            new iam.PolicyStatement({
                sid: 'OpenSearchAccess',
                effect: iam.Effect.ALLOW,
                actions: ['aoss:APIAccessAll'],
                resources: [opensearchCollectionArn],
            }),
        );

        // 4. Secrets Manager — read DB credentials
        this.taskRole.addToPolicy(
            new iam.PolicyStatement({
                sid: 'SecretsManagerRead',
                effect: iam.Effect.ALLOW,
                actions: ['secretsmanager:GetSecretValue'],
                resources: [dbSecretArn],
            }),
        );

        // 5. CloudWatch — metrics and logs
        this.taskRole.addToPolicy(
            new iam.PolicyStatement({
                sid: 'CloudWatchMetrics',
                effect: iam.Effect.ALLOW,
                actions: ['cloudwatch:PutMetricData'],
                resources: ['*'],
                conditions: {
                    StringEquals: {
                        'cloudwatch:namespace': 'MissionControl',
                    },
                },
            }),
        );

        this.taskRole.addToPolicy(
            new iam.PolicyStatement({
                sid: 'CloudWatchLogs',
                effect: iam.Effect.ALLOW,
                actions: ['logs:CreateLogStream', 'logs:PutLogEvents'],
                resources: [
                    `arn:aws:logs:${this.region}:${this.account}:log-group:/ecs/mission-control*`,
                ],
            }),
        );

        // Outputs
        new cdk.CfnOutput(this, 'TaskRoleArnOutput', {
            value: this.taskRole.roleArn,
            description: 'ECS task role ARN for Mission Control',
        });

        new ssm.StringParameter(this, 'TaskRoleArnSsm', {
            parameterName: '/mission-control/task-role-arn',
            stringValue: this.taskRole.roleArn,
            description: 'ECS task role ARN',
        });
    }
}
