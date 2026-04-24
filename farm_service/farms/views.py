from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Field
from .serializers import FieldSerializer
from .auth import JWTAuthentication, IsFarmer


class FieldListCreateView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        """List all fields belonging to the authenticated farmer."""
        fields = Field.objects.filter(owner_id=request.user.id)
        serializer = FieldSerializer(fields, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new field for the authenticated farmer."""
        if not IsFarmer.check(request):
            return Response({'detail': 'Only farmers can create fields.'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = FieldSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner_id=request.user.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FieldDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    def get_object(self, pk, owner_id):
        return get_object_or_404(Field, pk=pk, owner_id=owner_id)

    def get(self, request, pk):
        field = self.get_object(pk, request.user.id)
        return Response(FieldSerializer(field).data)

    def put(self, request, pk):
        field = self.get_object(pk, request.user.id)
        serializer = FieldSerializer(field, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        field = self.get_object(pk, request.user.id)
        serializer = FieldSerializer(field, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        field = self.get_object(pk, request.user.id)
        field.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminFieldListView(APIView):
    """Admin only — see all fields across all farmers."""
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Admin only.'}, status=status.HTTP_403_FORBIDDEN)
        fields = Field.objects.all()
        return Response(FieldSerializer(fields, many=True).data)