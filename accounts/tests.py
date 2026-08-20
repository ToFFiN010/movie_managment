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
        self.assertRedirects(response, reverse('movies:listing'), fetch_redirect_response=False)

    def test_profile_update(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('accounts:profile'), {
            'phone': '1122334455',
            'address': '123 Cinema Way'
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, '1122334455')

    def test_password_reset_request_registered_email(self):
        from django.core import mail
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, 'CinePrime - Reset Your Password')
        self.assertIn('testuser', sent_email.body)
        self.assertIn('/accounts/password-reset-confirm/', sent_email.body)
        self.assertIn('We received a request to reset your CinePrime password', sent_email.body)

    def test_password_reset_request_unregistered_email(self):
        from django.core import mail
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': 'unknown@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        # No email sent for unregistered address, protecting user privacy
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_invalid_token(self):
        response = self.client.get(reverse('accounts:password_reset_confirm', kwargs={
            'uidb64': 'invaliduid',
            'token': 'invalidtoken'
        }))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Link Expired')

    def test_password_reset_confirm_weak_password(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        
        # GET request follows redirect to set-password form
        get_resp = self.client.get(confirm_url, follow=True)
        self.assertEqual(get_resp.status_code, 200)

        # POST weak password to the redirected set-password form
        set_password_url = get_resp.redirect_chain[0][0]
        response = self.client.post(set_password_url, {
            'new_password1': '123',
            'new_password2': '123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please fix the password errors below')

    def test_password_reset_full_flow_success(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        
        # GET request follows redirect to set-password form
        get_resp = self.client.get(confirm_url, follow=True)
        self.assertEqual(get_resp.status_code, 200)

        set_password_url = get_resp.redirect_chain[0][0]
        new_pass = 'SuperSecurePass2026!'
        response = self.client.post(set_password_url, {
            'new_password1': new_pass,
            'new_password2': new_pass
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:password_reset_complete'))
        
        # Verify user can log in with new password
        login_response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': new_pass
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertRedirects(login_response, reverse('movies:listing'))

