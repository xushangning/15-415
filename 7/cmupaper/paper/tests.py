"""Design Choices:
1. No test for `reset_db`. The code of `reset_db` is handed down as a definition
for database schema that shouldn't be change. What's the point of testing
something that can't fail, because it itself is the definition of correctness?
"""
from django.test import TestCase

# Create your tests here.
