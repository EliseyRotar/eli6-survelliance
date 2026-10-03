#!/usr/bin/env python3
"""Probe RTSP/ONVIF on wc2.dartmouth.edu"""
import socket

# ONVIF WS-Discovery probe
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)
msg = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Envelope xmlns:dn="http://www.onvif.org/ver10/network/wsdl" xmlns="http://www.w3.org/2003/05/soap-envelope">'
    '<Header><wsa:MessageID xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">uuid:probe-1</wsa:MessageID>'
    '<wsa:To xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>'
    '<Action xmlns="http://www.w3.org/2005/08/addressing">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</Action></Header>'
    '<Body><Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
    '<Types>dn:NetworkVideoTransmitter</Types></Probe></Body></Envelope>'
)
try:
    sock.sendto(msg.encode(), ('239.255.255.250', 3702))
    resp, addr = sock.recvfrom(8192)
    print('Got ONVIF response from', addr)
    print(resp.decode('utf-8', errors='ignore')[:2000])
except socket.timeout:
    print('No ONVIF multicast response (probably no mDNS/WS-Discovery in our network)')
except Exception as e:
    print('ONVIF error:', e)
sock.close()

# RTSP GET_PARAMETER to server root
print()
print('=== RTSP GET_PARAMETER to / ===')
s = socket.create_connection(('wc2.dartmouth.edu', 554), timeout=5)
s.settimeout(5)
req = 'GET_PARAMETER rtsp://wc2.dartmouth.edu/ RTSP/1.0\r\nCSeq: 99\r\n\r\n'
s.send(req.encode())
try:
    resp = s.recv(4096).decode('latin-1', errors='ignore')
    print(resp)
except Exception as e:
    print('Timeout:', e)
s.close()

# RTSP DESCRIBE to '/'
print()
print('=== RTSP DESCRIBE to / ===')
s = socket.create_connection(('wc2.dartmouth.edu', 554), timeout=5)
s.settimeout(5)
req = 'DESCRIBE rtsp://wc2.dartmouth.edu/ RTSP/1.0\r\nCSeq: 100\r\nAccept: application/sdp\r\n\r\n'
s.send(req.encode())
try:
    resp = s.recv(4096).decode('latin-1', errors='ignore')
    print(resp)
except Exception as e:
    print('Timeout:', e)
s.close()

# RTSP describe with various paths - get SDP
print()
print('=== Trying various path patterns ===')
import re
for path in ['/live.sdp', '/live/0', '/live/1', '/mpeg4.amp', '/axis-media/media.amp',
             '/media/video0', '/onvif/streaming/channels/101', '/streaming/channels/101',
             '/video.sdp', '/h264', '/h264.sdp']:
    s = socket.create_connection(('wc2.dartmouth.edu', 554), timeout=5)
    s.settimeout(3)
    req = 'DESCRIBE rtsp://wc2.dartmouth.edu' + path + ' RTSP/1.0\r\nCSeq: 101\r\nAccept: application/sdp\r\n\r\n'
    s.send(req.encode())
    try:
        resp = s.recv(2048).decode('latin-1', errors='ignore')
        # Get just status line
        lines = resp.split('\r\n')
        print(path, '->', lines[0])
        if '200 OK' in lines[0]:
            print('  SDP:')
            for line in lines[1:10]:
                print('   ', line)
    except Exception as e:
        print(path, '->', 'timeout')
    s.close()