from flask import Flask, jsonify, render_template
import os
from pathlib import Path
import paramiko

app = Flask(__name__, template_folder='Templates')

def load_env():
    env_path = Path(__file__).parent / '.env'
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip())

load_env()

SSH_HOST = os.environ.get('SSH_HOST', '127.0.0.1')
SSH_PORT = int(os.environ.get('SSH_PORT', '2222'))
SSH_USERNAME = os.environ.get('SSH_USERNAME', '')
SSH_PASSWORD = os.environ.get('SSH_PASSWORD', '')
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))

def ssh_command(command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USERNAME, password=SSH_PASSWORD,)
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode()
    ssh.close()
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/disk')
def disk():
    output = ssh_command('df -h')
    return jsonify({'disk': output})

@app.route('/api/lsblk')
def lsblk():
    output = ssh_command('lsblk -n -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL')
    return jsonify({'lsblk': output})

@app.route('/api/iostat')
def iostat():
    output = ssh_command('iostat -x 1 1')
    return jsonify({'iostat': output})

@app.route('/api/cpu')
def cpu():
    output = ssh_command('top -bn1 | grep "Cpu(s)"')
    return jsonify({'cpu': output})

@app.route('/api/memory')
def memory():
    output = ssh_command('free -m')
    return jsonify({'memory': output})

@app.route('/api/traffic')
def traffic():
    output = ssh_command('ip -s link show')
    return jsonify({'traffic': output})

@app.route('/api/nic')
def nic():
    output = ssh_command(
        'for i in $(ls /sys/class/net | grep -v lo); do '
        'echo "=== $i ==="; ip link show $i; '
        'echo "---ADDR---"; ip -br addr show $i; '
        'echo "---ETHTOOL---"; ethtool $i 2>&1 | head -15; done'
    )
    return jsonify({'nic': output})

@app.route('/api/gpu')
def gpu():
    output = ssh_command("lspci | grep -iE 'vga|3d|display'")
    return jsonify({'gpu': output})

@app.route('/api/pci')
def pci():
    output = ssh_command('lspci -nn')
    return jsonify({'pci': output})

@app.route('/api/sensors')
def sensors():
    output = ssh_command(
        'sensors 2>&1; '
        'for d in /sys/class/hwmon/hwmon*; do '
        'echo "=== $d ==="; cat $d/name 2>/dev/null; '
        'for f in $d/fan*_input $d/temp*_input $d/power*_input $d/in*_input; do '
        '[ -f "$f" ] && echo "$(basename $f): $(cat $f)"; done; done'
    )
    return jsonify({'sensors': output})

if __name__ == '__main__':
    app.run(debug=True, port=FLASK_PORT)
