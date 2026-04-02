# Standard library imports
from datetime import timedelta

# Third party imports
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

# Local folder imports
from .models import Event


class EventModelTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(title="Test Event", description="Test Description", start_date=timezone.now() + timedelta(days=1), frequency='weekly')

    def test_event_str(self):
        self.assertEqual(str(self.event), "Test Event")

    def test_get_absolute_url(self):
        url = self.event.get_absolute_url()
        self.assertEqual(url, f'/events/{self.event.pk}/')

    def test_is_upcoming(self):
        self.assertTrue(self.event.is_upcoming())

    def test_get_next_occurrence_weekly(self):
        next_occurrence = self.event.get_next_occurrence()
        self.assertIsNotNone(next_occurrence)


class EventViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')
        self.event = Event.objects.create(title="Test Event", description="Test Description", start_date=timezone.now() + timedelta(days=1), frequency='once')

    def test_event_list_view(self):
        response = self.client.get(reverse('events:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Event")

    def test_event_detail_view(self):
        response = self.client.get(reverse('events:detail', kwargs={
            'pk': self.event.pk
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Event")

    def test_event_create_view_requires_login(self):
        response = self.client.get(reverse('events:create'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_event_create_view_authenticated(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('events:create'))
        self.assertEqual(response.status_code, 200)
