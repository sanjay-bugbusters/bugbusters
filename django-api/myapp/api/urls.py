from django.urls import path
from .views import IssueCreateView

urlpatterns = [
    path('issue/', IssueCreateView.as_view(), name='issue-create'),  # Route to submit issues
]
