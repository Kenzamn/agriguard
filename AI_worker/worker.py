import json
import logging
import os
import time
import pika
import requests
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
import timm

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)

RABBITMQ_URL   = os.environ.get("RABBITMQ_URL",   "amqp://guest:guest@localhost:5672/")
DIAGNOSIS_HOST = os.environ.get("DIAGNOSIS_HOST", "http://localhost:8003")
MODEL_PATH     = os.environ.get("MODEL_PATH",     "./best_model.pth")
MEDIA_ROOT     = os.environ.get("MEDIA_ROOT",     "./media")
DEVICE         = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CLASS_NAMES = [
    "Apple_Apple_scab", "Apple_Black_rot", "Apple_Cedar_apple_rust", "Apple_healthy",
    "Cherry_(including_sour)_Powdery_mildew", "Cherry_(including_sour)_healthy",
    "Corn_(maize)_Cercospora_leaf_spot Gray_leaf_spot", "Corn_(maize)_Common_rust_",
    "Corn_(maize)_Northern_Leaf_Blight", "Corn_(maize)_healthy",
    "Grape_Black_rot", "Grape_Esca_(Black_Measles)", "Grape_Leaf_blight_(Isariopsis_Leaf_Spot)",
    "Grape_healthy", "Orange_Haunglongbing_(Citrus_greening)",
    "Peach_Bacterial_spot", "Peach_healthy",
    "Pepper,_bell_Bacterial_spot", "Pepper,_bell_healthy",
    "Potato_Early_blight", "Potato_Late_blight", "Potato_healthy",
    "Squash_Powdery_mildew",
    "Strawberry_Leaf_scorch", "Strawberry_healthy",
    "Tomato_Bacterial_spot", "Tomato_Early_blight", "Tomato_Late_blight",
    "Tomato_Leaf_Mold", "Tomato_Septoria_leaf_spot",
    "Tomato_Spider_mites Two-spotted_spider_mite", "Tomato_Target_Spot",
    "Tomato_Tomato_Yellow_Leaf_Curl_Virus", "Tomato_Tomato_mosaic_virus",
    "Tomato_healthy",
]
NUM_CLASSES    = len(CLASS_NAMES)
HEALTHY_CLASSES = {name for name in CLASS_NAMES if name.endswith("_healthy")}

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def load_model():
    logger.info(f"Loading model from {MODEL_PATH} on {DEVICE}...")
    model = timm.create_model("vit_base_patch16_224", pretrained=False)
    model.head = nn.Linear(model.head.in_features, NUM_CLASSES)
    state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.eval()
    model.to(DEVICE)
    logger.info("Model loaded successfully.")
    return model

def load_image(image_path):
    full_path = os.path.join(MEDIA_ROOT, image_path)
    logger.info(f"Loading image from: {full_path}")
    image = Image.open(full_path).convert("RGB")
    return TRANSFORM(image).unsqueeze(0).to(DEVICE)

@torch.no_grad()
def predict(model, image_tensor):
    outputs = model(image_tensor)
    probs = torch.softmax(outputs, dim=1)
    confidence, pred_idx = probs.max(dim=1)
    class_name = CLASS_NAMES[pred_idx.item()]
    confidence_score = confidence.item()
    is_healthy = class_name in HEALTHY_CLASSES
    logger.info(f"Prediction: {class_name} ({confidence_score*100:.1f}%)")
    return class_name, confidence_score, is_healthy

def publish_result(channel, diagnosis_id, field_id, farmer_id, disease_name, confidence_score, is_healthy):
    payload = json.dumps({
        "diagnosis_id": diagnosis_id,
        "field_id": field_id,
        "farmer_id": farmer_id,
        "disease_name": disease_name,
        "confidence_score": confidence_score,
        "is_healthy": is_healthy,
    })
    channel.basic_publish(
        exchange="agriguard",
        routing_key="diagnosis.done",
        body=payload,
        properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
    )
    logger.info(f"Published diagnosis.done for {diagnosis_id}")

def update_diagnosis(diagnosis_id, disease_name, confidence_score, is_healthy):
    url = f"{DIAGNOSIS_HOST}/api/diagnosis/internal/results/"
    try:
        resp = requests.post(url, json={
            "diagnosis_id": diagnosis_id,
            "disease_name": disease_name,
            "confidence_score": confidence_score,
            "is_healthy": is_healthy,
        }, timeout=10)
        if resp.status_code in (200, 201):
            logger.info(f"Diagnosis {diagnosis_id} updated to completed.")
        else:
            logger.error(f"Failed to update diagnosis {diagnosis_id}: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"HTTP error updating diagnosis {diagnosis_id}: {e}")

def on_message(channel, method, properties, body, model):
    try:
        event = json.loads(body)
        diagnosis_id = event["diagnosis_id"]
        image_path   = event["image_path"]
        field_id     = event["field_id"]
        farmer_id    = event["farmer_id"]
        logger.info(f"Processing diagnosis {diagnosis_id}...")
        image_tensor = load_image(image_path)
        disease_name, confidence_score, is_healthy = predict(model, image_tensor)
        update_diagnosis(diagnosis_id, disease_name, confidence_score, is_healthy)
        publish_result(channel, diagnosis_id, field_id, farmer_id, disease_name, confidence_score, is_healthy)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Diagnosis {diagnosis_id} done: {disease_name} ({confidence_score*100:.1f}%)")
    except Exception as e:
        logger.error(f"Failed to process message: {e}", exc_info=True)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def main():
    model = load_model()
    params = pika.URLParameters(RABBITMQ_URL)
    connection = None
    for attempt in range(20):
        try:
            connection = pika.BlockingConnection(params)
            logger.info("Connected to RabbitMQ.")
            break
        except Exception as e:
            logger.warning(f"RabbitMQ not ready ({attempt+1}/20): {e} — retrying in 5s")
            time.sleep(5)
    if not connection:
        logger.error("Could not connect to RabbitMQ. Exiting.")
        return
    channel = connection.channel()
    channel.exchange_declare(exchange="agriguard", exchange_type="topic", durable=True)
    channel.queue_declare(queue="ai.diagnosis", durable=True)
    channel.queue_bind(exchange="agriguard", queue="ai.diagnosis", routing_key="diagnosis.requested")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(
        queue="ai.diagnosis",
        on_message_callback=lambda ch, method, props, body: on_message(ch, method, props, body, model),
    )
    logger.info("AI Worker started — waiting for diagnosis.requested jobs...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        channel.stop_consuming()
        connection.close()

if __name__ == "__main__":
    main()