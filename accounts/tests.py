from django.test import TestCase
from django.urls import reverse
from accounts.models import User, UserProfile

class AccountsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        UserProfile.objects.create(user=self.user)

    def test_user_creation_and_role(self):
        self.assertEqual(self.user.role, User.Role.USER)
        self.assertFalse(self.user.is_admin_role)

    def test_login_view(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('movies:listing'))

    def test_profile_update(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('accounts:profile'), {
            'phone': '1122334455',
            'address': '123 Cinema Way'
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '1122334455')
