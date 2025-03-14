from flask import Flask, render_template
import json
import os
from datetime import datetime
import requestDuneData

app = Flask(__name__, template_folder='../templates')

def get_latest_data():

    returnData = {}

    """获取最新的数据文件"""
    data_dir = 'data'
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and f.startswith('validator_overview')]
    if not json_files:
        return None, None
    
    # 获取最新的文件
    latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
    file_path = os.path.join(data_dir, latest_file)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    
    # 定义字段顺序
    field_order = [
        'Date',
        'Daily BERA Staked',
        'Cumulative BERA Staked',
        'Daily BGT Rewards',
        'Cumulative BGT Rewards'
    ]
    
    # 重新排序数据字段
    ordered_results = []
    for item in results:
        ordered_item = {field: item.get(field, '') for field in field_order}
        ordered_results.append(ordered_item)
    
    returnData['overviewData'] = ordered_results

    """获取最新的 stake_snapshot 数据"""
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and f.startswith('stake_snapshot')]
    if not json_files:
        return None, None
    
    # 获取最新的文件
    latest_file = max(json_files, key=lambda x: os.path.getmtime(os.path.join(data_dir, x)))
    file_path = os.path.join(data_dir, latest_file)

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    returnData['stakeSnapshotData'] = data

    #print(json.dumps(returnData, indent=2, ensure_ascii=False))
    
    return returnData, data.get('timestamp')

@app.route('/')
def index():

    config_dir = 'config'
    config_file = os.path.join(config_dir, 'config.json')
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    #requestDuneData.update_stake_snapshot()

    # 获取数据
    data, timestamp = get_latest_data()
    
    if not data:
        return "没有找到数据文件", 404
    
    # 获取表头（现在已经按照指定顺序）
    headers = config['page_config']['overview_header']
    stakeSnapshotHeaders = config['page_config']['stake_snapshot_header']

    overviewData = data['overviewData']
    stakeSnapshotData = data['stakeSnapshotData']['results']
    print(json.dumps(stakeSnapshotData, indent=2, ensure_ascii=False))
  
    
    # 格式化时间戳
    formatted_time = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('index.html', 
                         data=overviewData,
                         headers=headers,
                         stakeSnapshotHeaders=stakeSnapshotHeaders,
                         stakeSnapshotData=stakeSnapshotData,
                         timestamp=formatted_time)

if __name__ == '__main__':
    app.run(debug=True)
    