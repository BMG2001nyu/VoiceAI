import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export interface RdsStackProps extends cdk.StackProps {
    vpc: ec2.Vpc;
    rdsSg: ec2.SecurityGroup;
}

export class RdsStack extends cdk.Stack {
    public readonly dbEndpoint: string;
    public readonly dbSecretArn: string;

    constructor(scope: Construct, id: string, props: RdsStackProps) {
        super(scope, id, props);

        const { vpc, rdsSg } = props;

        // 1. Postgres 16 instance with Secrets Manager credentials
        const instance = new rds.DatabaseInstance(this, 'MissionControlDb', {
            engine: rds.DatabaseInstanceEngine.postgres({
                version: rds.PostgresEngineVersion.VER_16,
            }),
            instanceType: ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO,
            ),
            vpc,
            vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
            securityGroups: [rdsSg],
            databaseName: 'missioncontrol',
            credentials: rds.Credentials.fromGeneratedSecret('mc'),
            allocatedStorage: 20,
            storageType: rds.StorageType.GP3,
            multiAz: false,
            deletionProtection: false,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            backupRetention: cdk.Duration.days(7),
        });

        this.dbEndpoint = instance.dbInstanceEndpointAddress;
        this.dbSecretArn = instance.secret?.secretArn ?? '';

        // 2. Outputs
        new cdk.CfnOutput(this, 'RdsEndpointOutput', {
            value: this.dbEndpoint,
            description: 'RDS Postgres endpoint address',
        });

        new cdk.CfnOutput(this, 'RdsSecretArnOutput', {
            value: this.dbSecretArn,
            description: 'ARN of the Secrets Manager secret for DB credentials',
        });

        new ssm.StringParameter(this, 'RdsEndpointSsm', {
            parameterName: '/mission-control/rds-endpoint',
            stringValue: this.dbEndpoint,
            description: 'RDS Postgres endpoint for Mission Control',
        });

        new ssm.StringParameter(this, 'RdsSecretArnSsm', {
            parameterName: '/mission-control/rds-secret-arn',
            stringValue: this.dbSecretArn,
            description: 'ARN of the DB credentials secret',
        });
    }
}
