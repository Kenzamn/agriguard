from django.shortcuts import render

# Create your views here.
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Diagnosis, DiagnosisResult
from .serializers import DiagnosisSerializer, DiagnosisCreateSerializer
from .auth import JWTAuthentication
from .storage import save_diagnosis_image
from .publisher import publish_diagnosis_job

logger = logging.getLogger(__name__)

class DiagnosisListCreateView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """List all diagnoses for the authenticated farmer."""
        diagnoses = Diagnosis.objects.filter(
            farmer_id=request.user.id
        ).order_by('-created_at').select_related('result')
        return Response(DiagnosisSerializer(diagnoses, many=True).data)

    def post(self, request):
        """Upload a crop image and create a pending diagnosis."""
        if request.user.role != 'farmer':
            return Response({'detail': 'Only farmers can submit diagnoses.'},
                            status=status.HTTP_403_FORBIDDEN)
        
        serializer = DiagnosisCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        field_id  = serializer.validated_data['field_id']
        image     = serializer.validated_data['image']

        # Save the image and get its path
        try:
            image_path = save_diagnosis_image(image, request.user.id)
        except Exception as e:
            logger.error(f"Image save failed: {e}")
            return Response({'detail': 'Failed to save image.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create diagnosis record with status=pending
        diagnosis = Diagnosis.objects.create(
            field_id   = field_id,
            farmer_id  = request.user.id,
            image_path = image_path,
            status     = 'pending',
        )

        # Publish job to RabbitMQ for AI Worker
        try:
            publish_diagnosis_job(
                diagnosis_id = diagnosis.id,
                image_path   = image_path,
                field_id     = field_id,
                farmer_id    = request.user.id,
            )
            diagnosis.status = 'processing'
            diagnosis.save(update_fields=['status'])
        except Exception as e:
            logger.error(f"RabbitMQ publish failed: {e}")
            # Don't block the farmer — job stays pending, can be retried
            pass

        return Response(DiagnosisSerializer(diagnosis).data,
                        status=status.HTTP_201_CREATED)
    
class DiagnosisDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, pk):
        """Get a single diagnosis with its result (if completed)."""
        diagnosis = get_object_or_404(
            Diagnosis.objects.select_related('result'),
            pk=pk,
            farmer_id=request.user.id,
        )
        return Response(DiagnosisSerializer(diagnosis).data)
    
class AdminDiagnosisListView(APIView):
    """Admin only — all diagnoses across all farmers."""
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Only admins can access this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        diagnoses = Diagnosis.objects.all().order_by('-created_at').select_related('result')
        return Response(DiagnosisSerializer(diagnoses, many=True).data)
    
from rest_framework.permissions import AllowAny

class InternalResultView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        diagnosis_id     = request.data.get("diagnosis_id")
        disease_name     = request.data.get("disease_name")
        confidence_score = request.data.get("confidence_score")
        is_healthy       = request.data.get("is_healthy")

        diagnosis = get_object_or_404(Diagnosis, pk=diagnosis_id)
        DiagnosisResult.objects.create(
            diagnosis        = diagnosis,
            disease_name     = disease_name,
            confidence_score = confidence_score,
            is_healthy       = is_healthy,
        )
        diagnosis.status = "completed"
        diagnosis.save(update_fields=["status"])
        return Response({"detail": "ok"}, status=status.HTTP_201_CREATED)    