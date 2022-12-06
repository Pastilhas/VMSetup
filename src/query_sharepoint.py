from time import sleep
import json
from datetime import datetime, timezone, timedelta
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from defines import SP_USER, SP_PASS, QURY_BKP
from main import create_machine, destroy_machine, get_vnc


PREFIX = 'inegiuppt'
SITE = 'inegi_compute'
SITEURL = f'https://{PREFIX}.sharepoint.com/sites/{SITE}'
SP_LIST = 'Requests'
PARSED_IDS: dict = {}


with open(QURY_BKP, 'r') as file:
    PARSED_IDS = json.load(file)


def isToday(date: str) -> bool: return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date()
def isYesterday(date: str) -> bool: return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ').date() == datetime.today().date() - timedelta(days=1)


def send_mail(userid: str, subject: str, body: str):
    user = ctx.web.site_users.filter(f'Id eq {userid}')
    ctx.load(user)
    ctx.execute_query()
    user = user[0].properties if len(user) > 0 else None

    if user is not None:
        mimemsg = MIMEMultipart()
        mimemsg['From'] = SP_USER
        mimemsg['To'] = user['Email']
        mimemsg['Subject'] = subject
        mimemsg.attach(MIMEText(body, 'plain'))
        connection = smtplib.SMTP(host='smtp.office365.com', port=587)
        connection.starttls()
        connection.login(SP_USER, SP_PASS)
        connection.send_message(mimemsg)
        connection.quit()


while True:
    sleep(10)
    try:
        ctx = ClientContext(SITEURL).with_credentials(UserCredential(SP_USER, SP_PASS))
        sp_list = ctx.web.lists.get_by_title(SP_LIST)
        sp_items = sp_list.get_items()
        ctx.load(sp_items)
        ctx.execute_query()
        active_items = [i.properties for i in sp_items if i.properties['Active']]
        for i in range(len(active_items)): active_items[i]['ID'] = str(active_items[i]['ID'])
        new_items = [i for i in active_items if isToday(i['From']) and i['ID'] not in PARSED_IDS]
        old_items = [i for i in active_items if isYesterday(i['To']) and i['ID'] in PARSED_IDS]
        old_items = [i for i in old_items if not PARSED_IDS[i['ID']]['destroyed']]

        for i in new_items:
            name = create_machine(i['RAM_x0028_32GB_x0029_'] * 32, i['GPUS'] * 4, i['GPUS'], i['Storage_x0028_2TB_x0029_'])
            PARSED_IDS[i['ID']] = {'name': name, 'destroyed': False}
            vncdisplay = '192.168.190.190:' + get_vnc(name)

            send_mail(i["UserId"], 'Request accepted', f'''
Your request of {i["Title"]} from {datetime.strptime(i['From'], '%Y-%m-%dT%H:%M:%SZ').date()} to {datetime.strptime(i['To'], '%Y-%m-%dT%H:%M:%SZ').date()} was accepted
To access the virtual machine:
Use a VNC client
Connect to {vncdisplay}
Login: vm
Password: vm
''')

        for i in old_items:
            name = PARSED_IDS[i['ID']]['name']
            destroy_machine(name)
            PARSED_IDS[i['ID']] = {'name': name, 'destroyed': True}
            
            send_mail(i["UserId"], 'End of reservation', f'''
Your reservation of {i["Title"]} from {datetime.strptime(i['From'], '%Y-%m-%dT%H:%M:%SZ').date()} to {datetime.strptime(i['To'], '%Y-%m-%dT%H:%M:%SZ').date()} has ended.
Access to the virtual machine was revoked.
''')

        if len(new_items) + len(old_items) > 0:
            with open(QURY_BKP, 'w') as file:
                json.dump(PARSED_IDS, file)

    except Exception as ex:
        print(f'Error {ex}')
        break
