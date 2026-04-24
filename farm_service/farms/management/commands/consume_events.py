import json
import logging
import pika
from django.core.management.base import BaseCommand
from django.conf import settings
from farms.models import Field

logger = logging.getLogger(__name__)


def map_disease_to_status(is_healthy: bool, confidence_score: float) -> str:
    """Decide field status from AI result."""
    if is_healthy:
        return 'healthy'
    if confidence_score >= 0.75:
        return 'disease'
    return 'warning'


def handle_diagnosis_done(ch, method, properties, body):
    """Callback fired for every diagnosis.done message."""
    try:
        event = json.loads(body)
        logger.info(f"Received diagnosis.done: {event}")

        field_id      = event.get('field_id')
        is_healthy    = event.get('is_healthy', True)
        confidence    = event.get('confidence_score', 0.0)

        if not field_id:
            logger.warning("diagnosis.done event missing field_id — skipping.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        new_status = map_disease_to_status(is_healthy, confidence)

        updated = Field.objects.filter(id=field_id).update(status=new_status)
        if updated:
            logger.info(f"Field {field_id} status updated to '{new_status}'")
        else:
            logger.warning(f"Field {field_id} not found — no update performed.")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Failed to process diagnosis.done: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


class Command(BaseCommand):
    help = 'Listen to RabbitMQ and update field status on diagnosis.done events'

    def handle(self, *args, **kwargs):
        params = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        # Declare the same exchange the AI Worker publishes to
        channel.exchange_declare(
            exchange='agriguard',
            exchange_type='topic',
            durable=True,
        )

        # Exclusive queue for farm service
        queue = channel.queue_declare(queue='farm.field_status', durable=True)
        channel.queue_bind(
            exchange='agriguard',
            queue='farm.field_status',
            routing_key='diagnosis.done',
        )

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue='farm.field_status',
            on_message_callback=handle_diagnosis_done,
        )

        self.stdout.write(self.style.SUCCESS(
            'Farm Service consumer started — waiting for diagnosis.done events...'
        ))
        channel.start_consuming()