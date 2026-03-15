import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import { Construct } from 'constructs';

const NS = 'MissionControl';

export interface DashboardsStackProps extends cdk.StackProps {
  /** ALB full name — used for 5xx alarm. Pass from EcsStack output. */
  albFullName?: string;
  /** ALB target-group full name. */
  targetGroupFullName?: string;
}

export class DashboardsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: DashboardsStackProps = {}) {
    super(scope, id, props);

    // ── SNS topic for alarm notifications ──────────────────────────────
    const alarmTopic = new sns.Topic(this, 'AlarmTopic', {
      topicName: 'mission-control-alarms',
    });

    // ── Helper to build a custom metric ────────────────────────────────
    const metric = (
      metricName: string,
      opts: { statistic?: string; period?: cdk.Duration; unit?: cloudwatch.Unit } = {},
    ): cloudwatch.Metric =>
      new cloudwatch.Metric({
        namespace: NS,
        metricName,
        statistic: opts.statistic ?? 'Sum',
        period: opts.period ?? cdk.Duration.minutes(1),
        unit: opts.unit,
      });

    // ── Mission widgets ────────────────────────────────────────────────
    const missionStartWidget = new cloudwatch.GraphWidget({
      title: 'Mission Starts (count/min)',
      left: [metric('mission_start_total')],
      width: 12,
    });

    const missionDurationWidget = new cloudwatch.GraphWidget({
      title: 'Mission Duration (p50 / p95)',
      left: [
        metric('mission_duration_seconds', { statistic: 'p50', unit: cloudwatch.Unit.SECONDS }),
        metric('mission_duration_seconds', { statistic: 'p95', unit: cloudwatch.Unit.SECONDS }),
      ],
      width: 12,
    });

    // ── Evidence widgets ───────────────────────────────────────────────
    const evidenceRateWidget = new cloudwatch.GraphWidget({
      title: 'Evidence Ingested (rate/min)',
      left: [metric('evidence_ingested_total')],
      width: 12,
    });

    const evidenceCountWidget = new cloudwatch.SingleValueWidget({
      title: 'Total Evidence Ingested',
      metrics: [metric('evidence_ingested_total', { period: cdk.Duration.hours(1) })],
      width: 12,
    });

    // ── Agent widgets ──────────────────────────────────────────────────
    const agentTaskDurationWidget = new cloudwatch.GraphWidget({
      title: 'Agent Task Duration (p50 / p95)',
      left: [
        metric('agent_task_duration_seconds', { statistic: 'p50', unit: cloudwatch.Unit.SECONDS }),
        metric('agent_task_duration_seconds', { statistic: 'p95', unit: cloudwatch.Unit.SECONDS }),
      ],
      width: 12,
    });

    const heartbeatWidget = new cloudwatch.GraphWidget({
      title: 'Agent Heartbeat Misses',
      left: [metric('agent_heartbeat_missed_total')],
      width: 12,
    });

    // ── WebSocket & orchestrator widgets ────────────────────────────────
    const wsWidget = new cloudwatch.GraphWidget({
      title: 'Active WebSocket Connections',
      left: [metric('websocket_connections_active', { statistic: 'Maximum' })],
      width: 12,
    });

    const orchWidget = new cloudwatch.GraphWidget({
      title: 'Orchestrator Cycle Duration (p50 / p95)',
      left: [
        metric('orchestrator_cycle_duration_seconds', { statistic: 'p50', unit: cloudwatch.Unit.SECONDS }),
        metric('orchestrator_cycle_duration_seconds', { statistic: 'p95', unit: cloudwatch.Unit.SECONDS }),
      ],
      width: 12,
    });

    // ── Dashboard ──────────────────────────────────────────────────────
    new cloudwatch.Dashboard(this, 'MissionControlDashboard', {
      dashboardName: 'MissionControl',
      widgets: [
        [missionStartWidget, missionDurationWidget],
        [evidenceRateWidget, evidenceCountWidget],
        [agentTaskDurationWidget, heartbeatWidget],
        [wsWidget, orchWidget],
      ],
    });

    // ── Alarms ─────────────────────────────────────────────────────────

    // 1. Mission stuck — no mission_start_total in 120 s means nothing is moving.
    const missionStuckAlarm = new cloudwatch.Alarm(this, 'MissionStuckAlarm', {
      alarmName: 'MissionControl-MissionStuck',
      alarmDescription: 'No mission status change for > 120 seconds',
      metric: metric('mission_duration_seconds', {
        statistic: 'Maximum',
        period: cdk.Duration.seconds(120),
        unit: cloudwatch.Unit.SECONDS,
      }),
      threshold: 120,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    missionStuckAlarm.addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(alarmTopic));

    // 2. Agent heartbeat misses > 3 in 5 minutes.
    const heartbeatAlarm = new cloudwatch.Alarm(this, 'HeartbeatMissAlarm', {
      alarmName: 'MissionControl-HeartbeatMisses',
      alarmDescription: 'Agent heartbeat missed > 3 times in 5 min',
      metric: metric('agent_heartbeat_missed_total', {
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 3,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    heartbeatAlarm.addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(alarmTopic));

    // 3. ALB 5xx error rate > 5 %  (only when ALB names are provided).
    if (props.albFullName && props.targetGroupFullName) {
      const http5xxMetric = new cloudwatch.Metric({
        namespace: 'AWS/ApplicationELB',
        metricName: 'HTTPCode_Target_5XX_Count',
        dimensionsMap: {
          LoadBalancer: props.albFullName,
          TargetGroup: props.targetGroupFullName,
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      });

      const requestCountMetric = new cloudwatch.Metric({
        namespace: 'AWS/ApplicationELB',
        metricName: 'RequestCount',
        dimensionsMap: {
          LoadBalancer: props.albFullName,
          TargetGroup: props.targetGroupFullName,
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      });

      const errorRateMetric = new cloudwatch.MathExpression({
        expression: '(errors / requests) * 100',
        usingMetrics: {
          errors: http5xxMetric,
          requests: requestCountMetric,
        },
        period: cdk.Duration.minutes(5),
        label: '5xx Error Rate %',
      });

      const errorRateAlarm = new cloudwatch.Alarm(this, 'ErrorRateAlarm', {
        alarmName: 'MissionControl-5xxErrorRate',
        alarmDescription: '5xx error rate exceeds 5 %',
        metric: errorRateMetric,
        threshold: 5,
        evaluationPeriods: 1,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });
      errorRateAlarm.addAlarmAction(new cdk.aws_cloudwatch_actions.SnsAction(alarmTopic));
    }
  }
}
