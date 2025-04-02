import utils
import time

def format_honey_data_json_file():

    config = utils.load_config()
    honey_file_prefix = config['save_file_prefix']['honey_rewards_claimed']
    honey_token = config['contracts']['HONEY Token']['address']
    
    honey_data = utils.get_file_data(honey_file_prefix)
    honey_data = honey_data['results']

    for block_number, amount in honey_data.items():
        raw_amount = amount * (10 ** 18)
        data = {
            block_number : {
                'token': honey_token,
                'amount': raw_amount
            }
        }
        utils.save_results_to_json(data, honey_file_prefix, 'honey')
        time.sleep(1)

format_honey_data_json_file()