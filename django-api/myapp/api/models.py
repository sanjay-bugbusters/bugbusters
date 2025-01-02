from django.db import models

# Create your models here.
# Model to store a bug or issue text
class Issue(models.Model):
    text = models.TextField()  # The bug or issue text entered by the user

    def __str__(self):
        return self.text[:50]  # Show the first 50 characters for readability