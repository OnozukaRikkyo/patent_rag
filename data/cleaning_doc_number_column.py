import pandas as pd
import glob
import re
import os

# pathディレクトリ内のすべてのCSVファイルを取得
csv_files = glob.glob('patent_rag/data/path/*.csv')

# doc_numberからアルファベット以降を削除する関数
def extract_numbers_only(doc_number):
    """
    doc_numberから最初のアルファベット文字より前の数字だけを抽出
    例: '10027000A' -> '10027000'
    """
    if pd.isna(doc_number):
        return doc_number
    
    # 最初のアルファベット文字の位置を見つける
    match = re.search(r'[A-Za-z]', str(doc_number))
    if match:
        # アルファベットより前の部分を返す
        return str(doc_number)[:match.start()]
    else:
        # アルファベットがない場合はそのまま返す
        return str(doc_number)

# 全CSVファイルを処理
for csv_file in csv_files:
    print(f'処理中: {csv_file}')
    
    # CSVファイルを読み込む
    df = pd.read_csv(csv_file)
    
    # doc_number列が存在する場合のみ処理
    if 'doc_number' in df.columns:
        # doc_number列を処理
        df['doc_number'] = df['doc_number'].apply(extract_numbers_only)
        
        # 処理済みファイルを上書き保存
        df.to_csv(csv_file, index=False)
        print(f'  完了: {len(df)}行を処理しました')
    else:
        print(f'  警告: doc_number列が見つかりません')

print('\n全ての処理が完了しました')