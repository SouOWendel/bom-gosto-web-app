from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from estoque.serializers import EstoqueSerializer
from .serializers import RegistrarProducaoSerializer


class RegistrarProducaoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = RegistrarProducaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lote = serializer.save()

        return Response(
            EstoqueSerializer(lote).data,
            status=status.HTTP_201_CREATED,
        )