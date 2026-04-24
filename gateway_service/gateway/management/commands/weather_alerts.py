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
    'alger':         {'lat': 36.74, 'lon': 3.06,  'name': 'Alger'},
    'oran':          {'lat': 35.69, 'lon': -0.64, 'name': 'Oran'},
    'constantine':   {'lat': 36.36, 'lon': 6.61,  'name': 'Constantine'},
    'annaba':        {'lat': 36.90, 'lon': 7.76,  'name': 'Annaba'},
    'batna':         {'lat': 35.55, 'lon': 6.17,  'name': 'Batna'},
    'setif':         {'lat': 36.19, 'lon': 5.41,  'name': 'Sétif'},
    'tizi_ouzou':    {'lat': 36.71, 'lon': 4.04,  'name': 'Tizi Ouzou'},
    'bejaia':        {'lat': 36.75, 'lon': 5.06,  'name': 'Béjaïa'},
    'blida':         {'lat': 36.47, 'lon': 2.83,  'name': 'Blida'},
    'biskra':        {'lat': 34.85, 'lon': 5.73,  'name': 'Biskra'},
    'ouargla':       {'lat': 31.95, 'lon': 5.32,  'name': 'Ouargla'},
    'tlemcen':       {'lat': 34.88, 'lon': -1.32, 'name': 'Tlemcen'},
    'ghardaia':      {'lat': 32.49, 'lon': 3.67,  'name': 'Ghardaïa'},
    'skikda':        {'lat': 36.87, 'lon': 6.90,  'name': 'Skikda'},
    'tiaret':        {'lat': 35.37, 'lon': 1.32,  'name': 'Tiaret'},
    'saida':         {'lat': 34.83, 'lon': 0.15,  'name': 'Saïda'},
    'mostaganem':    {'lat': 35.93, 'lon': 0.09,  'name': 'Mostaganem'},
    'medea':         {'lat': 36.27, 'lon': 2.75,  'name': 'Médéa'},
    'msila':         {'lat': 35.70, 'lon': 4.54,  'name': "M'Sila"},
    'mascara':       {'lat': 35.40, 'lon': 0.14,  'name': 'Mascara'},
    'djelfa':        {'lat': 34.67, 'lon': 3.26,  'name': 'Djelfa'},
    'jijel':         {'lat': 36.82, 'lon': 5.77,  'name': 'Jijel'},
    'guelma':        {'lat': 36.46, 'lon': 7.43,  'name': 'Guelma'},
    'tipaza':        {'lat': 36.59, 'lon': 2.44,  'name': 'Tipaza'},
    'boumerdes':     {'lat': 36.76, 'lon': 3.48,  'name': 'Boumerdès'},
    'ain_defla':     {'lat': 36.26, 'lon': 1.97,  'name': 'Aïn Defla'},
    'relizane':      {'lat': 35.73, 'lon': 0.56,  'name': 'Relizane'},
    'mila':          {'lat': 36.45, 'lon': 6.26,  'name': 'Mila'},
    'tamanrasset':   {'lat': 22.78, 'lon': 5.52,  'name': 'Tamanrasset'},
    'adrar':         {'lat': 27.87, 'lon': -0.29, 'name': 'Adrar'},
    'bechar':        {'lat': 31.62, 'lon': -2.22, 'name': 'Béchar'},
    'tebessa':       {'lat': 35.40, 'lon': 8.12,  'name': 'Tébessa'},
    'naama':         {'lat': 33.27, 'lon': -0.31, 'name': 'Naâma'},
    'souk_ahras':    {'lat': 36.28, 'lon': 7.95,  'name': 'Souk Ahras'},
    'khenchela':     {'lat': 35.42, 'lon': 7.14,  'name': 'Khenchela'},
    'el_oued':       {'lat': 33.37, 'lon': 6.86,  'name': 'El Oued'},
    'el_tarf':       {'lat': 36.77, 'lon': 8.31,  'name': 'El Tarf'},
    'tissemsilt':    {'lat': 35.60, 'lon': 1.81,  'name': 'Tissemsilt'},
    'oum_el_bouaghi':{'lat': 35.87, 'lon': 7.11,  'name': 'Oum El Bouaghi'},
    'ain_temouchent':{'lat': 35.30, 'lon': -1.14, 'name': 'Aïn Témouchent'},
    'bordj_bou_arreridj': {'lat': 36.07, 'lon': 4.76, 'name': 'Bordj Bou Arréridj'},
    'sidi_bel_abbes':{'lat': 35.19, 'lon': -0.63, 'name': 'Sidi Bel Abbès'},
    'laghouat':      {'lat': 33.80, 'lon': 2.86,  'name': 'Laghouat'},
    'bouira':        {'lat': 36.37, 'lon': 3.90,  'name': 'Bouira'},
    'el_bayadh':     {'lat': 33.68, 'lon': 1.02,  'name': 'El Bayadh'},
    'illizi':        {'lat': 26.48, 'lon': 8.47,  'name': 'Illizi'},
    'tindouf':       {'lat': 27.67, 'lon': -8.15, 'name': 'Tindouf'},
}

# Only alert on genuinely important conditions — not every minor thing
def evaluate_alerts(weather: dict, wilaya_name: str) -> list:
    temp     = weather['temperature_2m']
    humidity = weather['relative_humidity_2m']
    wind     = weather['wind_speed_10m']
    precip   = weather['precipitation']
    code     = weather.get('weathercode', 0)

    alerts = []

    # Thunderstorm
    if code >= 95:
        alerts.append({
            'severity': 'danger',
            'title':    f'Thunderstorm warning — {wilaya_name}',
            'message':  f'Thunderstorms detected in {wilaya_name}. Secure equipment, stay indoors, do not work in fields. All irrigation and spraying must stop immediately.',
            'watering_ok': False,
            'planting_ok': False,
        })

    # Heavy rain / flooding risk
    elif precip > 15:
        alerts.append({
            'severity': 'danger',
            'title':    f'Heavy rainfall alert — {wilaya_name}',
            'message':  f'Heavy rain ({round(precip)}mm) in {wilaya_name}. Check drainage on all fields immediately to prevent waterlogging and root damage. Skip all irrigation today.',
            'watering_ok': False,
            'planting_ok': False,
        })

    elif precip > 5:
        alerts.append({
            'severity': 'info',
            'title':    f'Rain today in {wilaya_name} — skip irrigation',
            'message':  f'Rainfall of {round(precip)}mm expected in {wilaya_name}. No irrigation needed today. Good natural moisture for most crops.',
            'watering_ok': False,
            'planting_ok': True,
        })

    # Extreme heat
    if temp >= 40:
        alerts.append({
            'severity': 'danger',
            'title':    f'Extreme heat — {wilaya_name} {round(temp)}°C',
            'message':  f'Dangerous heat of {round(temp)}°C in {wilaya_name}. Water only before 7 AM or after 7 PM. Protect seedlings with shade cloth. Risk of crop dehydration and sunscald.',
            'watering_ok': False,
            'planting_ok': False,
        })
    elif temp >= 36:
        alerts.append({
            'severity': 'warning',
            'title':    f'High heat warning — {wilaya_name} {round(temp)}°C',
            'message':  f'Temperature reaching {round(temp)}°C in {wilaya_name}. Water early morning only. Increase irrigation frequency for tomatoes, peppers, and other fruiting crops.',
            'watering_ok': True,
            'planting_ok': False,
        })

    # Frost risk
    if temp <= 3:
        alerts.append({
            'severity': 'danger',
            'title':    f'Frost risk — {wilaya_name} {round(temp)}°C',
            'message':  f'Near-freezing temperature of {round(temp)}°C in {wilaya_name}. Cover sensitive crops immediately — tomatoes, peppers, cucumbers are at high risk. Do not water tonight.',
            'watering_ok': False,
            'planting_ok': False,
        })
    elif temp <= 6:
        alerts.append({
            'severity': 'warning',
            'title':    f'Cold alert — {wilaya_name} {round(temp)}°C',
            'message':  f'Cold temperatures of {round(temp)}°C expected in {wilaya_name}. Protect young seedlings. Reduce watering frequency — cold wet soil causes root rot.',
            'watering_ok': False,
            'planting_ok': False,
        })

    # High humidity — fungal disease risk
    if humidity >= 88 and temp >= 15:
        alerts.append({
            'severity': 'warning',
            'title':    f'Fungal disease risk — {wilaya_name}',
            'message':  f'Very high humidity ({round(humidity)}%) with warm temperatures in {wilaya_name}. Ideal conditions for mildew, blight, and botrytis. Inspect crops now and apply preventive fungicide.',
            'watering_ok': False,
            'planting_ok': False,
        })

    # Strong wind
    if wind >= 45:
        alerts.append({
            'severity': 'warning',
            'title':    f'Strong winds — {wilaya_name} {round(wind)} km/h',
            'message':  f'Strong winds of {round(wind)} km/h in {wilaya_name}. Postpone all spraying and foliar applications. Secure greenhouse covers and protective netting.',
            'watering_ok': False,
            'planting_ok': False,
        })

    # Perfect watering conditions — notify as good news too
    if (18 <= temp <= 28 and humidity <= 60
            and wind <= 15 and precip == 0 and code < 3):
        alerts.append({
            'severity': 'good',
            'title':    f'Perfect watering conditions — {wilaya_name}',
            'message':  f'Ideal conditions today in {wilaya_name}: {round(temp)}°C, {round(humidity)}% humidity, calm winds. Best time for morning irrigation and foliar treatments.',
            'watering_ok': True,
            'planting_ok': True,
        })

    return alerts


def get_farmers_by_wilaya() -> dict:
    """Fetch all farmers grouped by wilaya from Auth Service."""
    try:
        # Try admin login to get farmer list
        login = requests.post(
            'http://auth-service:8001/api/auth/login/',
            json={'email': 'admin@agriguard.dz', 'password': 'AdminPass123!'},
            timeout=5,
        )
        if not login.ok:
            return {}

        token = login.json().get('access', '')
        users = requests.get(
            'http://auth-service:8001/api/auth/admin/users/',
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        if not users.ok:
            return {}

        grouped = {}
        for user in users.json():
            wilaya = user.get('wilaya', '').lower()
            if wilaya and user.get('is_active'):
                grouped.setdefault(wilaya, []).append(user['id'])
        return grouped

    except Exception as e:
        logger.warning(f"Could not fetch farmers from Auth Service: {e}")
        return {}


class Command(BaseCommand):
    help = 'Check weather for all active farmer wilayas and push important alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            action='store_true',
            help='Run continuously every 3 hours',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=180,
            help='Check interval in minutes (default: 180)',
        )

    def handle(self, *args, **options):
        # Wait for RabbitMQ to be fully ready
        #time.sleep(10)
        # Retry connecting to RabbitMQ up to 10 times
        params = pika.URLParameters(settings.RABBITMQ_URL)
        connection = None
        for attempt in range(10):
            try:
                connection = pika.BlockingConnection(params)
                self.stdout.write(self.style.SUCCESS('Connected to RabbitMQ'))
                break
            except Exception as e:
                self.stdout.write(f'RabbitMQ not ready (attempt {attempt+1}/10) — retrying in 5s...')
                time.sleep(5)

        if not connection:
            self.stdout.write(self.style.ERROR('Could not connect to RabbitMQ after 10 attempts'))
            return

        channel = connection.channel()
        channel.exchange_declare(
            exchange='agriguard',
            exchange_type='topic',
            durable=True,
        )

        self.stdout.write(self.style.SUCCESS('Weather scheduler started'))
        self._run_check(channel)

        if options['loop']:
            interval_seconds = options['interval'] * 60
            self.stdout.write(
                self.style.SUCCESS(
                    f'Loop mode — checking every {options["interval"]} minutes'
                )
            )
            while True:
                time.sleep(interval_seconds)
                try:
                    if connection.is_closed:
                        connection = pika.BlockingConnection(params)
                        channel = connection.channel()
                        channel.exchange_declare(
                            exchange='agriguard',
                            exchange_type='topic',
                            durable=True,
                        )
                    self._run_check(channel)
                except Exception as e:
                    logger.error(f'Error in weather loop: {e}')

    def _run_check(self, channel):
        self.stdout.write(f'Running weather check…')
        farmers_by_wilaya = get_farmers_by_wilaya()

        if not farmers_by_wilaya:
            self.stdout.write(
                self.style.WARNING('No farmers found — skipping alert targeting')
            )
            return

        total_alerts = 0

        for wilaya_key, farmer_ids in farmers_by_wilaya.items():
            coords = WILAYA_COORDS.get(wilaya_key)
            if not coords:
                continue

            try:
                res = requests.get(OPEN_METEO_URL, params={
                    'latitude':  coords['lat'],
                    'longitude': coords['lon'],
                    'current':   'temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weathercode',
                    'timezone':  'Africa/Algiers',
                }, timeout=10)
                res.raise_for_status()
                weather = res.json()['current']

                alerts = evaluate_alerts(weather, coords['name'])

                for alert in alerts:
                    for farmer_id in farmer_ids:
                        payload = json.dumps({
                            'farmer_id':   str(farmer_id),
                            'wilaya':      wilaya_key,
                            'severity':    alert['severity'],
                            'title':       alert['title'],
                            'message':     alert['message'],
                            'watering_ok': alert['watering_ok'],
                            'planting_ok': alert['planting_ok'],
                        })
                        channel.basic_publish(
                            exchange='agriguard',
                            routing_key='weather.alert',
                            body=payload,
                            properties=pika.BasicProperties(delivery_mode=2),
                        )
                        total_alerts += 1

                time.sleep(0.5)  # be nice to the free API

            except Exception as e:
                logger.error(f"Failed weather check for {wilaya_key}: {e}")

        self.stdout.write(
            self.style.SUCCESS(f'Done — {total_alerts} alerts published')
        )