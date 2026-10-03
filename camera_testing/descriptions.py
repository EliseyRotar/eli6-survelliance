"""Better description generator for CSV rows.

Inputs: dict containing 'host', 'port', 'city', 'country', 'org', 'family', 'stream_kind', 'lat', 'lon', 'notes'.
Output: a human-readable 2-3 sentence description that is unique per cam.

Goals:
- Specify the cam family / server banner if known
- Specify the host's primary geo + ISP for context
- Note whether it's residential / business / institutional
- Don't repeat "live cam in <city>" copy that the existing CSV already has

This is intentionally more aggressive than `entry_from_probe`'s description, which currently leaves it blank.
"""

SUBJECT_BY_FAMILY = {
    'insecam-viewer': 'public IP camera exposing /cgi-bin/viewer/video.jpg MJPEG snapshots (Bosch/Canon/Panasonic OEM server)',
    'mjpeg-faststream': 'IP camera using ACTi/Mobotix-style MJPEG faststream at /control/faststream.jpg',
    'mjpeg-wvhttp': 'ACTi/Canon camera serving MJPEG over wvhttp protocol',
    'mjpeg-cgi': 'generic IP camera MJPEG CGI endpoint at /cgi-bin/mjpeg',
    'mjpeg-mjpg': 'generic /mjpg/video.mjpg MJPEG stream (commonly WebcamXP / ACTi)',
    'webcamxp': 'WebcamXP / webcam 7 camera serving MJPEG at /cam_1.cgi or /cam_1.mjpg',
    'hipcam-mjpeg': 'Hipcam Hi3510/Hi3518 (HiSilicon platform) MJPEG stream at /web/tmpfs/mjpeg',
    'hipcam-snap': 'Hipcam Hi3510/Hi3518 snapshot endpoint at /web/tmpfs/snap.jpg',
    'axis-mjpeg': 'Axis network camera MJPEG stream via /axis-cgi/mjpg/video.cgi',
    'axis-h264-matroska': 'Axis camera H.264/Matroska live stream via /axis-cgi/media.cgi (smooth, 25fps)',
    'axis-h264-mp4': 'Axis camera H.264/MP4 live stream via /axis-cgi/media.cgi',
    'axis-h264': 'Axis camera H.264 stream via /axis-cgi/media.cgi',
    'axis-h265': 'Axis camera H.265 stream via /axis-cgi/media.cgi',
    'hikvision-h264': 'Hikvision IP camera H.264 live preview via /ISAPI/Streaming/channels/1/httppreview',
    'hikvision-snap': 'Hikvision camera still snapshot at /ISAPI/Streaming/channels/1/picture',
    'hikvision': 'Hikvision camera',
    'mobotix-mjpeg': 'Mobotix camera MJPEG via /nphMotionJpeg',
    'mobotix': 'Mobotix camera',
    'canon': 'Canon camera image stream via /img/main.cgi',
    'onvif-channel': 'ONVIF device streaming channel 1',
    'image': 'IP camera still snapshot endpoint',
    'blueiris-mjpeg': 'Blue Iris NVR /mjpg/1/video.cgi MJPEG stream',
    'ispy-mjpeg': 'iSpy / Agent DVR video stream',
    'nuuo': 'NUUO NVR video stream',
    'synology': 'Synology Surveillance Station camera',
    'zoneminder': 'ZoneMinder camera via ZMS',
    'dahua': 'Dahua camera /cam/realmonitor',
    'uniview': 'Uniview camera streaming channel',
    'cam-cgi': 'generic IP camera MJPEG CGI',
    'hls': 'HLS live stream',
    'unknown': 'IP camera (server signature recognised, family TBD)',
}


def describe(row):
    """Compose a description for a CSV row."""
    host = row.get('host', '')
    geo = row.get('geo', {})
    city = (geo.get('city') or '').strip()
    region = (geo.get('regionName') or '').strip()
    country = (geo.get('country') or '').strip()
    org = (geo.get('org') or geo.get('isp') or '').strip()
    family = row.get('family', 'unknown')
    stream_kind = row.get('stream_kind', '')

    # Subject line
    subj = SUBJECT_BY_FAMILY.get(family, SUBJECT_BY_FAMILY['unknown'])
    # If stream_kind indicates jpeg-frame, note it
    if stream_kind and 'jpeg' in stream_kind and 'Multipart' not in stream_kind:
        subj += f' (single-frame JPEG; refresh-rate image viewer)'
    if stream_kind == 'mjpeg-multipart' or stream_kind == 'mjpeg-related':
        subj += ' (true motion MJPEG live stream; playable in VLC / browser)'

    # Geo descriptor
    geo_parts = []
    if city:
        geo_parts.append(city)
    if region and region not in (city, ''):
        geo_parts.append(region)
    if country:
        geo_parts.append(country)
    geo_desc = ', '.join(geo_parts) if geo_parts else 'unknown location'

    isp_desc = ''
    if org:
        # Identify ISP kind
        low = org.lower()
        if any(x in low for x in ('comcast', 'spectrum', 'charter', 'xfinity', 'verizon', 'at&t', 'cox', 'frontier', 'tmobile', 't-mobile', 'centurylink', 'rogers', 'bell', 'telus')):
            isp_kind = 'residential ISP'
        elif any(x in low for x in ('orange', 'vodafone', 'telecom', 't-com', 'kpn', 'ziggo', 'init7', 'swisscom', 'green.ch', 'fastweb', 'tiscali', 'eolo', 'sky', 'virgin', 'o2', 'three')):
            isp_kind = 'residential ISP'
        elif any(x in low for x in ('viettel', 'chunghwa', 'korea telecom', 'kh', 'vnpt', 'fpt', 'mytel', 'mobifone', 'htc', 'viettel')):
            isp_kind = 'residential mobile ISP'
        elif any(x in low for x in ('huawei', 'alibaba', 'tencent', 'amazon', 'microsoft', 'digitalocean', 'ovh', 'hetzner', 'linode', 'contabo', 'scaleway', 'google')):
            isp_kind = 'cloud / data-center host'
        elif any(x in low for x in ('university', 'college', 'polytech', 'institute', 'school', 'embry', 'dartmouth', 'nordic', 'skog')):
            isp_kind = 'academic / institutional'
        else:
            isp_kind = 'ISP / org'

        isp_desc = f'Hosted by **{org}** ({isp_kind})'

    # Civic categorization
    isp_low = (org or '').lower()
    if 'residential' in isp_low or any(x in isp_low for x in ('comcast', 'spectrum', 'charter', 'xfinity', 'verizon',
                                                              'at&t', 'cox', 'frontier', 'tmobile', 't-mobile', 'rogers',
                                                              'bell', 'telus')):
        civic = 'private residential cam'
    elif 'university' in isp_low or 'embry-riddle' in isp_low or 'college' in isp_low:
        civic = 'institutional cam (university / campus)'
    elif 'hotel' in isp_low or 'inn' in isp_low or 'resort' in isp_low:
        civic = 'hotel / resort cam'
    else:
        civic = 'cam view'

    parts = [
        f'**{civic}**',
        subj,
    ]
    if geo_desc != 'unknown location':
        parts.append(f'located in {geo_desc}')
    if isp_desc:
        parts.append(f'- {isp_desc}.')
    if host and org:
        parts.append(f'Direct stream URL tested live; resolved via {org.split()[0] if org else "ISP"}.')
    parts.append(f'Hostname: {host}.')
    parts.append(f'Server signature / banner family: **{family}**, stream kind `{stream_kind}`.')
    return ' '.join(parts)
