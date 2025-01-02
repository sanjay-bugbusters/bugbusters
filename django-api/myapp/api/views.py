from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import IssueSerializer

# API to handle issue creation and send a custom response
class IssueCreateView(APIView):
    def post(self, request):
        # Serialize the incoming data
        serializer = IssueSerializer(data=request.data)
        if serializer.is_valid():
            # Save the issue to the database
            serializer.save()
            # Return a custom response
            return Response(
                {"message": "Welcome! You got a response from the API."}, 
                status=status.HTTP_201_CREATED
            )
        # If data is invalid, return an error response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
