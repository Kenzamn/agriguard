import os
import uuid
from django.conf import settings


def save_diagnosis_image(image_file, farmer_id: str) -> str:
    """
    Save uploaded image to MEDIA_ROOT/diagnoses/<farmer_id>/<uuid>.<ext>
    Returns the relative path stored in the DB.
    """

    ext = os.path.splitext(image_file.name)[1].lower() # get file extension (e.g. .jpg)
    filename = f"{uuid.uuid4()}{ext}" # generate unique filename
    rel_dir = os.path.join('diagnoses', str(farmer_id)) # e.g. diagnoses/123e4567-e89b-12d3-a456-426614174000
    abs_dir  = os.path.join(settings.MEDIA_ROOT, rel_dir) # absolute path to the farmer's diagnosis folder

    os.makedirs(abs_dir, exist_ok=True) 

    abs_path = os.path.join(abs_dir, filename) # absolute path to the saved image
    with open(abs_path, 'wb+') as dest:
        for chunk in image_file.chunks():
            dest.write(chunk)

    return os.path.join(rel_dir, filename) # return the relative path to store in DB e.g. diagnoses/uuid/uuid.jpg
