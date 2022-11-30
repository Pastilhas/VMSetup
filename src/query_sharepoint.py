from time import sleep
import json
from datetime import datetime, timezone, timedelta
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from defines import SP_USER, SP_PASS, QURY_BKP
from main import create_machine,destroy_machine


PREFIX = 'inegiuppt'
SITE = 'inegi_compute'
SITEURL = f'https://{PREFIX}.sharepoint.com/sites/{SITE}'
SP_LIST = 'Requests'
PARSED_IDS: dict = {}


with open(QURY_BKP, 'r') as file:
    PARSED_IDS = json.load(file)


def isToday(date: str) -> bool: return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date()
def isYesterday(date: str) -> bool: return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date() - timedelta(days=1)


while True:
    sleep(10)
    try:
        ctx = ClientContext(SITEURL).with_credentials(UserCredential(SP_USER, SP_PASS))
        sp_list = ctx.web.lists.get_by_title(SP_LIST)
        sp_items = sp_list.get_items()
        ctx.load(sp_items)
        ctx.execute_query()
        active_items = [i.properties for i in sp_items if i.properties['Active']]
        new_items = [i for i in active_items if isToday(i['From']) and i['ID'] not in PARSED_IDS]
        old_items = [i for i in active_items if isYesterday(i['To']) and i['ID'] in PARSED_IDS]

        for i in new_items:
            name = create_machine(i['RAM_x0028_32GB_x0029_'] * 32, i['GPUS'] * 4, i['GPUS'], i['Storage_x0028_2TB_x0029_'])
            PARSED_IDS[i['ID']] = { 'name': name, 'destroyed': False }

        for i in old_items:
            name = PARSED_IDS[i['ID']]['name']
            destroy_machine(name)
            PARSED_IDS[i['ID']] = { 'name': name, 'destroyed': True }

        if len(new_items) + len(old_items) > 0:
            with open(QURY_BKP, 'w') as file:
                json.dump(PARSED_IDS, file)

    except Exception as ex:
        print(f'Error {ex}')
        break
