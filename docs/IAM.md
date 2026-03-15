# IAM Roles and Permissions

Mission Control uses a single ECS task role with least-privilege policies, defined in `infra/cdk/lib/iam-stack.ts`.

---

## ECS Task Role

**Principal:** `ecs-tasks.amazonaws.com`
**SSM Parameter:** `/mission-control/task-role-arn`

The role is assumed by ECS containers running the Mission Control backend. It grants access to five AWS services, each scoped to the minimum required resources.

---

## Permissions

### 1. Amazon Bedrock

| Action | Resource |
|--------|----------|
| `bedrock:InvokeModel` | `arn:aws:bedrock:{region}::foundation-model/amazon.nova-*` |
| `bedrock:InvokeModelWithResponseStream` | Same as above |

Grants invoke access to all Amazon Nova foundation models (Nova 2 Lite, Nova 2 Sonic, Nova Multimodal Embeddings). Scoped to `amazon.nova-*` -- no access to third-party models.

### 2. S3 (Evidence Bucket)

| Action | Resource |
|--------|----------|
| `s3:PutObject` | `{evidenceBucketArn}/*` |
| `s3:GetObject` | `{evidenceBucketArn}/*` |

Read/write access to objects in the evidence bucket only. No `DeleteObject`, `ListBucket`, or bucket-level permissions.

### 3. OpenSearch Serverless

| Action | Resource |
|--------|----------|
| `aoss:APIAccessAll` | `{opensearchCollectionArn}` |

Full API access to the vector collection used for evidence embeddings. Scoped to the specific collection ARN passed from the OpenSearch stack.

### 4. Secrets Manager

| Action | Resource |
|--------|----------|
| `secretsmanager:GetSecretValue` | `{dbSecretArn}` |

Read-only access to the RDS database credentials secret. Scoped to the exact secret ARN -- no wildcard.

### 5. CloudWatch

| Action | Resource | Condition |
|--------|----------|-----------|
| `cloudwatch:PutMetricData` | `*` | `cloudwatch:namespace = "MissionControl"` |
| `logs:CreateLogStream` | `/ecs/mission-control*` log groups | -- |
| `logs:PutLogEvents` | `/ecs/mission-control*` log groups | -- |

Metrics are restricted to the `MissionControl` namespace via IAM condition. Log access is scoped to `/ecs/mission-control*` log groups.

---

## Retrieving the Role ARN

```bash
# From SSM Parameter Store
aws ssm get-parameter --name /mission-control/task-role-arn --query 'Parameter.Value' --output text

# From CloudFormation stack output
aws cloudformation describe-stacks --stack-name MissionControlIam \
  --query 'Stacks[0].Outputs[?OutputKey==`TaskRoleArnOutput`].OutputValue' --output text
```

---

## Security Notes

- **No wildcard resources** except CloudWatch `PutMetricData`, which is constrained by a namespace condition.
- **No write access to secrets** -- the role can only read the DB credential secret.
- **No S3 delete or list** -- containers can only put and get evidence objects.
- **Bedrock scoped to Nova models** -- no access to Anthropic, Cohere, or other provider models.
- The role is created by CDK and its ARN is stored in SSM for consumption by the ECS stack.
