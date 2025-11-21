import glob
import os
import numpy as np
import pandas as pd


def process_csv_to_numpy():
    """
    pathディレクトリ内のすべてのCSVファイルを読み込み、
    doc_number, table_name, typeの列をnumpy配列に変換して結合し、
    patent_path_numpy.npyとして保存する
    type列は文字列から整数に変換: A=0, 1=1, B=2, U=3
    """
    # pathディレクトリのパスを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path_dir = os.path.join(current_dir, 'path')

    # pathディレクトリ内のすべてのCSVファイルを取得
    csv_files = glob.glob(os.path.join(path_dir, '*.csv'))

    if not csv_files:
        print("CSVファイルが見つかりませんでした")
        return

    print(f"{len(csv_files)}個のCSVファイルを検出しました")

    # type列の文字列から整数へのマッピング
    type_mapping = {'A': 0, '1': 1, 'B': 2, 'U': 3}

    # すべてのデータを格納するリスト
    all_arrays = []

    # 各CSVファイルを処理
    for csv_file in csv_files:
        print(f"処理中: {os.path.basename(csv_file)}")

        # CSVファイルを読み込み、必要な列のみ取得
        df = pd.read_csv(csv_file, usecols=['doc_number', 'table_name', 'type'])

        # type列を文字列に変換してからマッピング
        df['type'] = df['type'].astype(str).map(type_mapping)

        # numpy配列に変換（整数型に変換）
        numpy_array = df.to_numpy(dtype=np.int64)
        all_arrays.append(numpy_array)

    # すべての配列を結合
    combined_array = np.concatenate(all_arrays, axis=0)

    print(f"結合後のデータ形状: {combined_array.shape}")
    print(f"総行数: {combined_array.shape[0]:,}行")

    # numpy形式で保存
    output_file = os.path.join(path_dir, 'patent_path_numpy.npy')
    print(combined_array.shape)
    np.save(output_file, combined_array)

    print(f"保存完了: {output_file}")
    print(f"ファイルサイズ: {os.path.getsize(output_file) / (1024*1024):.2f} MB")


if __name__ == '__main__':
    process_csv_to_numpy()
