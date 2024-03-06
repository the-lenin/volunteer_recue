"""Test actions between CustomUserAdmin and CustomUser."""
from django.test import Client, TestCase
from django.urls import reverse
from django.http import HttpRequest
from .models import CustomUser
from django.utils.translation import gettext as _


class BaseSetAdmin(TestCase):
    """
    Create a Superuser instance in DB for all following methods.

    Once before any of the tests and delete it at the end.
    """
    password = 'admin123'

    @classmethod
    def setUpTestData(cls):
        """Create a superuser for testing admin dashboard,
        once for the class."""
        cls.superuser = CustomUser.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            phone_number='+79111132812',
            address='Test Address',
            has_car=False,
        )

    @classmethod
    def tearDownTestData(cls):
        """Delete superuser after all tests."""
        cls.superuser.delete()


class TestAdminAccess(BaseSetAdmin):
    """Test access to admin dashboard panel."""

    def setUp(self):
        """Set initial condition for each test method."""
        self.client = Client()

    def test_admin_access_index(self):
        """Test Admin access to admin index page."""
        admin_index_url = reverse('admin:index')
        request = HttpRequest()

        self.client.login(
            request=request,
            username=self.superuser.username,
            password=self.password
        )

        response = self.client.get(admin_index_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Django')


class CustomUserCRUDByAdmin(BaseSetAdmin):
    """Test CustomUsser CRUD by admin dashboard."""

    @classmethod
    def setUpTestData(cls):
        """
        Create a superuser for testing admin dashboard, once for the class.
        """
        super().setUpTestData()
        cls.test_user = CustomUser.objects.create_user(
            username='testuser',
            password='testpassword123',
            email='testuser@example.com',
            first_name='Test',
            last_name='User',
            phone_number='+79111132811',
            address='Test Address',
            has_car=False,
        )

    @classmethod
    def tearDownTestData(cls):
        super().tearDownTestData()
        cls.test_user.delete()

    def setUp(self):
        """Set up test environment and login admin."""
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_admin_create_user(self):
        """Test user creation by Admin."""
        create_url = reverse('admin:users_customuser_add')

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            create_url,
            data={
                'username': 'testuser2',
                'password1': 'testpassword123',
                'password2': 'testpassword123',
                'email': 'testuser2@example.com',
                'first_name': 'Test',
                'last_name': 'CustomUser',
                'patronymic_name': 'Patronymic',
                'address': 'Test Address',
                'phone_number': '+79111132810',
                'has_car': False,
                'comment': 'Test Comment',
            },
        )

        self.assertEqual(response.status_code, 302)
        user = CustomUser.objects.get(username='testuser2')
        self.assertTrue(user)

        default_group_name = 'Volunteer'
        print(user.groups.all())
        self.assertTrue(user.groups.filter(name=default_group_name).exists())

    def test_admin_update_user(self):
        """Test updating user by Admin."""
        test_user = CustomUser.objects.get(username='testuser')
        update_url = reverse('admin:users_customuser_change',
                             args=[test_user.pk])

        response = self.client.get(update_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            update_url,
            data={
                'username': 'testuser',
                'email': 'updated_user@example.com',
                'first_name': 'Updated',
                'last_name': 'User',
                'patronymic_name': 'Updated Patronymic',
                'address': 'Updated Address',
                'phone_number': '+79111132811',
                'has_car': False,
                'comment': 'Updated Comment',
            },
        )

        self.assertEqual(response.status_code, 302)

        updated_user = CustomUser.objects.get(pk=test_user.pk)
        self.assertEqual(updated_user.username, 'testuser')
        self.assertEqual(updated_user.email, 'updated_user@example.com')
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'User')
        self.assertEqual(updated_user.patronymic_name, 'Updated Patronymic')
        self.assertEqual(updated_user.address, 'Updated Address')
        self.assertEqual(updated_user.phone_number, '+79111132811')
        self.assertEqual(updated_user.has_car, False)
        self.assertEqual(updated_user.comment, 'Updated Comment')

    def test_admin_delete_user(self):
        """Test deleting user by Admin."""
        test_user = CustomUser.objects.get(username='testuser')
        delete_url = reverse('admin:users_customuser_delete',
                             args=[test_user.pk])

        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(delete_url, data={'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CustomUser.objects.filter(pk=test_user.pk).exists())

    def test_admin_fail_add_user(self):
        """
        Test failure scenario of adding a user with missing required fields.
        """
        self.assertEqual(CustomUser.objects.count(), 2)

        add_user_url = reverse('admin:users_customuser_add')
        response = self.client.post(add_user_url, data={})
        self.assertEqual(response.status_code, 200)

        self.assertEqual(CustomUser.objects.count(), 2)
        self.assertContains(response, _('This field is required.'))
