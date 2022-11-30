import subprocess
import json
from defines import MAIN_BKP, QCOW_ORG


UID: int = 1
MACHINES: dict = {}
GPUS: dict = {}
STORAGE: dict = {}


with open(MAIN_BKP,'r') as file:
    obj = json.load(file)
    UID = obj['uid']
    MACHINES = obj['machines']
    GPUS = obj['gpus']
    STORAGE = obj['storage']


def update_file() -> None:
    global UID, MACHINES, GPUS, STORAGE
    with open(MAIN_BKP,'w') as file:
        json.dump({ 'uid': UID, 'machines': MACHINES, 'gpus': GPUS, 'storage': STORAGE }, file)



def attach_devices(devices: dict, max: int, machine: str) -> list:
    arr = [x for x in devices if devices[x]]
    if len(arr) > max:arr = arr[:max]
    for x in arr: subprocess.run(f'virsh attach-device {machine} {x} --config', shell=True)
    return arr


def create_machine(ram: int, cpus: int, gpus: int, storage: int) -> str:
    global UID, MACHINES, GPUS, STORAGE
    machine = {'gpus': [], 'storage': []}
    vmid = f'vm{UID}'
    subprocess.run(
        f'cp {QCOW_ORG} /var/lib/libvirt/images/{vmid}.qcow2', shell=True)
    subprocess.run(
        f'virt-install --name {vmid} --virt-type kvm --hvm --memory {ram * 1024} \
        --vcpus {cpus} --disk /var/lib/libvirt/images/{vmid}.qcow2,format=qcow2 \
        --network network=default --graphics vnc,listen=0.0.0.0 \
        --noautoconsole --os-variant=ubuntu20.04 --import', shell=True)

    used_gpus = attach_devices(GPUS, gpus, vmid)
    used_storage = attach_devices(STORAGE, storage, vmid)
    for i in used_gpus: GPUS[i] = False
    for i in used_storage: STORAGE[i] = False
    machine['gpus'] = used_gpus
    machine['storage'] = used_storage

    subprocess.run(f'virsh destroy {vmid}', shell=True)
    subprocess.run(f'virsh start {vmid}', shell=True)

    UID = UID + 1
    MACHINES[vmid] = machine
    update_file()


def destroy_machine(name: str) -> None:
    global UID, MACHINES, GPUS, STORAGE
    machine = MACHINES[name]
    for x in machine['gpus']: GPUS[x] = True
    for x in machine['storage']: STORAGE[x] = True
    subprocess.run(f'virsh destroy {name}', shell=True)
    subprocess.run(f'virsh undefine {name}', shell=True)
    subprocess.run(f'rm /var/lib/libvirt/images/{name}.qcow2', shell=True)
    update_file()
