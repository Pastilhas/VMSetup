from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess


class ServerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        req = json.loads(post_data)
        try:
            self.process_req(req['type'], req['name'], req['ram'], req['cpus'], req['gpus'], req['storage'])
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'name': 'vm{0}'.format(G_UID-1)}).encode('utf-8'))
        except BaseException as e:
            self.send_response(400)
            self.end_headers()
            print(e)

    def process_req(self, type, name, ram, cpus, gpus, storage):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        if type == 0: self.create_machine(ram, cpus, gpus, storage)
        else: self.destroy_machine(name)
        with open('/home/inegi/VMSetup/main.py.backup','w') as file:
            file.write(json.dumps({'uid':G_UID,'machines':G_MACHINES,'gpus':G_GPUS,'storage':G_STORAGE}))


    def create_machine(self, ram, cpus, gpus, storage):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        vmid = 'vm{0}'.format(G_UID)
        print('Creating drive. Wait...')
        subprocess.run('cp /home/inegi/VMSetup/ubuntu.qcow2 /var/lib/libvirt/images/{0}.qcow2'.format(vmid), shell=True)
        subprocess.run(
            'virt-install --name {0} --virt-type kvm --hvm --memory {1} \
            --vcpus {2} --disk /var/lib/libvirt/images/{0}.qcow2,format=qcow2 \
            --network network=default --graphics vnc,listen=0.0.0.0 \
            --noautoconsole --os-variant=ubuntu20.04 --import'.format(
                vmid, str(ram * 1024), str(cpus)
            ), shell=True)

        avail_gpu = [x for x in G_GPUS if G_GPUS[x]]
        if len(avail_gpu) > gpus: avail_gpu = avail_gpu[:gpus]

        for x in avail_gpu:
            subprocess.run('virsh attach-device {0} {1} --config'.format(vmid, x), shell=True)
            G_GPUS[x] = False

        avail_str = [x for x in G_STORAGE if G_STORAGE[x]]
        if len(avail_str) > storage: avail_str = avail_str[:storage]

        for x in avail_str:
            subprocess.run('virsh attach-device {0} {1} --config'.format(vmid, x), shell=True)
            G_STORAGE[x] = False

        G_UID = G_UID + 1
        G_MACHINES[vmid] = {
            'gpus': avail_gpu,
            'storage': avail_str
        }

        subprocess.run('virsh destroy {0}'.format(vmid), shell=True)
        subprocess.run('virsh start {0}'.format(vmid), shell=True)


    def destroy_machine(self, name):
        global G_UID, G_MACHINES, G_GPUS, G_STORAGE
        machine = G_MACHINES[name]
        for x in machine['gpus']: G_GPUS[x] = True
        for x in machine['storage']: G_STORAGE[x] = True
        subprocess.run('virsh destroy {0}'.format(name), shell=True)
        subprocess.run('virsh undefine {0}'.format(name), shell=True)
        subprocess.run('rm /var/lib/libvirt/images/{0}.qcow2'.format(name), shell=True)


ADDR = ('192.168.190.190', 58580)
HTTP = HTTPServer(ADDR, ServerHandler)

G_UID = 1
G_MACHINES = {}
G_GPUS = {}
G_STORAGE = {}

with open('/home/inegi/VMSetup/main.py.backup', 'r') as file:
    obj = json.load(file)
    G_UID = obj['uid']
    G_MACHINES = obj['machines']
    G_GPUS = obj['gpus']
    G_STORAGE = obj['storage']

HTTP.serve_forever()

