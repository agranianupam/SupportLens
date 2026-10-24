import os
from pathlib import Path
import pandas as pd
import pytest
from src.data_generator import generate_synthetic_data
from src.data_quality import clean_and_validate_data

def test_reproducibility(tmp_path):
    dir1 = tmp_path / 'run1'
    dir2 = tmp_path / 'run2'
    generate_synthetic_data(seed=42, output_dir=str(dir1))
    generate_synthetic_data(seed=42, output_dir=str(dir2))
    df1_students = pd.read_csv(dir1 / 'students.csv')
    df2_students = pd.read_csv(dir2 / 'students.csv')
    pd.testing.assert_frame_equal(df1_students, df2_students)
    df1_weekly = pd.read_csv(dir1 / 'weekly_records.csv')
    df2_weekly = pd.read_csv(dir2 / 'weekly_records.csv')
    pd.testing.assert_frame_equal(df1_weekly, df2_weekly)

def test_student_anonymisation_and_count():
    students_df = pd.read_csv('data/students.csv')
    assert len(students_df) == 100
    assert students_df['student_id'].nunique() == 100
    assert students_df['student_id'].str.match('^S-\\d{4}$').all()
    prohibited_cols = {'name', 'email', 'phone', 'address', 'ssn', 'gender', 'race', 'ethnicity'}
    assert prohibited_cols.isdisjoint(set(students_df.columns))

def test_data_quality_cleaning():
    students_df = pd.read_csv('data/students.csv')
    weekly_df = pd.read_csv('data/weekly_records.csv')
    cleaned_df, report = clean_and_validate_data(weekly_df, students_df)
    assert report['duplicates_removed'] >= 2
    assert len(cleaned_df) == 1200
    assert report['invalid_attendance_corrected'] >= 1
    assert report['invalid_quiz_corrected'] >= 1
    assert report['invalid_assignment_status_corrected'] >= 1
    valid_att = cleaned_df['attendance_pct'].dropna()
    assert (valid_att >= 0).all() and (valid_att <= 100).all()
    valid_quiz = cleaned_df['quiz_score'].dropna()
    assert (valid_quiz >= 0).all() and (valid_quiz <= 100).all()
    assert cleaned_df['student_id'].nunique() == 100
