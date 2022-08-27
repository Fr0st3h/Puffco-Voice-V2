import flask
import json
import threading
import socket
import json
from readsettings import ReadSettings
import asyncio
from bleak import BleakScanner, BleakClient
import logging
from hashlib import sha256
from base64 import b64decode

logging.getLogger("werkzeug").disabled = True

config = ReadSettings('config.json')

print('\n\nPuffco Voice v2 By Fr0st3h\n\n')

async def getFirmware():
        try:
            firmware = await client.read_gatt_char('00002A28-0000-1000-8000-00805F9B34FB', response=True)
            return firmware.decode("utf-8")
        except:
            return

async def firmwareXAuth():
    try:
        DEVICE_HANDSHAKE = bytearray(b64decode('FUrZc0WilhUBteT2JlCc+A=='))
        print("Reading AccessSeedKey from Puffco..")
        accessSeedKey = list(await client.read_gatt_char('f9a98c15-c651-4f34-b656-d100bf5800e0'))
        newAccessSeedKey = bytearray(32)
        print("Encrypting new AccessSeedKey..")
        for i in range(0, 16):
            newAccessSeedKey[i] = DEVICE_HANDSHAKE[i]
            newAccessSeedKey[i+16] = accessSeedKey[i]
            
        encodedKey = sha256(newAccessSeedKey).hexdigest()
        finalKey = bytearray([int(encodedKey[i:i+2], 16) for i in range(0, len(encodedKey), 2)][0:16])
        print("Writing New AccessSeedKey..")
        await client.write_gatt_char('f9a98c15-c651-4f34-b656-d100bf5800e0', finalKey, response=True)
        return True
    except Exception as e:
        print(f"Exception while Authenticating with Firmware X: {e}")
        return False

async def findPuffco():
    scanning = True
    while scanning:
        print("Searching for your puffco..")
        devices = await BleakScanner.discover()
        for d in devices:
            service_uuids = d.metadata.get('uuids')
        
            if "06caf9c0-74d3-454f-9be9-e30cd999c17a" in service_uuids:
                foundPro = input(f'Found Peak Pro "{d.name}" ({d.address}). Do you want to use this device? (y/n): ')
                if(foundPro.lower() == 'y'):
                    config['Puffco_MacAddress'] = d.address
                    config['Puffco_Name'] = d.name
                    config.save()
                    
                scanning = False
                
asyncio.run(findPuffco())

client = BleakClient(config['Puffco_MacAddress'])

class UPNPResponderThread(threading.Thread):

    UPNP_RESPONSE = """HTTP/1.1 200 OK
CACHE-CONTROL: max-age=60
EXT:
LOCATION: http://{0}:{1}/description.xml
SERVER: FreeRTOS/6.0.5, UPnP/1.0, IpBridge/0.1
ST: urn:schemas-upnp-org:device:basic:1
USN: uuid:Socket-1_0-221438K0100073::urn:schemas-upnp-org:device:basic:1

""".format(config['Local_IPv4'], 80).replace("\n", "\r\n").encode('utf-8')

    stop_thread = False

    def run(self):
        print("UPNP Thread Started")
        ssdpmc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        ssdpmc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ssdpmc_socket.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(str(config['Local_IPv4'])))
        ssdpmc_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton("239.255.255.250") + socket.inet_aton(str(config['Local_IPv4'])))

        ssdpmc_socket.bind((config['Local_IPv4'], 1900))

        while True:
            try:
                data, addr = ssdpmc_socket.recvfrom(1024)
            except socket.error as e:
                if self.stop_thread == True:
                    print("UPNP Reponder Thread closing socket and shutting down...")
                    ssdpmc_socket.close()
                    return
                print ("UPNP Responder socket.error exception occured: {0}".format(e.__str__))

            if "M-SEARCH" in data.decode('utf-8'):
                ssdpout_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                ssdpout_socket.sendto(self.UPNP_RESPONSE, addr)
                ssdpout_socket.close()

    def stop(self):
        self.stop_thread = True

upnp_responder = UPNPResponderThread()
app = flask.Flask(__name__)

DESCRIPTION_XML_RESPONSE = """<?xml version="1.0" encoding="UTF-8" ?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
<specVersion>
<major>1</major>
<minor>0</minor>
</specVersion>
<URLBase>http://{0}:{1}/</URLBase>
<device>
<deviceType>urn:schemas-upnp-org:device:Basic:1</deviceType>
<friendlyName>HA-Echo ({0})</friendlyName>
<manufacturer>Royal Philips Electronics</manufacturer>
<manufacturerURL>http://www.philips.com</manufacturerURL>
<modelDescription>Philips hue Personal Wireless Lighting</modelDescription>
<modelName>Philips hue bridge 2015</modelName>
<modelNumber>BSB002</modelNumber>
<modelURL>http://www.meethue.com</modelURL>
<serialNumber>1234</serialNumber>
<UDN>uuid:2f402f80-da50-11e1-9b23-001788255acc</UDN>
<presentationURL>index.html</presentationURL>
<iconList>
<icon>
<mimetype>image/png</mimetype>
<height>48</height>
<width>48</width>
<depth>24</depth>
<url>hue_logo_0.png</url>
</icon>
<icon>
<mimetype>image/png</mimetype>
<height>120</height>
<width>120</width>
<depth>24</depth>
<url>hue_logo_3.png</url>
</icon>
</iconList>
</device>
</root>
""".format(config['Local_IPv4'], 80)

@app.route('/description.xml', strict_slashes=False, methods = ['GET'])
async def hue_description_xml():
    return flask.Response(DESCRIPTION_XML_RESPONSE, mimetype='text/xml')

@app.route('/api/<token>/lights', strict_slashes=False, methods = ['GET'])
@app.route('/api/<token>/lights/', strict_slashes=False, methods = ['GET'])
async def hue_api_lights(token):

    json_response = {}

    json_response[0] = {
        'id': "100",
        'state': {
            'on': config['CurrentSettings']['Enabled'],
            'bri': config['CurrentSettings']['Brightness'],
            'hue':config['CurrentSettings']['Hue'],
            'sat':config['CurrentSettings']['Saturation'],
            'effect': 'none',
            'xy':[0,0],
            'alert': 'none',
            'reachable':True, 
            'colormode':'hs'
        },
        'type': 'Extended color light',
        'name': f'{config["Puffco_Name"]} (Puffco)',
        'modelid': 'LWB004',
        'manufacturername': 'Philips',
        'uniqueid': '00:f8:99:13:9d:f5:e1:04-13',
        'swversion': '66012040'
    }
    print(f"Sent Light GET response (/api/{token}/lights/)")
    return flask.Response(json.dumps(json_response), mimetype='application/json')

@app.route('/api/<token>/lights/<int:id_num>/state', methods = ['PUT'])
async def hue_api_put_light(token, id_num):
    request_json = flask.request.get_json(force=True)
    
    if 'hue' in request_json:
        config['CurrentSettings']['Hue'] = request_json['hue']
        config['CurrentSettings']['Saturation'] = request_json['sat']
        config['CurrentSettings']['Enabled'] = True
        config.save()
        return flask.Response(json.dumps([{'success': {'/lights/{0}/state/hue': request_json['hue']}}]), mimetype='application/json', status=200)
    
    if 'sat' in request_json:
        config['CurrentSettings']['Hue'] = request_json['hue']
        config['CurrentSettings']['Saturation'] = request_json['sat']
        config['CurrentSettings']['Enabled'] = True
        config.save()
        return flask.Response(json.dumps([{'success': {'/lights/{0}/state/sat': request_json['sat']}}]), mimetype='application/json', status=200)
    
    if 'bri' in request_json:
        config['CurrentSettings']['Brightness'] = request_json['bri']
        config['CurrentSettings']['Enabled'] = True
        config.save()
        if(request_json['bri'] >= 4 and request_json['bri'] <= 64):
            print("Preheating Profile 1")
            preheatBytes = bytearray([0, 0, 0, 0])
        elif(request_json['bri'] >= 64 and request_json['bri'] <= 128):
            print("Preheating Profile 2")
            preheatBytes = bytearray([0, 0, 128, 63])
        elif(request_json['bri'] >= 128 and request_json['bri'] <= 191):
            print("Preheating Profile 3")
            preheatBytes = bytearray([0, 0, 0, 64])
        elif(request_json['bri'] >= 128 and request_json['bri'] <= 254):
            print("Preheating Profile 4")
            preheatBytes = bytearray([0, 0, 64, 64])
        await client.write_gatt_char('f9a98c15-c651-4f34-b656-d100bf580041', preheatBytes, response=True)
        startPreheatBytes = bytearray([0, 0, 224, 64])
        await client.write_gatt_char('F9A98C15-C651-4F34-B656-D100BF580040', startPreheatBytes, response=True)
        return flask.Response(json.dumps([{'success': {'/lights/{0}/state/bri': request_json['bri']}}]), mimetype='application/json', status=200)

    if 'on' in request_json and request_json['on'] == True:
        config['CurrentSettings']['Enabled'] = True
        config.save()
        startPreheatBytes = bytearray([0, 0, 224, 64])
        await client.write_gatt_char('F9A98C15-C651-4F34-B656-D100BF580040', startPreheatBytes, response=True)
        print("Started preheating")
        return flask.Response(json.dumps([{'success': {'/lights/{0}/state/on'.format(id_num): True }}]), mimetype='application/json', status=200)

    if 'on' in request_json and request_json['on'] == False:
        print("Canceled Preheat")
        config['CurrentSettings']['Enabled'] = False
        config.save()
        cancelPreheatBytes = bytearray([0, 0, 0, 65])
        await client.write_gatt_char('F9A98C15-C651-4F34-B656-D100BF580040', cancelPreheatBytes, response=True)
        return flask.Response(json.dumps([{'success': {'/lights/{0}/state/on'.format(id_num): False }}]), mimetype='application/json', status=200)

    print(f"Unhandled API request: {request_json}")
    flask.abort(500)

@app.route('/api/<token>/lights/<int:id_num>', strict_slashes=False, methods = ['GET'])
async def hue_api_individual_light(token, id_num):


    json_response = {
        'id': "100",
        'state': {
            'on': config['CurrentSettings']['Enabled'],
            'bri': config['CurrentSettings']['Brightness'],
            'hue':config['CurrentSettings']['Hue'],
            'sat':config['CurrentSettings']['Saturation'],
            'effect': 'none',
            'xy':[0,0],
            'alert': 'none',
            'reachable':True, 
            'colormode':'hs'
        },
        'type': 'Extended color light',
        'name': f'{config["Puffco_Name"]} (Puffco)',
        'modelid': 'LWB004',
        'manufacturername': 'Philips',
        'uniqueid': '00:f8:99:13:9d:f5:e1:04-13',
        'swversion': '66012040'
    }

    return flask.Response(json.dumps(json_response), mimetype='application/json')

@app.route('/api/<token>/groups', strict_slashes=False)
@app.route('/api/<token>/groups/0', strict_slashes=False)
async def hue_api_groups_0(token):
    print("ERROR: If echo requests /api/groups that usually means it failed to parse /api/lights.")
    print("This probably means the Echo didn't like something in a name.")
    return flask.abort(500)

@app.route('/api', strict_slashes=False, methods = ['POST'])
async def hue_api_create_user():
    request_json = flask.request.get_json(force=True)

    if 'devicetype' not in request_json:
        return flask.abort(500)

    print("Echo asked to be assigned a username")
    return flask.Response(json.dumps([{'success': {'username': 'PuffcoVoiceByFr0st3h'}}]), mimetype='application/json')

async def main():
    global upnp_responder
    global app

    print("Trying to connect to puffco..")
    await client.connect()
    if(client.is_connected):
        firmware = await getFirmware()
        if(firmware == 'X'):
            authenticated = await firmwareXAuth()
            if(authenticated):
                print("Authenticated With Firmware X!")
            else:
                print("Failed to authenticate with Firmware X")
                return
        print("Connected! Starting HTTP Server..")
    else:
        print("Failed to connect")
        return

    upnp_responder.start()
    print("Starting Flask for HTTP listening on {0}:{1}...".format(config['Local_IPv4'], 80))
    try:
        app.run(host=config['Local_IPv4'], port=80, threaded=True, use_reloader=False)
    except Exception as e:
        print(f"Exception while starting Flask {e}")
        

if __name__ == "__main__":
    asyncio.run(main())
