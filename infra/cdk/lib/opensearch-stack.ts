import * as cdk from 'aws-cdk-lib';
import * as opensearchserverless from 'aws-cdk-lib/aws-opensearchserverless';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { Construct } from 'constructs';

export class OpenSearchStack extends cdk.Stack {
    public readonly collectionEndpoint: string;
    public readonly collectionArn: string;

    constructor(scope: Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        const collectionName = 'mission-control-vectors';

        // 1. Encryption policy (required before collection creation)
        const encryptionPolicy = new opensearchserverless.CfnSecurityPolicy(
            this,
            'EncryptionPolicy',
            {
                name: 'mc-vectors-encryption',
                type: 'encryption',
                policy: JSON.stringify({
                    Rules: [
                        {
                            ResourceType: 'collection',
                            Resource: [`collection/${collectionName}`],
                        },
                    ],
                    AWSOwnedKey: true,
                }),
            },
        );

        // 2. Network policy — allow public access to the collection endpoint
        const networkPolicy = new opensearchserverless.CfnSecurityPolicy(
            this,
            'NetworkPolicy',
            {
                name: 'mc-vectors-network',
                type: 'network',
                policy: JSON.stringify([
                    {
                        Rules: [
                            {
                                ResourceType: 'collection',
                                Resource: [`collection/${collectionName}`],
                            },
                            {
                                ResourceType: 'dashboard',
                                Resource: [`collection/${collectionName}`],
                            },
                        ],
                        AllowFromPublic: true,
                    },
                ]),
            },
        );

        // 3. Data access policy — grant the calling account full access
        const dataAccessPolicy = new opensearchserverless.CfnAccessPolicy(
            this,
            'DataAccessPolicy',
            {
                name: 'mc-vectors-access',
                type: 'data',
                policy: JSON.stringify([
                    {
                        Rules: [
                            {
                                ResourceType: 'collection',
                                Resource: [`collection/${collectionName}`],
                                Permission: [
                                    'aoss:CreateCollectionItems',
                                    'aoss:UpdateCollectionItems',
                                    'aoss:DescribeCollectionItems',
                                ],
                            },
                            {
                                ResourceType: 'index',
                                Resource: [`index/${collectionName}/*`],
                                Permission: [
                                    'aoss:CreateIndex',
                                    'aoss:UpdateIndex',
                                    'aoss:DescribeIndex',
                                    'aoss:ReadDocument',
                                    'aoss:WriteDocument',
                                ],
                            },
                        ],
                        Principal: [`arn:aws:iam::${this.account}:root`],
                    },
                ]),
            },
        );

        // 4. VECTORSEARCH collection
        const collection = new opensearchserverless.CfnCollection(
            this,
            'VectorCollection',
            {
                name: collectionName,
                type: 'VECTORSEARCH',
                description:
                    'Vector search collection for Mission Control evidence embeddings (1024-dim Titan Embed Image v1)',
            },
        );

        collection.addDependency(encryptionPolicy);
        collection.addDependency(networkPolicy);
        collection.addDependency(dataAccessPolicy);

        this.collectionEndpoint = collection.attrCollectionEndpoint;
        this.collectionArn = collection.attrArn;

        // 5. Outputs
        new cdk.CfnOutput(this, 'CollectionEndpointOutput', {
            value: this.collectionEndpoint,
            description: 'OpenSearch Serverless collection endpoint',
        });

        new cdk.CfnOutput(this, 'CollectionArnOutput', {
            value: this.collectionArn,
            description: 'OpenSearch Serverless collection ARN',
        });

        new ssm.StringParameter(this, 'CollectionEndpointSsm', {
            parameterName: '/mission-control/opensearch-endpoint',
            stringValue: this.collectionEndpoint,
            description: 'OpenSearch Serverless vector collection endpoint',
        });
    }
}
