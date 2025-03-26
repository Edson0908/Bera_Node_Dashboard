from flask import Flask, render_template
import json
import os
import utils
from datetime import datetime


app = Flask(__name__, template_folder='../templates')

def get_latest_data():

    config = utils.load_config()
    overview_prefix = config['save_file_prefix']['validator_overview']
    stake_snapshot_prefix = config['save_file_prefix']['stake_snapshot']

    returnData = {}

    """获取最新的数据文件"""
    data = utils.get_file_data(overview_prefix)
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
    data = utils.get_file_data(stake_snapshot_prefix)
    timestamp = data['timestamp']
    data = data['results']
    
    returnData['stakeSnapshotData'] = data

    #print(json.dumps(returnData, indent=2, ensure_ascii=False))
    
    return returnData, timestamp


def process_stake_snapshot_data(data):

    processed_data = {}

    for key, value in data.items():
        processed_data[key] = {}
        processed_data[key]['Records'] = []
        processed_data[key]['name'] = value.get('name', key)
        index = 0
        for record in value.get('Records'):
            if record.get('End Block', None) is None:
                break
            if index == 0:
                processed_data[key]['Records'].append(record)
            else:
                if record.get('Total Staked') == value.get('Records')[index - 1].get('Total Staked') and record.get('Weight') == value.get('Records')[index - 1].get('Weight'):
                    processed_data[key]['Records'][-1]['End Block'] = record.get('End Block')
                    processed_data[key]['Records'][-1]['Total BGT Rewards'] += record.get('Total BGT Rewards')
                    processed_data[key]['Records'][-1]['Staker BGT Rewards'] += record.get('Staker BGT Rewards')
                    processed_data[key]['Records'][-1]['Commission'] += record.get('Commission')
                    processed_data[key]['Records'][-1]['BGT Rewards'] += record.get('BGT Rewards')
                else:
                    processed_data[key]['Records'].append(record)
            index += 1

    return processed_data
                
                          

@app.route('/')
def index():

    
    config = utils.load_config()

    #requestDuneData.update_stake_snapshot()

    # 获取数据
    data, timestamp = get_latest_data()
    
    if not data:
        return "没有找到数据文件", 404
    
    # 获取表头（现在已经按照指定顺序）
    headers = config['page_config']['overview_header']
    stakeSnapshotHeaders = config['page_config']['stake_snapshot_header']

    overviewData = data['overviewData']
    stakeSnapshotData = data['stakeSnapshotData']

    processed_stakeSnapshotData = process_stake_snapshot_data(stakeSnapshotData)

    print(json.dumps(stakeSnapshotData, indent=2, ensure_ascii=False))
    print(json.dumps(processed_stakeSnapshotData, indent=2, ensure_ascii=False))
  
    
    # 格式化时间戳
    formatted_time = datetime.fromisoformat(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('index.html', 
                         data=overviewData,
                         headers=headers,
                         stakeSnapshotHeaders=stakeSnapshotHeaders,
                         stakeSnapshotData=processed_stakeSnapshotData,
                         timestamp=formatted_time)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # 从环境变量获取端口，默认5000
    app.run(debug=True, host='0.0.0.0', port=port)
    