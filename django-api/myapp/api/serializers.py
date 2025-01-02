from rest_framework import serializers
from .models import Issue

# Serializer to convert Issue model data to JSON
class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = '__all__'  # Include all fields in the response
