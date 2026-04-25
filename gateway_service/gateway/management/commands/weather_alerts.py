import json
import time
import logging
import requests
import pika
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

WILAYA_COORDS = {
    'alger':              {'lat': 36.74, 'lon': 3.06,  'name': 'Alger'},
    'oran':               {'lat': 35.69, 'lon': -0.64, 'name': 'Oran'},
    'constantine':        {'lat': 36.36, 'lon': 6.61,  'name': 'Constantine'},
    'annaba':             {'lat': 36.90, 'lon': 7.76,  'name': 'Annaba'},
    'batna':              {'lat': 35.55, 'lon': 6.17,  'name': 'Batna'},
    'setif':              {'lat': 36.19, 'lon': 5.41,  'name': 'Sétif'},
    'tizi_ouzou':         {'lat': 36.71, 'lon': 4.04,  'name': 'Tizi Ouzou'},
    'bejaia':             {'lat': 36.75, 'lon': 5.06,  'name': 'Béjaïa'},
    'blida':              {'lat': 36.47, 'lon': 2.83,  'name': 'Blida'},
    'biskra':             {'lat': 34.85, 'lon': 5.73,  'name': 'Biskra'},
    'ouargla':            {'lat': 31.95, 'lon': 5.32,  'name': 'Ouargla'},
    'tlemcen':            {'lat': 34.88, 'lon': -1.32, 'name': 'Tlemcen'},
    'ghardaia':           {'lat': 32.49, 'lon': 3.67,  'name': 'Ghardaïa'},
    'skikda':             {'lat': 36.87, 'lon': 6.90,  'name': 'Skikda'},
    'tiaret':             {'lat': 35.37, 'lon': 1.32,  'name': 'Tiaret'},
    'saida':              {'lat': 34.83, 'lon': 0.15,  'name': 'Saïda'},
    'mostaganem':         {'lat': 35.93, 'lon': 0.09,  'name': 'Mostaganem'},
    'medea':              {'lat': 36.27, 'lon': 2.75,  'name': 'Médéa'},
    'msila':              {'lat': 35.70, 'lon': 4.54,  'name': "M'Sila"},
    'mascara':            {'lat': 35.40, 'lon': 0.14,  'name': 'Mascara'},
    'djelfa':             {'lat': 34.67, 'lon': 3.26,  'name': 'Djelfa'},
    'jijel':              {'lat': 36.82, 'lon': 5.77,  'name': 'Jijel'},
    'guelma':             {'lat': 36.46, 'lon': 7.43,  'name': 'Guelma'},
    'tipaza':             {'lat': 36.59, 'lon': 2.44,  'name': 'Tipaza'},
    'boumerdes':          {'lat': 36.76, 'lon': 3.48,  'name': 'Boumerdès'},
    'ain_defla':          {'lat': 36.26, 'lon': 1.97,  'name': 'Aïn Defla'},
    'relizane':           {'lat': 35.73, 'lon': 0.56,  'name': 'Relizane'},
    'mila':               {'lat': 36.45, 'lon': 6.26,  'name': 'Mila'},
    'tamanrasset':        {'lat': 22.78, 'lon': 5.52,  'name': 'Tamanrasset'},
    'adrar':              {'lat': 27.87, 'lon': -0.29, 'name': 'Adrar'},
    'bechar':             {'lat': 31.62, 'lon': -2.22, 'name': 'Béchar'},
    'tebessa':            {'lat': 35.40, 'lon': 8.12,  'name': 'Tébessa'},
    'naama':              {'lat': 33.27, 'lon': -0.31, 'name': 'Naâma'},
    'souk_ahras':         {'lat': 36.28, 'lon': 7.95,  'name': 'Souk Ahras'},
    'khenchela':          {'lat': 35.42, 'lon': 7.14,  'name': 'Khenchela'},
    'el_oued':            {'lat': 33.37, 'lon': 6.86,  'name': 'El Oued'},
    'el_tarf':            {'lat': 36.77, 'lon': 8.31,  'name': 'El Tarf'},
    'tissemsilt':         {'lat': 35.60, 'lon': 1.81,  'name': 'Tissemsilt'},
    'oum_el_bouaghi':     {'lat': 35.87, 'lon': 7.11,  'name': 'Oum El Bouaghi'},
    'ain_temouchent':     {'lat': 35.30, 'lon': -1.14, 'name': 'Aïn Témouchent'},
    'bordj_bou_arreridj': {'lat': 36.07, 'lon': 4.76,  'name': 'Bordj Bou Arréridj'},
    'sidi_bel_abbes':     {'lat': 35.19, 'lon': -0.63, 'name': 'Sidi Bel Abbès'},
    'laghouat':           {'lat': 33.80, 'lon': 2.86,  'name': 'Laghouat'},
    'bouira':             {'lat': 36.37, 'lon': 3.90,  'name': 'Bouira'},
    'el_bayadh':          {'lat': 33.68, 'lon': 1.02,  'name': 'El Bayadh'},
    'illizi':             {'lat': 26.48, 'lon': 8.47,  'name': 'Illizi'},
    'tindouf':            {'lat': 27.67, 'lon': -8.15, 'name': 'Tindouf'},
}

# Only severities that warrant a push notification.
# 'good' (perfect conditions) is NOT pushed — that's just normal weather.
PUSH_SEVERITIES = {'warning', 'danger'}


def evaluate_alerts(weather: dict, wilaya_name: str) -> list:
    """
    Evaluate current weather conditions and return a list of alert dicts.
    Only returns alerts that are actionable for farmers.
    """
    temp     = weather['temperature_2m']
    humidity = weather['relative_humidity_2m']
    wind     = weather['wind_speed_10m']
    precip   = weather['precipitation']
    code     = weather.get('weathercode', 0)

    alerts = []

    # ── Thunderstorm ──────────────────────────────────────────────────
    if code >= 95:
        alerts.append({
            'severity': 'danger',
            'title':    f'⛈️ Thunderstorm warning — {wilaya_name}',
            'message':  (
                f'Thunderstorms detected in {wilaya_name}. '
                f'Secure all equipment immediately, stay indoors, '
                f'and do not work in the fields. '
                f'Stop all irrigation and spraying now.'
            ),
        })

    # ── Heavy rain / flood risk ───────────────────────────────────────
    elif precip > 15:
        alerts.append({
            'severity': 'danger',
            'title':    f'🌊 Heavy rainfall — {wilaya_name} ({round(precip)}mm)',
            'message':  (
                f'Heavy rain of {round(precip)}mm in {wilaya_name}. '
                f'Check field drainage immediately to prevent waterlogging '
                f'and root damage. Skip all irrigation today.'
            ),
        })
    elif precip > 5:
        alerts.append({
            'severity': 'warning',
            'title':    f'🌧️ Rain today — skip irrigation ({wilaya_name})',
            'message':  (
                f'Rainfall of {round(precip)}mm expected in {wilaya_name}. '
                f'No irrigation needed today — natural moisture is sufficient.'
            ),
        })

    # ── Extreme heat ──────────────────────────────────────────────────
    if temp >= 40:
        alerts.append({
            'severity': 'danger',
            'title':    f'🌡️ Extreme heat — {wilaya_name} {round(temp)}°C',
            'message':  (
                f'Dangerous heat of {round(temp)}°C in {wilaya_name}. '
                f'Water only before 7 AM or after 7 PM. '
                f'Protect seedlings with shade cloth. '
                f'Risk of crop dehydration and sunscald is very high.'
            ),
        })
    elif temp >= 36:
        alerts.append({
            'severity': 'warning',
            'title':    f'🌡️ High heat — {wilaya_name} {round(temp)}°C',
            'message':  (
                f'Temperature reaching {round(temp)}°C in {wilaya_name}. '
                f'Water early morning only. Increase irrigation frequency '
                f'for tomatoes, peppers, and other fruiting crops.'
            ),
        })

    # ── Frost risk ────────────────────────────────────────────────────
    if temp <= 3:
        alerts.append({
            'severity': 'danger',
            'title':    f'🥶 Frost risk — {wilaya_name} {round(temp)}°C',
            'message':  (
                f'Near-freezing temperature of {round(temp)}°C in {wilaya_name}. '
                f'Cover sensitive crops immediately — tomatoes, peppers, '
                f'and cucumbers are at high risk. Do not water tonight.'
            ),
        })
    elif temp <= 6:
        alerts.append({
            'severity': 'warning',
            'title':    f'❄️ Cold alert — {wilaya_name} {round(temp)}°C',
            'message':  (
                f'Cold temperature of {round(temp)}°C in {wilaya_name}. '
                f'Protect young seedlings. Reduce watering — '
                f'cold wet soil causes root rot.'
            ),
        })

    # ── High humidity (fungal risk) ───────────────────────────────────
    if humidity >= 88 and temp >= 15:
        alerts.append({
            'severity': 'warning',
            'title':    f'🍄 Fungal disease risk — {wilaya_name}',
            'message':  (
                f'Very high humidity ({round(humidity)}%) with warm temperatures '
                f'in {wilaya_name}. Ideal conditions for mildew, blight, '
                f'and botrytis. Inspect crops now and apply preventive fungicide.'
            ),
        })

    # ── Strong wind ───────────────────────────────────────────────────
    if wind >= 45:
        alerts.append({
            'severity': 'warning',
            'title':    f'💨 Strong winds — {wilaya_name} {round(wind)} km/h',
            'message':  (
                f'Strong winds of {round(wind)} km/h in {wilaya_name}. '
                f'Postpone all spraying and foliar applications. '
                f'Secure greenhouse covers and protective netting.'
            ),
        })

    return alerts


def get_farmers_by_wilaya(internal_secret: str) -> dict:
    """
    Fetch active farmers grouped by wilaya from the Auth Service.
    Uses a shared internal secret header — no admin login required.
    Returns: { 'alger': ['uuid1', 'uuid2'], 'oran': [...], ... }
    """
    try:
        resp = requests.get(
            'http://agriguard-auth:8001/api/auth/internal/farmers-by-wilaya/',
            headers={'X-Internal-Secret': internal_secret},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            logger.info(
                f"Fetched farmers: {sum(len(v) for v in data.values())} farmers "
                f"across {len(data)} wilayas"
            )
            return data
        else:
            logger.error(
                f"farmers-by-wilaya endpoint returned {resp.status_code}: {resp.text}"
            )
            return {}
    except Exception as e:
        logger.error(f"Could not reach Auth Service to get farmers: {e}")
        return {}


class Command(BaseCommand):
    help = 'Check weather for all active farmer wilayas and push important alerts via RabbitMQ'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true',
                            help='Run continuously')
        parser.add_argument('--interval', type=int, default=180,
                            help='Check interval in minutes (default: 180)')

    def handle(self, *args, **options):
        internal_secret = settings.INTERNAL_API_SECRET

        # Connect to RabbitMQ with retries
        params     = pika.URLParameters(settings.RABBITMQ_URL)
        connection = None
        for attempt in range(10):
            try:
                connection = pika.BlockingConnection(params)
                self.stdout.write(self.style.SUCCESS('Connected to RabbitMQ'))
                break
            except Exception as e:
                self.stdout.write(f'RabbitMQ not ready ({attempt+1}/10): {e} — retrying in 5s')
                time.sleep(5)

        if not connection:
            self.stdout.write(self.style.ERROR('Could not connect to RabbitMQ after 10 attempts'))
            return

        channel = connection.channel()
        channel.exchange_declare(exchange='agriguard', exchange_type='topic', durable=True)

        self.stdout.write(self.style.SUCCESS('Weather scheduler started'))
        self._run_check(channel, internal_secret)

        if options['loop']:
            interval_seconds = options['interval'] * 60
            self.stdout.write(self.style.SUCCESS(
                f'Loop mode — checking every {options["interval"]} minutes'
            ))
            while True:
                time.sleep(interval_seconds)
                try:
                    if connection.is_closed:
                        connection = pika.BlockingConnection(params)
                        channel    = connection.channel()
                        channel.exchange_declare(
                            exchange='agriguard', exchange_type='topic', durable=True
                        )
                    self._run_check(channel, internal_secret)
                except Exception as e:
                    logger.error(f'Error in weather loop: {e}')

    def _run_check(self, channel, internal_secret: str):
        self.stdout.write('Running weather check…')

        farmers_by_wilaya = get_farmers_by_wilaya(internal_secret)
        if not farmers_by_wilaya:
            self.stdout.write(self.style.WARNING(
                'No active farmers found — no alerts will be published. '
                'Check that the Auth Service is reachable and farmers are registered.'
            ))
            return

        total_published = 0

        for wilaya_key, farmer_ids in farmers_by_wilaya.items():
            coords = WILAYA_COORDS.get(wilaya_key)
            if not coords:
                logger.debug(f"No coordinates for wilaya '{wilaya_key}' — skipping")
                continue

            try:
                resp = requests.get(OPEN_METEO_URL, params={
                    'latitude':  coords['lat'],
                    'longitude': coords['lon'],
                    'current':   'temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weathercode',
                    'timezone':  'Africa/Algiers',
                }, timeout=10)
                resp.raise_for_status()
                weather = resp.json()['current']
            except Exception as e:
                logger.error(f"Weather fetch failed for {wilaya_key}: {e}")
                continue

            alerts = evaluate_alerts(weather, coords['name'])

            # Only publish alerts that are warning or danger — not 'good' conditions
            actionable = [a for a in alerts if a['severity'] in PUSH_SEVERITIES]

            if not actionable:
                logger.debug(
                    f"{wilaya_key}: weather OK "
                    f"(temp={weather['temperature_2m']}°C, "
                    f"humidity={weather['relative_humidity_2m']}%, "
                    f"precip={weather['precipitation']}mm) — no alerts"
                )
                continue

            for alert in actionable:
                for farmer_id in farmer_ids:
                    payload = json.dumps({
                        'farmer_id': str(farmer_id),
                        'wilaya':    wilaya_key,
                        'severity':  alert['severity'],
                        'title':     alert['title'],
                        'message':   alert['message'],
                    })
                    channel.basic_publish(
                        exchange='agriguard',
                        routing_key='weather.alert',
                        body=payload,
                        properties=pika.BasicProperties(delivery_mode=2),
                    )
                    total_published += 1

            logger.info(
                f"{wilaya_key}: {len(actionable)} alert(s) "
                f"published to {len(farmer_ids)} farmer(s)"
            )

            time.sleep(0.3)  # be gentle to the free API

        self.stdout.write(self.style.SUCCESS(
            f'Done — {total_published} alert messages published'
        ))