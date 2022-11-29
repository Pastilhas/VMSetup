from time import sleep
import json
import requests
from datetime import datetime, timezone, timedelta
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from defines import SP_USER, SP_PASS, QURY_BKP


PREFIX = 'inegiuppt'
SITE = 'inegi_compute'
SITEURL = f'https://{PREFIX}.sharepoint.com/sites/{SITE}'
SP_LIST = 'Requests'
PARSED_IDS = {}


def isToday(date: str) -> bool: return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date()
def isYeste(date: str) -> bool: return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date() - timedelta(days=1)


with open(QURY_BKP, 'r') as read_file: PARSED_IDS = json.load(read_file)

while True:
    sleep(10)
    try:
        ctx = ClientContext(SITEURL).with_credentials(UserCredential(SP_USER, SP_PASS))
        sp_list = ctx.web.lists.get_by_title(SP_LIST)
        sp_items = sp_list.get_items()
        ctx.load(sp_items)
        ctx.execute_query()
        active_items = [i.properties for i in sp_items if i.properties['Active']]

        for i in active_items:
            id, name = str(i['ID']), ''
            msgtype, r, g, c, s = None, 0, 0, 0, 0
            if id in PARSED_IDS and isYeste(i['To']):
                if not PARSED_IDS[id]['destroyed']:
                    name = PARSED_IDS[id]['name']
                    msgtype, r, g, c, s = 1, 0, 0, 0, 0
            if id not in PARSED_IDS and isToday(i['From']):
                msgtype, r, g, c, s = 0, i['RAM_x0028_32GB_x0029_'] * 32, i['GPUS'], i['GPUS'] * 4, i['Storage_x0028_2TB_x0029_']
            if type != None:
                req = requests.post('http://192.168.190.190:58580', json={
                    'type': msgtype,
                    'name': name,
                    'ram': r,
                    'gpus': g,
                    'cpus': c,
                    'storage': s
                })
                if msgtype == 0: name = req.json()['name']
                PARSED_IDS[id] = {'name': name, 'destroyed': False if msgtype == 0 else True}
                with open(QURY_BKP, 'w') as write_file: json.dump(PARSED_IDS, write_file)
    except Exception as ex:
        print(f'Error {ex}')
        break
