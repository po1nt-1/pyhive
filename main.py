import json
import os
import time

import requests
from thehive4py.api import TheHiveApi
from thehive4py.query import And, Eq, Gt
from urllib3 import disable_warnings, exceptions


def init_config():
    try:
        global hive_url
        global username
        global password
        global default_case_owner
        global tg_token
        global tg_chat_id

        file_name = 'config.json'

        with open(file_name, 'r') as f:
            hive_url, username, password, default_case_owner, tg_token, tg_chat_id = json.load(
                f).values()

    except (FileNotFoundError, json.decoder.JSONDecodeError, ValueError) as e:
        hive_url = input('Enter Hive url: ').strip()
        username = input('Enter username: ').strip()
        password = input('Enter password: ').strip()
        default_case_owner = input('Enter default case owner: ').strip()
        tg_token = input('Enter tg token: ').strip()
        tg_chat_id = input('Enter tg chat_id: ').strip()
        with open(file_name, 'w') as f:
            json.dump(
                {
                    'hive_url': hive_url,
                    'username': username,
                    'password': password,
                    'default_case_owner': default_case_owner,
                    'tg_token': tg_token,
                    "tg_chat_id": tg_chat_id
                },
                f, indent=2
            )
        os.chmod(file_name, 0o600)


def parser(data):
    try:
        filter_list = (
            'caseId',
            'url',
            'title',
            'description'
        )

        for i, raw_case in enumerate(data):
            case = {}
            for key, value in raw_case.items():
                key = str(key).strip()
                value = str(value).strip()

                if key == 'description':
                    tmp_value = ''
                    tmp_description = ''
                    for line in value.splitlines():
                        if '**Поля таксономии**' in line or '**Корреляция:' in line:
                            continue
                        if '### ' == line[:4]:
                            tmp_help_description = line.split(
                                '### ')[1].split(' (2022-0')[0].strip()
                        if '* ####' in line:
                            line = line.split(
                                '* ####')[1].split(' (2022-0')[0].strip()
                            tmp_value += '* ' + line + '\n'
                    if tmp_value:
                        if tmp_value[-1] == '\n':
                            tmp_value = tmp_value[:-1]
                    else:
                        if tmp_help_description:
                            tmp_value = tmp_help_description
                        else:
                            tmp_value = 'empty'
                    value = tmp_value
                elif key == 'id':
                    value = f'{hive_url}/index.html#!/case/{value}/details'
                    key = 'url'

                if key in filter_list:
                    for character in '_*[]()~`>#+-=|{}.!':
                        if character in value:
                            value = value.replace(character, '\\' + character)

                    case.update({key: value})

            data[i] = case

        sorted_data = sorted(data, key=lambda x: int(x['caseId']))

        return sorted_data
    except Exception as e:
        print(f'{time.strftime("%d%m%Y-%H:%M:%S", time.localtime())}: {e}')
        raise Exception(e)


def send_nudes(case=None, error=None):
    try:
        msg = ''
        if case:
            msg += f'''Case \#{case['caseId']}: {case['title']}\n'''
            msg += f'''```\n\n{case['description']}\n\n```'''
            msg += f'''[Открыть в The Hive]({case['url']})'''

            # msg = f'''[Case \#{case['caseId']}]({case['url']})\n'''
            # msg += f'''{case['title']}\n'''
            # msg += f'''```\n{case['description']}\n```'''
        else:
            msg += f'{error}'

        payload = {
            'chat_id': f'{tg_chat_id}',
            'disable_web_page_preview': 'true',
            'protect_content': 'true',
            'parse_mode': 'MarkdownV2',
            'text': f'{msg}'
        }

        response = requests.post(
            url=f'https://api.telegram.org/bot{tg_token}/sendMessage',
            data=payload
        )
        if not response:
            raise ConnectionError('[requests.post] error')

    except Exception as e:
        print(f'{time.strftime("%d%m%Y-%H:%M:%S", time.localtime())}: {e}')
        raise Exception(e)


def main():
    print(f'{time.strftime("%d%m%Y-%H:%M:%S", time.localtime())}: Start')
    disable_warnings(exceptions.InsecureRequestWarning)
    init_config()

    api = TheHiveApi(hive_url, username, password, cert=False)

    query = And(
        Eq('owner', f'{default_case_owner}'),  # prod
        Eq('status', 'Open'),  # prod
        # Gt('caseId',  2426)  # test
    )

    err_count = 0
    detected_cases = []
    while True:
        try:
            response = api.find_cases(
                query=query
            )
            if not response:
                raise ConnectionError('[api.find_cases] error')

            data = response.json()
            if data:
                data = parser(data)
                for case in data:
                    if case['caseId'] not in detected_cases:
                        send_nudes(case=case)
                        detected_cases.append(case['caseId'])
            else:
                print(
                    f'{time.strftime("%d%m%Y-%H:%M:%S", time.localtime())}: nothing')

            time.sleep(60)
        except ConnectionError as e:
            print(f'{time.strftime("%d%m%Y-%H:%M:%S", time.localtime())}: {e}')
            err_count += 1
            send_nudes(error=e)
            time.sleep(15)
        except:
            err_count += 1
            if err_count >= 3:
                break

    print(f'detected cases: {detected_cases}')
    print(f'{time.strftime("%d%m%Y-%H:%M:%S", time.localtime())}: Stop')


if __name__ == '__main__':
    main()
