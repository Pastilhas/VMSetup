from time import sleep
import json
import requests
from datetime import datetime, timezone, timedelta
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext


PREFIX = 'inegiuppt'
SITE = 'inegi_compute'
SITEURL = f'https://{PREFIX}.sharepoint.com/sites/{SITE}'
USER = ''
PASS = ''
SP_LIST = 'Requests'
PARSED_IDS:dict = {}


def isToday(date:str) -> bool: return datetime.strptime(date,'%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date()
def isYeste(date:str) -> bool: return datetime.strptime(date,'%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date() - timedelta(days=1)

with open('/home/inegi/VMSetup/query_sharepoint.py.backup','r') as read_file:
    PARSED_IDS = json.load(read_file)

while True:
    sleep(10)
    try:
        ctx = ClientContext(SITEURL).with_credentials(UserCredential(USER, PASS))
        sp_list = ctx.web.lists.get_by_title(SP_LIST)
        sp_items = sp_list.get_items()
        ctx.load(sp_items)
        ctx.execute_query()
        active_items = [i.properties for i in sp_items if i.properties['Active']]
        new_items = [i for i in active_items if str(i['ID']) not in PARSED_IDS and isToday(i['From'])]
        old_items = [i for i in active_items if str(i['ID']) in PARSED_IDS]
        old_items = [i for i in old_items if not PARSED_IDS[i['ID']]['destroyed'] and isYeste(i['To'])]

        for i in new_items:
            id = i['ID']
            req = requests.post('http://192.168.190.190:58580', json={
                'type': 0,
                'name': '',
                'ram': i['RAM_x0028_32GB_x0029_'] * 32,
                'gpus': i['GPUS'],
                'cpus': i['GPUS'] * 4,
                'storage': i['Storage_x0028_2TB_x0029_']
            })
            PARSED_IDS[id] = { 'name':req.json()['name'], 'destroyed':False }

        for i in old_items:
            id = i['ID']
            name = PARSED_IDS[id]['name']
            req = requests.post('http://192.168.190.190:58580', json={
                'type': 1,
                'name': name,
                'ram': 0,
                'gpus': 0,
                'cpus': 0,
                'storage': 0
            })
            PARSED_IDS[id] = { 'name':name, 'destroyed':True }

        with open('/home/inegi/VMSetup/query_sharepoint.py.backup','w') as write_file:
            json.dump(PARSED_IDS,write_file)

    except Exception as ex:
        print(f'Error {ex}')
        break
