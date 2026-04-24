import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

CONSUL = 'http://consul:8500'

SERVICES = [
    {
        'ID': 'auth-service-1', 'Name': 'auth-service',
        'Address': 'agriguard-auth', 'Port': 8001,
        'path': '/api/auth', 'health': '/api/auth/health/', 'priority': 100,
    },
    {
        'ID': 'farm-service-1', 'Name': 'farm-service',
        'Address': 'agriguard-farm', 'Port': 8002,
        'path': '/api/farms', 'health': '/api/farms/health/', 'priority': 100,
    },
    {
        'ID': 'diagnosis-service-1', 'Name': 'diagnosis-service',
        'Address': 'agriguard-diagnosis', 'Port': 8003,
        'path': '/api/diagnosis', 'health': '/api/diagnosis/health/', 'priority': 100,
    },
    {
        'ID': 'notification-service-1', 'Name': 'notification-service',
        'Address': 'agriguard-notification', 'Port': 8004,
        'path': '/api/notify', 'health': '/api/notify/health/', 'priority': 100,
    },
    {
        'ID': 'gateway-service-1', 'Name': 'gateway-service',
        'Address': 'agriguard-gateway', 'Port': 8080,
        'path': '/', 'health': '/health/', 'priority': 1,
    },
]

def register_all():
    ok = 0
    for s in SERVICES:
        try:
            payload = {
                'ID':      s['ID'],
                'Name':    s['Name'],
                'Address': s['Address'],
                'Port':    s['Port'],
                'Tags': [
                    'traefik.enable=true',
                    f"traefik.http.routers.{s['Name']}.rule=PathPrefix(`{s['path']}`)",
                    f"traefik.http.routers.{s['Name']}.entrypoints=web",
                    f"traefik.http.routers.{s['Name']}.priority={s['priority']}",
                ],
                'Check': {
                    'HTTP':     f"http://{s['Address']}:{s['Port']}{s['health']}",
                    'Interval': '10s',
                    'Timeout':  '3s',
                },
            }
            r = requests.put(
                f'{CONSUL}/v1/agent/service/register',
                json=payload, timeout=5,
            )
            if r.status_code == 200:
                ok += 1
            else:
                logger.warning(f"Failed {s['Name']}: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"Error registering {s['Name']}: {e}")
    logger.info(f"Registered {ok}/{len(SERVICES)} services")

if __name__ == '__main__':
    # Wait for all services to be up first
    logger.info('Waiting 20s for services to start...')
    time.sleep(20)
    logger.info('Consul registrar started — registering every 60s')
    while True:
        register_all()
        time.sleep(60)
