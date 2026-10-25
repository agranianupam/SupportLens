from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
COLOR_PALETTE = {'On Track': '#10B981', 'Monitor': '#F59E0B', 'Suggest Outreach': '#F97316', 'Priority Check-in': '#EF4444', 'Insufficient Data': '#9CA3AF', 'Submitted': '#10B981', 'Late': '#F59E0B', 'Missing': '#EF4444', 'Not Due': '#E5E7EB'}

def create_student_attendance_chart(student_records: pd.DataFrame, as_of_week: int, threshold: float=75.0) -> go.Figure:
    df = student_records[student_records['week'] <= as_of_week].copy()
    fig = go.Figure()
    fig.add_hline(y=threshold, line_dash='dash', line_color='#DC2626', annotation_text=f'Threshold ({threshold:.0f}%)', annotation_position='bottom right')
    fig.add_trace(go.Scatter(x=df['week'], y=df['attendance_pct'], mode='lines+markers', name='Attendance %', line=dict(color='#2563EB', width=2.5), marker=dict(size=7, color='#1D4ED8'), connectgaps=False))
    fig.update_layout(title='Weekly Attendance Trajectory', xaxis=dict(title='Week', tickmode='linear', tick0=1, dtick=1, range=[0.5, as_of_week + 0.5]), yaxis=dict(title='Attendance (%)', range=[0, 105]), margin=dict(l=40, r=20, t=40, b=40), height=260, template='plotly_white')
    return fig

def create_student_assignment_strip(student_records: pd.DataFrame, as_of_week: int) -> go.Figure:
    df = student_records[student_records['week'] <= as_of_week].copy()
    status_colors = {'Submitted': '#10B981', 'Late': '#F59E0B', 'Missing': '#EF4444', 'Not Due': '#94A3B8'}
    colors = [status_colors.get(s, '#CBD5E1') for s in df['assignment_status']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['week'], y=[1] * len(df), marker_color=colors, text=df['assignment_status'], textposition='inside', hoverinfo='x+text'))
    fig.update_layout(title='Assignment Submissions by Week', xaxis=dict(title='Week', tickmode='linear', tick0=1, dtick=1, range=[0.5, as_of_week + 0.5]), yaxis=dict(visible=False), margin=dict(l=40, r=20, t=40, b=40), height=180, template='plotly_white')
    return fig

def create_student_quiz_chart(student_records: pd.DataFrame, as_of_week: int, threshold: float=50.0) -> go.Figure:
    df = student_records[(student_records['week'] <= as_of_week) & (student_records['quiz_taken'] == True)].copy()
    fig = go.Figure()
    fig.add_hline(y=threshold, line_dash='dash', line_color='#DC2626', annotation_text=f'Check-in Threshold ({threshold:.0f}%)', annotation_position='bottom right')
    if len(df) > 0:
        fig.add_trace(go.Scatter(x=df['week'], y=df['quiz_score'], mode='lines+markers', name='Quiz Score', line=dict(color='#7C3AED', width=2.5), marker=dict(size=8, color='#6D28D9'), connectgaps=False))
    fig.update_layout(title='Weekly Quiz Scores', xaxis=dict(title='Week', tickmode='linear', tick0=1, dtick=1, range=[0.5, as_of_week + 0.5]), yaxis=dict(title='Score (%)', range=[0, 105]), margin=dict(l=40, r=20, t=40, b=40), height=260, template='plotly_white')
    return fig

def create_cohort_level_donut(level_counts: Dict[str, int]) -> go.Figure:
    labels = list(level_counts.keys())
    values = list(level_counts.values())
    colors = [COLOR_PALETTE.get(l, '#6B7280') for l in labels]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.55, marker=dict(colors=colors), textinfo='label+value', hoverinfo='label+percent+value')])
    fig.update_layout(title='Cohort Distribution by Support Level', margin=dict(l=20, r=20, t=40, b=20), height=300, showlegend=False, template='plotly_white')
    return fig

def create_cohort_weekly_trends(weekly_df: pd.DataFrame, as_of_week: int) -> go.Figure:
    df = weekly_df[weekly_df['week'] <= as_of_week].copy()
    att_avg = df.groupby('week')['attendance_pct'].mean()
    quiz_avg = df[df['quiz_taken'] == True].groupby('week')['quiz_score'].mean()
    due_weeks = df[df['assignment_status'].isin(['Submitted', 'Late', 'Missing'])]
    sub_rate = due_weeks.groupby('week').apply(lambda g: g['assignment_status'].isin(['Submitted', 'Late']).mean() * 100)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=att_avg.index, y=att_avg.values, mode='lines+markers', name='Average Attendance %', line=dict(color='#2563EB', width=2.5)))
    fig.add_trace(go.Scatter(x=quiz_avg.index, y=quiz_avg.values, mode='lines+markers', name='Average Quiz %', line=dict(color='#7C3AED', width=2.5)))
    if len(sub_rate) > 0:
        fig.add_trace(go.Scatter(x=sub_rate.index, y=sub_rate.values, mode='lines+markers', name='Assignment Submission %', line=dict(color='#059669', width=2.5, dash='dot')))
    fig.update_layout(title='Cohort Engagement Averages Over Semester', xaxis=dict(title='Week', tickmode='linear', tick0=1, dtick=1, range=[0.5, as_of_week + 0.5]), yaxis=dict(title='Percentage (%)', range=[0, 105]), margin=dict(l=40, r=20, t=40, b=40), height=320, template='plotly_white', legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
    return fig

def create_subgroup_fairness_chart(subgroups: Dict[str, Dict[str, Any]], attribute_name: str) -> go.Figure:
    groups = list(subgroups.keys())
    flag_rates = [subgroups[g]['flag_rate_pct'] for g in groups]
    recalls = [subgroups[g]['recall'] * 100 for g in groups]
    fprs = [subgroups[g]['fpr'] * 100 for g in groups]
    fig = go.Figure(data=[go.Bar(name='Flag Rate (%)', x=groups, y=flag_rates, marker_color='#3B82F6'), go.Bar(name='Recall / Sensitivity (%)', x=groups, y=recalls, marker_color='#10B981'), go.Bar(name='False Positive Rate (%)', x=groups, y=fprs, marker_color='#F59E0B')])
    fig.update_layout(barmode='group', title=f'Subgroup Fairness Metrics ({attribute_name})', yaxis=dict(title='Rate (%)', range=[0, 100]), margin=dict(l=40, r=20, t=40, b=40), height=320, template='plotly_white')
    return fig

def create_missing_stress_chart(stress_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=stress_df['added_missingness_pct'], y=stress_df['recall'] * 100, mode='lines+markers', name='Recall (%)', line=dict(color='#10B981', width=2.5)))
    fig.add_trace(go.Scatter(x=stress_df['added_missingness_pct'], y=stress_df['precision'] * 100, mode='lines+markers', name='Precision (%)', line=dict(color='#3B82F6', width=2.5)))
    fig.add_trace(go.Scatter(x=stress_df['added_missingness_pct'], y=stress_df['alert_burden_pct'], mode='lines+markers', name='Alert Burden (%)', line=dict(color='#F59E0B', width=2, dash='dash')))
    return fig


def create_insufficient_data_growth_chart(stress_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=stress_df['added_missingness_pct'],
            y=stress_df['insufficient_data_pct'],
            name='Insufficient Data Share (%)',
            marker_color='#9CA3AF',
        )
    )
    if 'avg_data_confidence' in stress_df.columns:
        fig.add_trace(
            go.Scatter(
                x=stress_df['added_missingness_pct'],
                y=stress_df['avg_data_confidence'] * 100,
                mode='lines+markers',
                name='Avg Confidence Score (%)',
                line=dict(color='#6366F1', width=2.5),
                yaxis='y2',
            )
        )
    fig.update_layout(
        title='Abstention Telemetry: Insufficient Data Share & Confidence',
        xaxis=dict(title='Injected Data Missingness (%)', ticksuffix='%'),
        yaxis=dict(title='Insufficient Data Share (%)', range=[0, 100]),
        yaxis2=dict(title='Avg Confidence (%)', overlaying='y', side='right', range=[0, 100]),
        margin=dict(l=40, r=40, t=40, b=40),
        height=320,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig



def create_multiseed_box_plot(detailed_df: pd.DataFrame) -> go.Figure:
    fig = px.box(
        detailed_df,
        x='Method',
        y='F1 Score',
        color='Method',
        points='all',
        title='F1 Score Distribution Across 5 Random Seeds',
    )
    fig.update_layout(
        showlegend=False,
        yaxis=dict(title='F1 Score', range=[0.0, 1.05]),
        margin=dict(l=40, r=20, t=40, b=40),
        height=340,
        template='plotly_white',
    )
    return fig


def create_earliness_histogram(earliness_records: List[Dict[str, Any]]) -> go.Figure:
    valid_rel = [
        r['relative_earliness']
        for r in earliness_records
        if r.get('relative_earliness') is not None
    ]
    fig = go.Figure()
    if valid_rel:
        fig.add_trace(
            go.Histogram(
                x=valid_rel,
                nbinsx=10,
                marker_color='#3B82F6',
                opacity=0.85,
            )
        )
        fig.add_vline(
            x=0,
            line_dash='dash',
            line_color='#EF4444',
            annotation_text='Decline Start',
            annotation_position='top right',
        )
    fig.update_layout(
        title='Timeliness of Detection: (First Flag Week − Decline Start Week)',
        xaxis=dict(
            title='Weeks Relative to Decline Start (Negative = Early, 0 = Immediate, Positive = Weeks After)',
            dtick=1,
        ),
        yaxis=dict(title='Student Count'),
        margin=dict(l=40, r=20, t=40, b=40),
        height=300,
        template='plotly_white',
    )
    return fig


def create_threshold_sensitivity_chart(sensitivity_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sensitivity_df['Delta (%)'],
            y=sensitivity_df['F1 Score'] * 100,
            mode='lines+markers',
            name='F1 Score (%)',
            line=dict(color='#2563EB', width=2.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sensitivity_df['Delta (%)'],
            y=sensitivity_df['Recall'] * 100,
            mode='lines+markers',
            name='Recall (%)',
            line=dict(color='#10B981', width=2.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sensitivity_df['Delta (%)'],
            y=sensitivity_df['Alert Burden (%)'],
            mode='lines+markers',
            name='Alert Burden (%)',
            line=dict(color='#F59E0B', width=2, dash='dash'),
        )
    )
    fig.update_layout(
        title='Metric Stability Across ±20% Threshold Variations',
        xaxis=dict(title='Threshold Delta from Baseline (%)'),
        yaxis=dict(title='Percentage (%)', range=[0, 105]),
        margin=dict(l=40, r=20, t=40, b=40),
        height=320,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


def create_review_outcomes_donut(decision_counts: Dict[str, int]) -> go.Figure:
    labels = list(decision_counts.keys())
    values = list(decision_counts.values())
    outcome_colors = {
        'Confirmed': '#0284C7',
        'Corrected': '#8B5CF6',
        'Dismissed': '#64748B',
        'Deferred': '#F59E0B',
    }
    colors = [outcome_colors.get(l, '#94A3B8') for l in labels]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors),
                textinfo='label+value',
                hoverinfo='label+percent+value',
            )
        ]
    )
    fig.update_layout(
        title='Review Decisions Breakdown',
        margin=dict(l=20, r=20, t=40, b=20),
        height=300,
        showlegend=False,
        template='plotly_white',
    )
    return fig


def create_dismissal_reasons_bar(reason_counts: Dict[str, int]) -> go.Figure:
    labels = list(reason_counts.keys())
    values = list(reason_counts.values())
    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color='#F59E0B',
                text=values,
                textposition='auto',
            )
        ]
    )
    fig.update_layout(
        title='Dismissal Reasons (False Alarms)',
        xaxis=dict(title='Reason Code'),
        yaxis=dict(title='Count', tick0=0, dtick=1),
        margin=dict(l=40, r=20, t=40, b=40),
        height=300,
        template='plotly_white',
    )
    return fig


def create_action_effectiveness_bar_chart(breakdown_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name='Helpful',
            x=breakdown_df['Action Type'],
            y=breakdown_df['Helpful'],
            marker_color='#10B981',
        )
    )
    fig.add_trace(
        go.Bar(
            name='Partially helpful',
            x=breakdown_df['Action Type'],
            y=breakdown_df['Partially helpful'],
            marker_color='#F59E0B',
        )
    )
    fig.add_trace(
        go.Bar(
            name='Not helpful',
            x=breakdown_df['Action Type'],
            y=breakdown_df['Not helpful'],
            marker_color='#EF4444',
        )
    )
    fig.update_layout(
        barmode='stack',
        title='Action Effectiveness Breakdown by Type (Min. 3 Ratings)',
        xaxis=dict(title='Supportive Action Type'),
        yaxis=dict(title='Completed Feedback Count'),
        margin=dict(l=40, r=20, t=40, b=40),
        height=320,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig


