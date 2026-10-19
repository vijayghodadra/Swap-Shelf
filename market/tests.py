from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from market.models import Listing, Thread, Message


class SwapShelfAuthorizationTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(
            username="alex", password="campus123", first_name="Alex"
        )
        self.jordan = User.objects.create_user(
            username="jordan", password="campus123", first_name="Jordan"
        )
        self.listing = Listing.objects.create(
            owner=self.alex,
            title="USB-C charger",
            description="Works well",
            price="10.00",
            category="electronics",
        )

    def test_profile_cannot_grant_staff_privileges(self):
        self.client.login(username="jordan", password="campus123")
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Jordan",
                "last_name": "Park",
                "email": "jordan@example.edu",
                "is_staff": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.jordan.refresh_from_db()
        self.assertFalse(self.jordan.is_staff)
        self.assertNotContains(self.client.get(reverse("desk")), "DESK-2290")

    def test_non_owner_cannot_edit_listing(self):
        self.client.login(username="jordan", password="campus123")
        response = self.client.get(reverse("listing_edit", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 404)

    def test_non_owner_cannot_mark_listing_sold(self):
        self.client.login(username="jordan", password="campus123")
        response = self.client.post(reverse("listing_sold", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 404)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, "available")

    def test_non_participant_cannot_view_or_post_to_thread(self):
        thread = Thread.objects.create(listing=self.listing, buyer=self.alex)
        Message.objects.create(thread=thread, sender=self.alex, body="Private message")
        self.client.login(username="jordan", password="campus123")
        response = self.client.get(reverse("thread_detail", args=[thread.pk]))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse("thread_detail", args=[thread.pk]), {"body": "intrusion"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(thread.messages.filter(body="intrusion").exists())

    def test_owner_can_edit_own_listing(self):
        self.client.login(username="alex", password="campus123")
        response = self.client.get(reverse("listing_edit", args=[self.listing.pk]))
        self.assertEqual(response.status_code, 200)


class SwapShelfFunctionalTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller_user", password="password123", first_name="Sam", email="sam@example.edu"
        )
        self.buyer = User.objects.create_user(
            username="buyer_user", password="password123", first_name="Bob", email="bob@example.edu"
        )
        self.staff_user = User.objects.create_user(
            username="staff_user", password="password123", first_name="Staff", is_staff=True
        )
        self.listing_book = Listing.objects.create(
            owner=self.seller,
            title="Algorithms Textbook",
            description="Good condition",
            price="45.00",
            category="books",
        )
        self.listing_tech = Listing.objects.create(
            owner=self.seller,
            title="Wireless Mouse",
            description="Like new",
            price="15.00",
            category="electronics",
        )

    def test_css_static_file_resolution(self):
        from django.contrib.staticfiles import finders
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        from django.test.client import RequestFactory

        # Verify staticfiles finder locates the stylesheet
        found_path = finders.find("market/style.css")
        self.assertIsNotNone(found_path)

        # Verify StaticFilesHandler serves the stylesheet successfully
        handler = StaticFilesHandler(lambda env, sr: None)
        request = RequestFactory().get("/static/market/style.css")
        response = handler(request.environ, lambda s, h: None)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "text/css")

    def test_public_board_and_category_filtering(self):
        # Anonymous visitor can see the board
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algorithms Textbook")
        self.assertContains(response, "Wireless Mouse")

        # Category filter for books
        response = self.client.get(reverse("home") + "?category=books")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algorithms Textbook")
        self.assertNotContains(response, "Wireless Mouse")

    def test_registration_login_logout(self):
        # Register new account
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "password1": "ValidPassword987!",
                "password2": "ValidPassword987!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

        # Sign out
        self.client.post(reverse("logout"))

        # Sign in
        login_res = self.client.post(
            reverse("sign_in"),
            {"username": "newuser", "password": "ValidPassword987!"},
        )
        self.assertEqual(login_res.status_code, 302)

    def test_create_listing(self):
        self.client.login(username="seller_user", password="password123")
        response = self.client.post(
            reverse("listing_new"),
            {
                "title": "Bike Helmet",
                "description": "Black, medium size",
                "price": "20.00",
                "category": "bikes",
                "seller_note": "Pick up near library",
            },
        )
        self.assertEqual(response.status_code, 302)
        new_listing = Listing.objects.get(title="Bike Helmet")
        self.assertEqual(new_listing.owner, self.seller)
        self.assertEqual(new_listing.category, "bikes")

    def test_owner_can_mark_sold(self):
        self.client.login(username="seller_user", password="password123")
        response = self.client.post(reverse("listing_sold", args=[self.listing_book.pk]))
        self.assertEqual(response.status_code, 302)
        self.listing_book.refresh_from_db()
        self.assertEqual(self.listing_book.status, "sold")

    def test_owner_can_delete_and_non_owner_cannot(self):
        # Non-owner cannot delete
        self.client.login(username="buyer_user", password="password123")
        response = self.client.post(reverse("listing_delete", args=[self.listing_book.pk]))
        self.assertEqual(response.status_code, 404)
        self.listing_book.refresh_from_db()
        self.assertEqual(self.listing_book.status, "available")

        # Owner can delete
        self.client.login(username="seller_user", password="password123")
        del_response = self.client.post(reverse("listing_delete", args=[self.listing_book.pk]))
        self.assertEqual(del_response.status_code, 302)
        self.listing_book.refresh_from_db()
        self.assertEqual(self.listing_book.status, "removed")

    def test_message_thread_flow(self):
        # Buyer starts thread
        self.client.login(username="buyer_user", password="password123")
        start_res = self.client.get(reverse("start_thread", args=[self.listing_tech.pk]))
        self.assertEqual(start_res.status_code, 302)
        thread = Thread.objects.get(listing=self.listing_tech, buyer=self.buyer)

        # Buyer sends message
        msg_res = self.client.post(
            reverse("thread_detail", args=[thread.pk]),
            {"body": "Is this still available?"},
        )
        self.assertEqual(msg_res.status_code, 302)
        self.assertEqual(thread.messages.count(), 1)
        self.assertEqual(thread.messages.first().sender, self.buyer)

        # Seller replies
        self.client.login(username="seller_user", password="password123")
        reply_res = self.client.post(
            reverse("thread_detail", args=[thread.pk]),
            {"body": "Yes, can meet today."},
        )
        self.assertEqual(reply_res.status_code, 302)
        self.assertEqual(thread.messages.count(), 2)

        # Owner cannot start buyer thread with self
        self_thread_res = self.client.get(reverse("start_thread", args=[self.listing_tech.pk]))
        self.assertEqual(self_thread_res.status_code, 302)
        self.assertNotIn("threads", self_thread_res.url)

    def test_profile_update_normal_fields(self):
        self.client.login(username="buyer_user", password="password123")
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Robert",
                "last_name": "Smith",
                "email": "robert.smith@example.edu",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.first_name, "Robert")
        self.assertEqual(self.buyer.last_name, "Smith")
        self.assertEqual(self.buyer.email, "robert.smith@example.edu")

    def test_department_desk_staff_access(self):
        # Non-staff user cannot see staff note
        self.client.login(username="buyer_user", password="password123")
        non_staff_res = self.client.get(reverse("desk"))
        self.assertEqual(non_staff_res.status_code, 200)
        self.assertNotContains(non_staff_res, "DESK-2290")
        self.assertContains(non_staff_res, "This page is for department board accounts.")

        # Staff user can see staff note
        self.client.login(username="staff_user", password="password123")
        staff_res = self.client.get(reverse("desk"))
        self.assertEqual(staff_res.status_code, 200)
        self.assertContains(staff_res, "DESK-2290")

