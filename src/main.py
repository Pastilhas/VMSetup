from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
from defines import MAIN_BKP, QCOW_ORG


class ServerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data)
        try:
            self.process_req(req['type'], req['name'], req['ram'],
                             req['cpus'], req['gpus'], req['storage'])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(
                {'name': f'vm{G_UID-1}'}).encode('utf-8'))
        except BaseException as e:
            self.send_response(400)
            self.end_headers()
            print(e)

    def process_req(self, type, name, ram, cpus, gpus, storage):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        if type == 0:
            self.create_machine(ram, cpus, gpus, storage)
        else:
            self.destroy_machine(name)
        with open(MAIN_BKP, 'w') as file:
            file.write(json.dumps(
                {'uid': G_UID, 'machines': G_MACHINES, 'gpus': G_GPUS, 'storage': G_STORAGE}))

    def attach_dev(self, dict, max, vmid):
        arr = [x for x in dict if dict[x]]
        if len(arr) > max:
            arr = arr[:max]
        for x in arr:
            subprocess.run(
                f'virsh attach-device {vmid} {x} --config', shell=True)
            dict[x] = False
        return arr

    def create_machine(self, ram, cpus, gpus, storage):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        vmid = f'vm{G_UID}'
        subprocess.run(
            f'cp {QCOW_ORG} /var/lib/libvirt/images/{vmid}.qcow2', shell=True)
        subprocess.run(
            f'virt-install --name {vmid} --virt-type kvm --hvm --memory {ram * 1024} \
            --vcpus {cpus} --disk /var/lib/libvirt/images/{vmid}.qcow2,format=qcow2 \
            --network network=default --graphics vnc,listen=0.0.0.0 \
            --noautoconsole --os-variant=ubuntu20.04 --import', shell=True)

        used_gpus = self.attach_dev(G_GPUS, gpus, vmid)
        used_storage = self.attach_dev(G_STORAGE, storage, vmid)

        G_UID = G_UID + 1
        G_MACHINES[vmid] = {
            'gpus': used_gpus,
            'storage': used_storage
        }

        subprocess.run(f'virsh destroy {vmid}', shell=True)
        subprocess.run(f'virsh start {vmid}', shell=True)

    def destroy_machine(self, name):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        machine = G_MACHINES[name]
        for x in machine['gpus']:
            G_GPUS[x] = True
        for x in machine['storage']:
            G_STORAGE[x] = True
        subprocess.run(f'virsh destroy {name}', shell=True)
        subprocess.run(f'virsh undefine {name}', shell=True)
        subprocess.run(f'rm /var/lib/libvirt/images/{name}.qcow2', shell=True)


ADDR = ('192.168.190.190', 58580)
HTTP = HTTPServer(ADDR, ServerHandler)

G_UID = 1
G_MACHINES = {}
G_GPUS = {}
G_STORAGE = {}

with open(MAIN_BKP, 'r') as file:
    obj = json.load(file)
    G_UID = obj['uid']
    G_MACHINES = obj['machines']
    G_GPUS = obj['gpus']
    G_STORAGE = obj['storage']

HTTP.serve_forever()
