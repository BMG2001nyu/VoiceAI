import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export class S3Stack extends cdk.Stack {
    public readonly bucketName: string;
    public readonly bucketArn: string;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        const bucket = new s3.Bucket(this, 'EvidenceBucket', {
            bucketName: `mission-control-evidence-${this.account}-${this.region}`,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            encryption: s3.BucketEncryption.S3_MANAGED,
            enforceSSL: true,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            autoDeleteObjects: true,
            versioned: false,
            lifecycleRules: [
                {
                    id: 'TransitionAndExpire',
                    transitions: [
                        {
                            storageClass: s3.StorageClass.INFREQUENT_ACCESS,
                            transitionAfter: cdk.Duration.days(30),
                        },
                    ],
                    expiration: cdk.Duration.days(90),
                },
            ],
            cors: [
                {
                    allowedMethods: [
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                    ],
                    allowedOrigins: ['*'],
                    allowedHeaders: ['*'],
                    maxAge: 3600,
                },
            ],
        });

        this.bucketName = bucket.bucketName;
        this.bucketArn = bucket.bucketArn;

        // Outputs
        new cdk.CfnOutput(this, 'EvidenceBucketNameOutput', {
            value: this.bucketName,
            description: 'S3 bucket for evidence storage',
        });

        new cdk.CfnOutput(this, 'EvidenceBucketArnOutput', {
            value: this.bucketArn,
            description: 'ARN of the evidence S3 bucket',
        });

        new ssm.StringParameter(this, 'EvidenceBucketNameSsm', {
            parameterName: '/mission-control/evidence-bucket-name',
            stringValue: this.bucketName,
            description: 'Evidence S3 bucket name',
        });

        new ssm.StringParameter(this, 'EvidenceBucketArnSsm', {
            parameterName: '/mission-control/evidence-bucket-arn',
            stringValue: this.bucketArn,
            description: 'Evidence S3 bucket ARN',
        });
    }
}
