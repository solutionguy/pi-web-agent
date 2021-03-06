#!/usr/bin/python

import os
import sys
import subprocess
import cgi
import cgitb
import xml.etree.ElementTree as ET
import json
if 'MY_HOME' not in os.environ:
    os.environ['MY_HOME']='/usr/libexec/pi-web-agent'
sys.path.append(os.environ['MY_HOME']+'/cgi-bin')
sys.path.append(os.environ['MY_HOME']+'/objects')
sys.path.append(os.environ['MY_HOME']+'/cgi-bin/chrome')
from services import *
cgitb.enable()
NO_ACTION=0
UPDATE_READY=101
NEW_UPDATE=110
REBOOT_REQUIRED=120
UPDATE_PENDING=100
DPKG_CONFIG_NEEDED=200
PROCESS_RUNNING=201
 
from view import *

def execute(command):
    
    sp=subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, err = sp.communicate()
    sp.wait()
    return [output, sp.returncode]

def getMemoryUsage():
    command=os.environ['MY_HOME'] + '/scripts/memory_information MemFree'
    free=execute(command)[0]
    command=os.environ['MY_HOME'] + '/scripts/memory_information MemTotal'
    total=execute(command)[0]
    return 100 - int((float(free)/float(total))*100)
    
def getAptBusy():
    a, errorcode_apt_get = execute('pgrep apt-get')
    a, errorcode_aptitude = execute('pgrep aptitude')
    if errorcode_apt_get == 0 or errorcode_aptitude == 0 :
      return True
    return False

def getDiskUsage():
    command='df -hP / | grep -o -w -E \'[0-9]*\%\' | tr -d \'%\''
    return execute(command)[0]
        
def swapUsage():
    command=os.environ['MY_HOME'] + '/scripts/memory_information SwapFree'
    free=execute(command)[0]
    command=os.environ['MY_HOME'] + '/scripts/memory_information SwapTotal'
    total=execute(command)[0]
    if free == None or len(str(free)) == 0 or int(total) == 0:
        return -1
    return 100 - int((float(free)/float(total))*100)

def getKernelVersion():
    command='uname -r'
    return execute(command)[0]

def hostname():
    command = os.environ['MY_HOME'] + '/scripts/hostname.sh'
    return execute(command)[0]
    
def update_check():
    command = 'sudo system_update_check.sh 0<&- &>/dev/null &'
    execute(command)
    return 0
    
def update_check_for_app():
    command = 'update_check.py'
    json_body = execute(command)[0]  
    json_struct = json.loads(json_body)
    composeJS(json.dumps(json_struct))
    sys.exit(0)
    
def application_update():
    command = "sudo pi-web-agent-update -a"
    return execute(command)[1]
    
def update_check_quick():
    command = 'sudo pi-update -q'
    return execute(command)
        
def update_check_js():
    command = 'sudo pi-update -q'
    a=execute(command)
    return a[1] == NEW_UPDATE

def response(msg):
    element=ET.Element('response')
    element.text=msg
    composeXMLDocument(element)
    
def update_check_with_version():
    command = 'sudo pi-update -c'
    a=execute(command)
    response=a[1]
    return [response == NEW_UPDATE, a[0]]

def turn_service(service_name, turn):
    if (turn == "on"):
        newturn = "start"
    else:
        newturn = "stop"
    command='sudo service ' + service_name + ' ' + newturn    
    a, exit_code=execute(command)
    msg = {'response':exit_code}
    composeJS(json.dumps(msg))
      
    sys.exit(0)
    
def get_temperature():
    command='sudo /opt/vc/bin/vcgencmd measure_temp'
    output, exit_code = execute(command)
    if not exit_code == 0:
        return 'N/A'
    else:
        degrees_in_celcius=output.split('=')[1].split("'")[0]
        return degrees_in_celcius

def manage_vnc(turn):
    command = 'sudo /etc/init.d/vncboot ' + turn
    output, errcode = execute(command)

def get_services_status():
    sm = serviceManagerBuilder()
    composeJS(json.dumps(sm.services_js))
    sys.exit(0)

def all_status():
    memory_usage = getMemoryUsage()
    kernel = getKernelVersion()
    disk_usage = getDiskUsage()
    hostip = hostname()
    update = update_check_js()
    temperature = get_temperature()
    swap = swapUsage()
    
    statuses = {'mem':memory_usage, 'kernel':kernel.strip(), 'disk':disk_usage.strip(),\
     'hostname':hostip.strip(), 'ucheck':update, 'temp':temperature, 'swap':swap}
    json_string = json.dumps(statuses)
    composeJS(json_string)
    sys.exit(0)

def checkFlags(text):
    lines = text.split('\n')
    del lines[-1]
    package_line = lines[-1]
    flags = package_line.split()[0]
    if flags.find('r') >= 0:
        return False
    if flags.find('un') >= 0:
        return False
        
    return True

def package_is_installed(package_name):
    bashCommand = "dpkg-query -l " + package_name
    output, errorcode = execute( bashCommand )
    if errorcode != 0:
        installed=False
    elif errorcode == 0 and checkFlags(output):
        installed=True
    else:
        installed=False
    return installed
    
def main():
    cmds = {'update':update_check_js, 'edit_service':turn_service, 'apt': getAptBusy, 'check' : update_check,\
      'check_app': update_check_for_app, 'update_app' : application_update, 'all_status':all_status, 'services':get_services_status}
    fs = cgi.FieldStorage()
    if 'cmd' not in fs or fs['cmd'].value not in cmds.keys():
        response('Error')
    else:
        if 'param1' in fs and 'param2' in fs:
            response(str(cmds[fs['cmd'].value](fs['param1'].value, fs['param2'].value)))        
        else:
            response(str(cmds[fs['cmd'].value]()))  
    

if __name__ == '__main__':
    main()    
    
