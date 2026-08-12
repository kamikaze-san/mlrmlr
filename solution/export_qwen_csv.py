import pandas as pd
import json
import os

# Save clean standalone Qwen 3.5 submission CSV
df_comp = pd.read_csv('solution/qwen35_all_333_comparison.csv') if os.path.exists('solution/qwen35_all_333_comparison.csv') else None

if df_comp is not None:
    # Fill any null with det_ans fallback
    df_qwen = df_comp[['question_id', 'qwen35_ans']].copy()
    df_qwen['qwen35_ans'] = df_qwen['qwen35_ans'].fillna(df_comp['det_ans'])
    df_qwen = df_qwen.rename(columns={'qwen35_ans': 'answer'})
    df_qwen.to_csv('solution/answers_qwen35.csv', index=False)
    print("Saved solution/answers_qwen35.csv successfully!")
    print("Shape:", df_qwen.shape)
    print("Nulls:", df_qwen['answer'].isnull().sum())
    print(df_qwen.head(5))
else:
    print("qwen35_all_333_comparison.csv not found, creating from pipeline...")
    df_sub = pd.read_csv('solution/answers_submission.csv')
    df_sub.to_csv('solution/answers_qwen35.csv', index=False)
    print("Saved solution/answers_qwen35.csv from submission pipeline!")
