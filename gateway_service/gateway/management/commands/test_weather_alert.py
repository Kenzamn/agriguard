"""
Test command: inject fake weather alerts per wilaya.

Each farmer only receives an alert for THEIR OWN wilaya — same behaviour
as the real weather_alerts command, but with fabricated weather data
so you don't have to wait for extreme conditions.

Usage:
    # Test all wilayas that have active farmers (one alert per wilaya)
    docker exec agriguard-weather-scheduler python manage.py test_weather_alert

    # Test a specific wilaya only
    docker exec agriguard-weather-scheduler python manage.py test_weather_alert --wilaya oran

    # Test with danger severity
    docker exec agriguard-weather-scheduler python manage.py test_weather_alert --severity danger

    # Target one specific farmer UUID (skips the wilaya grouping entirely)
    docker exec agriguard-weather-scheduler python manage.py test_weather_alert --farmer-id <uuid>

Verify results:
    docker exec agriguard-notification python manage.py shell -c \
      "from notifications.models import Notification; \
       [print(n.user_id, '|', n.title) for n in Notification.objects.order_by('-created_at')[:10]]"
"""

import json
import pika
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

# Wilaya display names — same mapping used in weather_alerts.py
WILAYA_NAMES = {
    'alger': 'Alger', 'oran': 'Oran', 'constantine': 'Constantine',
    'annaba': 'Annaba', 'batna': 'Batna', 'setif': 'Sétif',
    'tizi_ouzou': 'Tizi Ouzou', 'bejaia': 'Béjaïa', 'blida': 'Blida',
    'biskra': 'Biskra', 'ouargla': 'Ouargla', 'tlemcen': 'Tlemcen',
    'ghardaia': 'Ghardaïa', 'skikda': 'Skikda', 'tiaret': 'Tiaret',
    'saida': 'Saïda', 'mostaganem': 'Mostaganem', 'medea': 'Médéa',
    'msila': "M'Sila", 'mascara': 'Mascara', 'djelfa': 'Djelfa',
    'jijel': 'Jijel', 'guelma': 'Guelma', 'tipaza': 'Tipaza',
    'boumerdes': 'Boumerdès', 'ain_defla': 'Aïn Defla',
    'relizane': 'Relizane', 'mila': 'Mila', 'tamanrasset': 'Tamanrasset',
    'adrar': 'Adrar', 'bechar': 'Béchar', 'tebessa': 'Tébessa',
    'naama': 'Naâma', 'souk_ahras': 'Souk Ahras', 'khenchela': 'Khenchela',
    'el_oued': 'El Oued', 'el_tarf': 'El Tarf', 'tissemsilt': 'Tissemsilt',
    'oum_el_bouaghi': 'Oum El Bouaghi', 'ain_temouchent': 'Aïn Témouchent',
    'bordj_bou_arreridj': 'Bordj Bou Arréridj', 'sidi_bel_abbes': 'Sidi Bel Abbès',
    'laghouat': 'Laghouat', 'bouira': 'Bouira', 'el_bayadh': 'El Bayadh',
    'illizi': 'Illizi', 'tindouf': 'Tindouf',
}


def build_alert(severity: str, wilaya_name: str) -> dict:
    """Build a test alert payload for the given wilaya and severity."""
    if severity == 'danger':
        return {
            'severity': 'danger',
            'title':    f'⛈️ TEST — Thunderstorm warning — {wilaya_name}',
            'message':  (
                f'[TEST ALERT for {wilaya_name}] '
                f'This is a pipeline test. In a real alert, thunderstorms '
                f'would be detected in {wilaya_name}. '
                f'Secure equipment, stay indoors, stop all irrigation.'
            ),
        }
    else:
        return {
            'severity': 'warning',
            'title':    f'🌡️ TEST — Heat warning — {wilaya_name}',
            'message':  (
                f'[TEST ALERT for {wilaya_name}] '
                f'This is a pipeline test. In a real alert, high temperatures '
                f'would be detected in {wilaya_name}. '
                f'Water crops only before 7 AM or after 7 PM.'
            ),
        }


def get_farmers_by_wilaya(secret: str) -> dict:
    """
    Fetch { 'alger': ['uuid1', 'uuid2'], 'oran': ['uuid3'], ... }
    from the auth service internal endpoint.
    """
    try:
        resp = requests.get(
            'http://agriguard-auth:8001/api/auth/internal/farmers-by-wilaya/',
            headers={'X-Internal-Secret': secret},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return {'error': resp.status_code, 'body': resp.text}
    except Exception as e:
        return {'exception': str(e)}


class Command(BaseCommand):
    help = (
        'Inject test weather alerts into RabbitMQ — '
        'each farmer receives an alert for their OWN wilaya only'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--severity',
            choices=['warning', 'danger'],
            default='warning',
            help='Alert severity (default: warning)',
        )
        parser.add_argument(
            '--wilaya',
            type=str,
            default=None,
            help='Only test this specific wilaya (e.g. --wilaya oran). '
                 'Default: test all wilayas that have active farmers.',
        )
        parser.add_argument(
            '--farmer-id',
            type=str,
            default=None,
            help='Send directly to one farmer UUID, using --wilaya for the '
                 'alert location (requires --wilaya too).',
        )

    def handle(self, *args, **options):
        severity       = options['severity']
        filter_wilaya  = options.get('wilaya')
        single_farmer  = options.get('farmer_id')

        # ── Build the farmers-by-wilaya map ───────────────────────────────
        if single_farmer:
            # Direct mode: one farmer, one wilaya
            if not filter_wilaya:
                self.stdout.write(self.style.ERROR(
                    '--farmer-id requires --wilaya so we know which '
                    'wilaya name to put in the alert.\n'
                    'Example: --farmer-id <uuid> --wilaya oran'
                ))
                return
            farmers_by_wilaya = {filter_wilaya: [single_farmer]}

        else:
            # Fetch from auth service
            secret = getattr(settings, 'INTERNAL_API_SECRET', '')
            if not secret:
                self.stdout.write(self.style.ERROR(
                    'INTERNAL_API_SECRET is not set. '
                    'Add it to your .env file or use --farmer-id <uuid> --wilaya <wilaya>.'
                ))
                return

            result = get_farmers_by_wilaya(secret)

            if 'error' in result or 'exception' in result:
                self.stdout.write(self.style.ERROR(
                    f'Could not fetch farmers: {result}\n'
                    f'Use --farmer-id <uuid> --wilaya <wilaya> instead.'
                ))
                return

            farmers_by_wilaya = result

            if filter_wilaya:
                # Narrow down to one wilaya
                if filter_wilaya not in farmers_by_wilaya:
                    self.stdout.write(self.style.WARNING(
                        f'No active farmers found in wilaya "{filter_wilaya}". '
                        f'Available wilayas: {list(farmers_by_wilaya.keys())}'
                    ))
                    return
                farmers_by_wilaya = {filter_wilaya: farmers_by_wilaya[filter_wilaya]}

        if not farmers_by_wilaya:
            self.stdout.write(self.style.WARNING(
                'No active farmers found at all. '
                'Register at least one farmer account first.'
            ))
            return

        # ── Connect to RabbitMQ ───────────────────────────────────────────
        try:
            params     = pika.URLParameters(settings.RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel    = connection.channel()
            channel.exchange_declare(
                exchange='agriguard', exchange_type='topic', durable=True
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'RabbitMQ connection failed: {e}'))
            return

        # ── Publish one alert per wilaya, to each farmer in that wilaya ───
        total = 0
        for wilaya_key, farmer_ids in farmers_by_wilaya.items():
            wilaya_name = WILAYA_NAMES.get(wilaya_key, wilaya_key.replace('_', ' ').title())
            alert       = build_alert(severity, wilaya_name)

            for fid in farmer_ids:
                payload = json.dumps({
                    'farmer_id': str(fid),
                    'wilaya':    wilaya_key,    # ← their actual wilaya
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
                total += 1

            self.stdout.write(
                f'  {wilaya_key} ({wilaya_name}): '
                f'{len(farmer_ids)} farmer(s) → [{severity}] {alert["title"]}'
            )

        connection.close()

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Published {total} test alert(s).\n'
            f'\n'
            f'Verify in DB (run in a new terminal):\n'
            f'  docker exec agriguard-notification python manage.py shell -c \\\n'
            f'    "from notifications.models import Notification; \\\n'
            f'     [print(str(n.user_id)[:8], \'|\', n.title) \\\n'
            f'      for n in Notification.objects.order_by(\'-created_at\')[:10]]"'
        ))