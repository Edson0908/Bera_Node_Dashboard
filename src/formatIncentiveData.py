import utils

def format_incentive_data_json_file():

    filename = 'incentive_data.json'
    data = utils.get_file_data(filename)
    
    for block_number, rewards in data.items():
        new_data = {}
        new_data['distributed'] = False
        new_data['rewards'] = rewards
        data[block_number] = new_data


    utils.update_json_file(filename, data)


format_incentive_data_json_file()