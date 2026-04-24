import json
import logging
import pika
from django.conf import settings

logger = logging.getLogger(__name__)


def get_channel():
    params     = pika.URLParameters(settings.RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel    = connection.channel()
    channel.exchange_declare(
        exchange='agriguard',
        exchange_type='topic',
        durable=True,
    )
    return connection, channel


def publish_diagnosis_job(diagnosis_id: str, image_path: str, field_id: str, farmer_id: str):
    """
    Publish a job to RabbitMQ so the AI Worker picks it up.
    Routing key: diagnosis.requested
    """
    connection, channel = get_channel()
    try:
        payload = json.dumps({
            'diagnosis_id': str(diagnosis_id),
            'image_path':   image_path,
            'field_id':     str(field_id),
            'farmer_id':    str(farmer_id),
        })
        channel.basic_publish(
            exchange='agriguard',
            routing_key='diagnosis.requested',
            body=payload,
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent — survives broker restart
                content_type='application/json',
            ),
        )
        logger.info(f"Published diagnosis.requested for diagnosis {diagnosis_id}")
    finally:
        connection.close()