# import numpy as np
# import os

# # numpyファイルを読み込む
# data = np.load(os.path.join(os.path.dirname(__file__), 'path', 'patent_path_numpy.npy'))

# print(f'データ形状: {data.shape}')
# print(f'データ型: {data.dtype}')
# print()
# print('最初の10行のdoc_number（第1列）:')
# print(data[:10, 0])
# print()
# print('doc_numberの統計情報:')
# print(f'最小値: {data[:, 0].min()}')
# print(f'最大値: {data[:, 0].max()}')
# print()
# print('サンプルデータ（最初の5行）:')
# print(data[:5])

import os
import pandas as pd

def modify_doc_number_in_csv(path: str) -> None:
    # pathディレクトリ下のA_から始まるすべてのcsvを読み込み、doc_numberのカラムを、doc_idのJPの後に続くアルファベットまでの整数を取得して置き換える
    for f in os.listdir(path):
        if f.startswith("A_") and f.endswith(".csv"):
            file_path = os.path.join(path, f)
            df = pd.read_csv(file_path)
            df['doc_number'] = df['doc_id'].str.extract(r'JP(\d+)')[0].astype(int)
            df.to_csv(file_path, index=False)

if __name__ == "__main__":
    modify_doc_number_in_csv(os.path.join(os.path.dirname(__file__), "path"))
