
### JSONLスキーマ設定手順

1. スキーマ　→　「テキストとして編集」をON　→　テキストボックスに下記スキーマ（json）をコピペする
2. 「テキストとして編集」をOFFにする　→　5~10秒でスキーマ定義が自動作成される
3. 「テーブルを作成」をクリック　→　30秒くらいで作成完了する

```json
[
  {"name":"path","type":"STRING","mode":"NULLABLE"},
  {"name":"publication","type":"RECORD","mode":"NULLABLE","fields":[
    {"name":"doc_number","type":"STRING","mode":"NULLABLE"},
    {"name":"country","type":"STRING","mode":"NULLABLE"},
    {"name":"kind","type":"STRING","mode":"NULLABLE"},
    {"name":"date","type":"STRING","mode":"NULLABLE"}
  ]},
  {"name":"application","type":"RECORD","mode":"NULLABLE","fields":[
    {"name":"doc_number","type":"STRING","mode":"NULLABLE"},
    {"name":"date","type":"STRING","mode":"NULLABLE"}
  ]},
  {"name":"invention_title","type":"STRING","mode":"NULLABLE"},
  {"name":"parties","type":"RECORD","mode":"NULLABLE","fields":[
    {"name":"applicants","type":"RECORD","mode":"REPEATED","fields":[
      {"name":"name","type":"STRING","mode":"NULLABLE"},
      {"name":"registered_number","type":"STRING","mode":"NULLABLE"},
      {"name":"address","type":"STRING","mode":"NULLABLE"}
    ]},
    {"name":"agents","type":"RECORD","mode":"REPEATED","fields":[
      {"name":"name","type":"STRING","mode":"NULLABLE"},
      {"name":"registered_number","type":"STRING","mode":"NULLABLE"},
      {"name":"address","type":"STRING","mode":"NULLABLE"}
    ]},
    {"name":"inventors","type":"RECORD","mode":"REPEATED","fields":[
      {"name":"name","type":"STRING","mode":"NULLABLE"},
      {"name":"registered_number","type":"STRING","mode":"NULLABLE"},
      {"name":"address","type":"STRING","mode":"NULLABLE"}
    ]}
  ]},
  {"name":"classifications","type":"RECORD","mode":"NULLABLE","fields":[
    {"name":"ipc_main","type":"STRING","mode":"NULLABLE"},
    {"name":"ipc_further","type":"STRING","mode":"REPEATED"},
    {"name":"jp_main","type":"STRING","mode":"NULLABLE"},
    {"name":"jp_further","type":"STRING","mode":"REPEATED"}
  ]},
  {"name":"theme_codes","type":"STRING","mode":"REPEATED"},
  {"name":"f_terms","type":"STRING","mode":"REPEATED"},
  {"name":"claims","type":"STRING","mode":"REPEATED"},
  {"name":"description","type":"RECORD","mode":"NULLABLE","fields":[
    {"name":"technical_field","type":"STRING","mode":"REPEATED"},
    {"name":"background_art","type":"STRING","mode":"REPEATED"},
    {"name":"disclosure","type":"RECORD","mode":"NULLABLE","fields":[
      {"name":"tech_problem","type":"STRING","mode":"REPEATED"},
      {"name":"tech_solution","type":"STRING","mode":"REPEATED"},
      {"name":"advantageous_effects","type":"STRING","mode":"REPEATED"}
    ]},
    {"name":"best_mode","type":"STRING","mode":"REPEATED"}
  ]},
  {"name":"abstract","type":"STRING","mode":"NULLABLE"}
]
```