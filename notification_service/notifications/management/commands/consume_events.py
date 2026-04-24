import json
import logging
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
        return

    if is_healthy:
        Notification.objects.create(
            user_id = farmer_id,
            type    = 'diagnosis_done',
            title   = 'Crop looks healthy',
            message = f'No disease detected (confidence: {round(confidence * 100)}%). Keep up the good work!',
        )
    else:
        Notification.objects.create(
            user_id = farmer_id,
            type    = 'disease_alert',
            title   = f'Disease detected — {disease}',
            message = (
                f'{disease} detected with {round(confidence * 100)}% confidence. '
                f'Immediate action recommended. Consult an agronomist.'
            ),
        )


def handle_weather_alert(event: dict):
    from notifications.models import Notification
    farmer_id = event.get('farmer_id')
    if not farmer_id:
        return

    # Only create notifications for genuinely important conditions
    severity = event.get('severity', 'info')
    if severity == 'good':
        notif_type = 'weather_alert'
    elif severity in ('warning', 'danger'):
        notif_type = 'weather_alert'
    else:
        notif_type = 'weather_alert'

    Notification.objects.create(
        user_id = farmer_id,
        type    = notif_type,
        title   = event.get('title', 'Weather alert'),
        message = event.get('message', ''),
    )
    logger.info(f"Weather notification created for farmer {farmer_id}: {event.get('title')}")


def on_message(ch, method, properties, body):
    from notifications.models import NotificationLog
    raw = body.decode('utf-8')

    try:
        event        = json.loads(raw)
        routing_key  = method.routing_key
        logger.info(f"Received [{routing_key}]: {event}")

        if routing_key == 'diagnosis.done':
            handle_diagnosis_done(event)
        elif routing_key == 'weather.alert':
            handle_weather_alert(event)
        else:
            logger.warning(f"Unknown routing key: {routing_key}")

        NotificationLog.objects.create(
            event_type = routing_key,
            payload    = event,
            success    = True,
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Failed to process message: {e}")
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


class Command(BaseCommand):
    help = 'Listen to RabbitMQ and create notifications'

    def handle(self, *args, **kwargs):
        params     = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel    = connection.channel()

        channel.exchange_declare(exchange='agriguard', exchange_type='topic', durable=True)
        channel.queue_declare(queue='notification.events', durable=True)
        channel.queue_bind(exchange='agriguard', queue='notification.events', routing_key='diagnosis.done')
        channel.queue_bind(exchange='agriguard', queue='notification.events', routing_key='weather.alert')

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='notification.events', on_message_callback=on_message)

        self.stdout.write(self.style.SUCCESS(
            'Notification consumer started — listening for diagnosis.done and weather.alert…'
        ))
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            connection.close()