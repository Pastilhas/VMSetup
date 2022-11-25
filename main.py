from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess


ADDR = ('192.168.190.190', 58580)


class ServerHandler(BaseHTTPRequestHandler):
    UID = 1
    MACHINES = {}
    GPUS = {}
    STORAGE = {}

    def __init__(self, *args):
        super().__init__(*args)
        with open('/home/inegi/VMSetup/main.py.backup', 'r') as file:
            obj = json.load(file)
            self.UID = obj['uid']
            self.MACHINES = obj['machines']
            self.GPUS = obj['gpus']
            self.STORAGE = obj['storage']

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data)
        try:
            process_req(self, req['type'], req['name'], req['ram'],
                        req['cpus'], req['gpus'], req['storage'])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'name': 'vm{0}'.format(self.UID-1)}).encode('utf-8'))
        except BaseException as e:
            self.send_response(400)
            self.end_headers()
            print(e)


def process_req(self, type, name, ram, cpus, gpus, storage):
    if type == 0: create_machine(self, ram, cpus, gpus, storage)
    else: destroy_machine(self, name)
    with open('/home/inegi/VMSetup/main.py.backup','w') as file:
        file.write(json.dumps({'uid':self.UID,'machines':self.MACHINES,'gpus':self.GPUS,'storage':self.STORAGE}))


def create_machine(self, ram, cpus, gpus, storage):
    vmid = 'vm{0}'.format(self.UID)
    print('Creating drive. Wait...')
    subprocess.run('cp /home/inegi/VMSetup/ubuntu.qcow2 /var/lib/libvirt/images/{0}.qcow2'.format(vmid), shell=True)
    subprocess.run(
        'virt-install --name {0} --virt-type kvm --hvm --memory {1} \
        --vcpus {2} --disk /var/lib/libvirt/images/{0}.qcow2,format=qcow2 \
        --network network=default --graphics vnc,listen=0.0.0.0 \
        --noautoconsole --os-variant=ubuntu20.04 --import'.format(
            vmid, str(ram * 1024), str(cpus)
        ), shell=True)

    avail_gpu = [x for x in self.GPUS if self.GPUS[x]]
    if len(avail_gpu) > gpus: avail_gpu = avail_gpu[:gpus]

    for x in avail_gpu:
        subprocess.run('virsh attach-device {0} {1} --config'.format(vmid, x), shell=True)
        self.GPUS[x] = False

    avail_str = [x for x in self.STORAGE if self.STORAGE[x]]
    if len(avail_str) > storage: avail_str = avail_str[:storage]

    for x in avail_str:
        subprocess.run('virsh attach-device {0} {1} --config'.format(vmid, x), shell=True)
        self.STORAGE[x] = False

    self.UID = self.UID + 1

    self.MACHINES[vmid] = {
        'gpus': avail_gpu,
        'storage': avail_str
    }

    subprocess.run('virsh destroy {0}'.format(vmid), shell=True)
    subprocess.run('virsh start {0}'.format(vmid), shell=True)


def destroy_machine(self, name):
    machine = self.MACHINES[name]
    for x in machine['gpus']: self.GPUS[x] = True
    for x in machine['storage']: self.STORAGE[x] = True
    subprocess.run('virsh destroy {0}'.format(name), shell=True)
    subprocess.run('virsh undefine {0}'.format(name), shell=True)
    subprocess.run('rm /var/lib/libvirt/images/{0}.qcow2'.format(name), shell=True)


HTTP = HTTPServer(ADDR, ServerHandler)
HTTP.serve_forever()

