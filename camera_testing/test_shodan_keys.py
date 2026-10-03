import requests, time

KEYS = [
    'OefcMxcunkm72Po71vVtX8zUN57vQtAC',
    'PSKINdQe1GyxGgecYz2191H2JoS9qvgD',
    'pHHlgpFt8Ka3Stb5UlTxcaEwciOeF2QM',
    '61TvA2dNwxNxmWziZxKzR5aO9tFD00Nj',
    'xTbXXOSBr0R65OcClImSwzadExoXU4tc',
    'EJV3A4Mka2wPs7P8VBCO6xcpRe27iNJu',
    'mEuInz8UH1ixLGJq4oQhEiJORERVG5xc',
    'lkY0ng0XMo29zEhzyw3ibQfeEBxghwPF',
    'syeCnFndQ8TE4qAGvhm9nZLBZOBgoLKd',
    '7TeyFZ8oyLulHwYUOcSPzZ5w3cLYib61',
    'v4YpsPUJ3wjDxEqywwu6aF5OZKWj8kik',
    'dTNGRiwYNozXIDRf5DWyGNbkdiS5m3JK',
    'kdnzf4fsYWQmGajRDn3hB0RElbUlIaqu',
    'boYedPn8iDWi6GDSO6h2kz72VLt6bZ3S',
    'FQNAMUdkeqXqVOdXsTLYeatFSpZSktdb',
    'OygcaGSSq46Lg5fZiADAuFxl4OBbn7zm',
    'XAbsu1Ruj5uhTNcxGdbGNgrh9WuMS1B6',
    'nkGd8uVE4oryfUVvioprswdKGmA5InzZ',
    'XYdjHDeJM36AjDfU1feBsyMJIj8XxGzD',
    'EBeU0lGqtIO6yCxVFCWC4nUVbvovtjo5',
    'e9SxSRCE1xDNS4CzyWzOQTUoE55KB9HX',
    'Jvt0B5uZIDPJ5pbCqMo12CqD7pdnMSEd',
    'kNWoMbgDfszHJqH95uAe0lelO4AsQIim',
    'rl89iPZ0hf7oVDyjz7jCHf65qEVKwawm',
    '3tj9ovMyEtTxhWOhTiEK4GcwNkVSj3B8',
    'uWlAoYQLXeFPP0BHM7Jca0hUYyr57gf1',
    'epUwsq69bGZwhaFsiHYCnyvO3mWcXatU',
    '7XRdrUMb9i2N6P6rqyXIM3PyDGBl6Wyg',
    'Z2soDBnFLLNRKZsamG9hUQLtBBh9GTwH',
    'mmNAl4hUHApCF27NlqHh79W8mYMH8GKT',
    'XSDjF1VpKNImZxAveSnnJuSrWW7sbBFs',
    '2sWQ6joUfopOtzQRSYW6JSs9tqeoiaqa',
    'qBA6erhzKJWy2L51g0FjgbYo4PI2vYwD',
    'bIWOjW69QxF96gvhb4a1vNN7JgyjPYQ4',
]
working = []
for k in KEYS:
    try:
        r = requests.get('https://api.shodan.io/api-info', params={'key': k}, timeout=8)
        if r.status_code == 200:
            j = r.json()
            credits = j.get('query_credits', 0)
            plan = j.get('plan', '?')
            print(f'  WORKING  {k[:8]}... credits={credits} plan={plan}')
            working.append((k, j))
        else:
            print(f'  DEAD     {k[:8]}... HTTP {r.status_code}')
    except Exception as e:
        print(f'  ERR      {k[:8]}... {e}')
    time.sleep(0.15)

print()
print(f'WORKING: {len(working)} of {len(KEYS)}')
for k, j in working:
    print(f'  {k[:12]}... {j}')
