import json
import logging
import time
import pika
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


def handle_diagnosis_done(event: dict):
    from notifications.models import Notification
    farmer_id  = event.get('farmer_id')
    is_healthy = event.get('is_healthy', True)
    disease    = event.get('disease_name', 'Unknown')
    confidence = event.get('confidence_score', 0.0)

    if not farmer_id:
        logger.warning('diagnosis.done event missing farmer_id — skipping')
        return

    if is_healthy:
        Notification.objects.create(
            user_id = farmer_id,
            type    = 'diagnosis_done',
            title   = '✅ Crop looks healthy',
            message = (
                f'No disease detected (confidence: {round(confidence * 100)}%). '
                f'Your crop is in good condition. Keep up the good work!'
            ),
        )
    else:
        Notification.objects.create(
            user_id = farmer_id,
            type    = 'disease_alert',
            title   = f'🦠 Disease detected — {disease}',
            message = (
                f'{disease} detected with {round(confidence * 100)}% confidence. '
                f'Immediate action recommended. Consult an agronomist as soon as possible.'
            ),
        )


def handle_weather_alert(event: dict):
    """
    severity='danger'  → type='disease_alert'  (red in UI — most urgent)
    severity='warning' → type='weather_alert'   (amber in UI)
    Only warning/danger are ever published by the weather-scheduler.
    """
    from notifications.models import Notification

    farmer_id = event.get('farmer_id')
    if not farmer_id:
        logger.warning('weather.alert event missing farmer_id — skipping')
        return

    severity   = event.get('severity', 'warning')
    title      = event.get('title',    'Weather alert')
    message    = event.get('message',  '')
    notif_type = 'disease_alert' if severity == 'danger' else 'weather_alert'

    Notification.objects.create(
        user_id = farmer_id,
        type    = notif_type,
        title   = title,
        message = message,
    )
    logger.info(
        f'Weather notification created for farmer {farmer_id} '
        f'[{severity}]: {title}'
    )


def on_message(ch, method, properties, body):
    from notifications.models import NotificationLog

    raw = body.decode('utf-8')

    try:
        event       = json.loads(raw)
        routing_key = method.routing_key
        logger.info(f'Received [{routing_key}]: {event}')

        if routing_key == 'diagnosis.done':
            handle_diagnosis_done(event)
        elif routing_key == 'weather.alert':
            handle_weather_alert(event)
        else:
            logger.warning(f'Unknown routing key: {routing_key}')

        NotificationLog.objects.create(
            event_type = routing_key,
            payload    = event,
            success    = True,
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f'Failed to process message: {e}')
        try:
            from notifications.models import NotificationLog
            NotificationLog.objects.create(
                event_type = method.routing_key,
                payload    = {'raw': raw},
                success    = False,
                error      = str(e),
            )
        except Exception:
            pass
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def connect_with_retry(rabbitmq_url: str, max_attempts: int = 20, delay: int = 5):
    """
    Try to connect to RabbitMQ, retrying with a fixed delay.
    Raises RuntimeError if all attempts fail.
    """
    params = pika.URLParameters(rabbitmq_url)
    for attempt in range(1, max_attempts + 1):
        try:
            connection = pika.BlockingConnection(params)
            logger.info(f'Connected to RabbitMQ on attempt {attempt}')
            return connection
        except Exception as e:
            logger.warning(
                f'RabbitMQ not ready (attempt {attempt}/{max_attempts}): {e} '
                f'— retrying in {delay}s'
            )
            time.sleep(delay)
    raise RuntimeError(
        f'Could not connect to RabbitMQ after {max_attempts} attempts'
    )


class Command(BaseCommand):
    help = 'Listen to RabbitMQ and create notifications'

    def handle(self, *args, **kwargs):
        rabbitmq_url = settings.RABBITMQ_URL

        # Retry connecting — RabbitMQ may not be ready when this container starts
        try:
            connection = connect_with_retry(rabbitmq_url)
        except RuntimeError as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        channel = connection.channel()
        channel.exchange_declare(
            exchange='agriguard', exchange_type='topic', durable=True
        )
        channel.queue_declare(queue='notification.events', durable=True)
        channel.queue_bind(
            exchange='agriguard',
            queue='notification.events',
            routing_key='diagnosis.done',
        )
        channel.queue_bind(
            exchange='agriguard',
            queue='notification.events',
            routing_key='weather.alert',
        )

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue='notification.events',
            on_message_callback=on_message,
        )

        self.stdout.write(self.style.SUCCESS(
            'Notification consumer started — '
            'listening for diagnosis.done and weather.alert…'
        ))
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            connection.close()