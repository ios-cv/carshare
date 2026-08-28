from django.test import TestCase, override_settings, RequestFactory
from django.utils import timezone
from django.urls import reverse
import json
from django.http import JsonResponse
from django.conf import settings

from bookings.models import Booking, get_current_booking_for_vehicle
from users.models import User
from billing.models import BillingAccount
from hardware.models import Vehicle, Box, BoxAction
from hardware.decorators import strip_errors_and_debug_from_api_response
from drivers.models import FullDriverProfile

TOUCH_URL = reverse("api_v1_touch")
FIXTURES = [
    "./hardware/test_data/station.json",
    "./hardware/test_data/bay.json",
    "./hardware/test_data/box.json",
    "./hardware/test_data/vehicletype.json",
    "./hardware/test_data/vehicle.json",
    "./hardware/test_data/card.json",
    "./hardware/test_data/user.json",
    "./hardware/test_data/billing.json",
    "./hardware/test_data/booking.json",
]


@strip_errors_and_debug_from_api_response
def dummy_view(request):
    testJson = json.loads(request.body)
    return JsonResponse(testJson, safe=False)


"""safe refers to a pre 2013 EMCAScript 3 vulnerability concerning JSON hijacking. 
It prevents Non dict object from being serialised.
For the purposes of testing safe=False poses no risk."""


@override_settings(STRIP_ERRORS_FROM_API_RESPONSE=True)
class StripErrorsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        return super().setUp()

    def test_strip_errors(self):
        input_data = {
            "error": "some error message",
            "action": "reject",
            "other_field": "some other data",
        }
        expected_output = {"action": "reject", "other_field": "some other data"}
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, expected_output)
        self.assertNotContains(response, '"error":"some error message"')

    def test_strip_errors_nested(self):
        input_data = {
            "error": "some error message",
            "action": "reject",
            "nested": {"error": "nested error message", "data": "some nested data"},
        }
        expected_output = {"action": "reject", "nested": {"data": "some nested data"}}
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, expected_output)
        self.assertNotContains(response, '"error":"some error message"')
        self.assertNotContains(response, '"error":"nested error message"')

    def test_strip_errors_no_error_key(self):
        input_data = {"action": "reject", "data": "some data"}
        expected_output = {"action": "reject", "data": "some data"}
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, expected_output)

    def test_strip_errors_non_dict(self):
        input_data = ["error", "some error message"]
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, input_data)

    def test_strip_errors_mixed_types(self):
        input_data = {
            "error": "some error message",
            "action": "reject",
            "list": [
                {"error": "list item error", "data": "list item data"},
                {"data": "list item without error"},
            ],
        }
        expected_output = {
            "action": "reject",
            "list": [{"data": "list item data"}, {"data": "list item without error"}],
        }
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, expected_output)
        self.assertNotContains(response, '"error":"some error message"')
        self.assertNotContains(response, '"error":"list item error"')

    def test_strip_debug(self):
        input_data = {"debug": "test endpoint identifier", "action": "accept"}
        expected_output = {
            "action": "accept",
        }
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, expected_output)
        self.assertNotContains(response, '"debug":"test endpoint identifier"')


@override_settings(STRIP_ERRORS_FROM_API_RESPONSE=False)
class StripErrorsDisabledTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        return super().setUp()

    def test_strip_errors_disabled(self):
        input_data = {
            "error": "some error message",
            "action": "reject",
            "other_field": "some other data",
        }
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, input_data)

    def test_strip_debug_disabled(self):
        input_data = {"debug": "debug endpooint identifier", "action": "accept"}
        request = self.factory.post(
            "/dummy/", data=json.dumps(input_data), content_type="application/json"
        )
        response = dummy_view(request)
        jsonOutput = json.loads(response.content)
        self.assertEqual(jsonOutput, input_data)


class ApiTouchHappyPath(TestCase):
    fixtures = FIXTURES

    def test_touch_happy_path(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(response, '"action": "lock"', status_code=200)
        self.assertNotContains(response, '"debug": "lock because operator card"')

        box = Box.objects.get(pk=1)
        box.locked = False
        box.save()
        with override_settings(STRIP_ERRORS_FROM_API_RESPONSE=False):
            response = self.client.post(
                TOUCH_URL,
                data=json.dumps(payload),
                content_type="application/json",
                HTTP_X_CARSHARE_BOX_ID="7B",
                HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
            )
            print(response.content)
            self.assertContains(
                response, '"debug": "lock because operator card"', status_code=200
            )


class ApiTouchDecoratorsFail(TestCase):
    fixtures = FIXTURES

    def test_touch_wrong_secret(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ac",  # Wrong secret
        )
        self.assertEqual(response.status_code, 401)

    def test_touch_no_secret(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
        )
        self.assertEqual(response.status_code, 401)

    def test_touch_no_box_id(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertEqual(response.status_code, 401)

    def test_touch_wrong_box_id(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7C",  # Wrong box ID
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertEqual(response.status_code, 401)

    def test_touch_non_hex_box_id(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="wrongid",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertEqual(response.status_code, 401)

    def test_touch_box_id_too_long(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="12345678901234567",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertEqual(response.status_code, 401)

    def test_touch_box_secret_wrong_length(self):
        payload = {"card_id": "01000000"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="short-secret",
        )
        self.assertEqual(response.status_code, 401)

    def test_touch_non_json_payload(self):
        response = self.client.post(
            TOUCH_URL,
            data="not a json payload",
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertEqual(response.status_code, 400)

    def test_touch_invalid_json_payload(self):
        response = self.client.post(
            TOUCH_URL,
            data="{invalid json}",
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertEqual(response.status_code, 400)

    def test_touch_method_not_allowed(self):
        response = self.client.get(
            TOUCH_URL,
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertEqual(response.status_code, 405)


@override_settings(STRIP_ERRORS_FROM_API_RESPONSE=False)
class ApiTouchReject(TestCase):
    fixtures = FIXTURES

    def test_touch_card_doesnt_exist(self):
        payload = {"card_id": "02000000"}  # Card doesn't exist
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response, '"error": "no card with that ID found"', status_code=200
        )
        box = Box.objects.get(pk=1)
        self.assertFalse(box.locked)  # Box should still be unlocked

    def test_touch_card_not_provided(self):
        payload = {}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(response, '"error": "missing card_id"', status_code=400)
        box = Box.objects.get(pk=1)
        self.assertFalse(box.locked)  # Box should still be unlocked

    def test_touch_box_not_assigned_to_vehicle(self):
        payload = {"card_id": "03000000"}  # Card is not an operator card
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="1C8",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890cd",
        )
        self.assertContains(
            response, '"error": "box is not assigned to any vehicle"', status_code=200
        )
        box = Box.objects.get(pk=2)
        self.assertFalse(box.locked)  # Box should still be unlocked

    def test_touch_no_active_booking(self):
        payload = {"card_id": "03000000"}  # Card is not an operator card
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7C",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ac",
        )
        self.assertContains(
            response, '"error": "no active booking found"', status_code=200
        )
        box = Box.objects.get(pk=3)
        self.assertTrue(box.locked)

    def test_touch_user_doesnt_have_permission(self):
        user = User.objects.get(id=1)
        ba = BillingAccount.objects.get(id=1)
        vehicle = Vehicle.objects.get(id=1)
        Booking.create_booking(
            user=user,
            vehicle=vehicle,
            billing_account=ba,
            start=timezone.now(),
            end=timezone.now() + timezone.timedelta(hours=1),
        )
        payload = {
            "card_id": "04000000"  # Card belongs to a user that is not a member of the billing account
        }
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response,
            '"error": "user cannot access this booking to lock"',
            status_code=200,
        )
        box = vehicle.box
        self.assertFalse(box.locked)
        box.locked = True
        box.save()
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response,
            '"error": "user cannot access this booking to unlock"',
            status_code=200,
        )
        box.refresh_from_db()
        self.assertTrue(box.locked)  # Box should still be locked
        box.locked = False
        box.save()

        booking = Booking.objects.last()
        booking.state = Booking.STATE_CANCELLED
        booking.save()
        driverprofile = FullDriverProfile.create(user=user)
        driverprofile.approved_full_name = True
        driverprofile.approved_address = True
        driverprofile.approved_date_of_birth = True
        driverprofile.approved_licence_number = True
        driverprofile.approved_licence_issue_date = True
        driverprofile.approved_licence_expiry_date = True
        driverprofile.approved_licence_front = True
        driverprofile.approved_licence_back = True
        driverprofile.approved_licence_selfie = True
        driverprofile.approved_proof_of_address = True
        driverprofile.approved_driving_record = True
        driverprofile.approved_at = timezone.now() - timezone.timedelta(days=1)
        driverprofile.expires_at = timezone.now() + timezone.timedelta(days=30)
        driverprofile.save()

        payload["card_id"] = "03000000"
        # This card belongs to the owner of the booking,
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(response, '"action": "lock"', status_code=200)
        box.refresh_from_db()
        self.assertTrue(box.locked)  # Box should have been locked

        box.locked = True
        box.save()
        booking.state = (
            Booking.STATE_ENDED
        )  # Should not be possible for a booking to end up in STATE_ENDED whilst also being current but this is the only way to test this scenario
        booking.save()
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response,
            '"error": "booking not in a state that allows unlocking"',
            status_code=200,
        )
        box.refresh_from_db()
        self.assertTrue(box.locked)  # Box should still be locked
        box.locked = False
        box.save()

    def test_touch_card_id_not_valid_hex(self):
        payload = {"card_id": "not hex"}
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response, '"error": "unable to parse card_id"', status_code=400
        )
        box = Box.objects.get(pk=1)
        self.assertFalse(box.locked)  # Box should still be unlocked

    def test_touch_card_disabled(self):
        payload = {
            "card_id": "05000000"  # enabled=False, operator=False, user=1 (is_operator, is_super_user, is_staff)
        }
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(response, '"error": "card is disabled"', status_code=200)
        payload = {
            "card_id": "06000000"  # enabled=False, operator=True, user=1 (is_operator, is_super_user, is_staff)
        }
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response, '"error": "card is disabled"', status_code=200
        )  # still rejected even though operator_card
        box = Box.objects.get(pk=1)
        self.assertFalse(box.locked)  # Box should still be unlocked

    def test_touch_lock_no_booking(self):
        box = Box.objects.get(pk=3)
        box.locked = False
        box.save()
        payload = {"card_id": "04000000"}  # neither card nor user is operator
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7C",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ac",
        )
        self.assertContains(
            response, '"error": "box is unlocked fallback"', status_code=200
        )
        box.refresh_from_db()
        self.assertFalse(box.locked)  # Box should still be unlocked


@override_settings(STRIP_ERRORS_FROM_API_RESPONSE=False)
class ApiTouchLock(TestCase):
    fixtures = FIXTURES

    def test_touch_waiting_box_action(self):
        box = Box.objects.get(pk=1)
        time_to_expire = timezone.now() + timezone.timedelta(minutes=10)
        action = BoxAction(
            action="lock",
            created_at=timezone.now(),
            expires_at=time_to_expire,
            box=box,
            user_id=1,
        )
        action.save()
        payload = {"card_id": "04000000"}  # neither card nor user is operator
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response, '"debug": "perform waiting box_action lock"', status_code=200
        )
        box_actions = BoxAction.objects.all()
        self.assertEqual(
            len(box_actions), 0
        )  # Waiting box action should have been deleted after being performed
        # box.refresh_from_db()
        # self.assertTrue(box.locked) #Box should be locked after performing the waiting lock action
        # This is not the case, the database isn't changed but the lock command is sent

    def test_touch_operator_lock(self):
        payload = {"card_id": "01000000"}  # operator card
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response, '"debug": "lock because operator card"', status_code=200
        )
        box = Box.objects.get(pk=1)
        self.assertTrue(box.locked)  # Box should be locked after operator locks
        self.assertIsNone(
            box.current_booking
        )  # Box's current booking should be cleared by the lock
        self.assertIsNone(
            box.unlocked_by
        )  # Box's unlocked_by should be cleared by the lock

    def test_touch_user_with_permission_from_booking_on_box_lock(self):
        user = User.objects.get(pk=1)
        driverprofile = FullDriverProfile.create(user=user)
        driverprofile.approved_full_name = True
        driverprofile.approved_address = True
        driverprofile.approved_date_of_birth = True
        driverprofile.approved_licence_number = True
        driverprofile.approved_licence_issue_date = True
        driverprofile.approved_licence_expiry_date = True
        driverprofile.approved_licence_front = True
        driverprofile.approved_licence_back = True
        driverprofile.approved_licence_selfie = True
        driverprofile.approved_proof_of_address = True
        driverprofile.approved_driving_record = True
        driverprofile.approved_at = timezone.now() - timezone.timedelta(days=1)
        driverprofile.expires_at = timezone.now() + timezone.timedelta(days=30)
        driverprofile.save()
        payload = {"card_id": "03000000"}  # admin's (booking owner) non operator card
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response,
            '"debug": "lock because user with access to booking on box requested"',
            status_code=200,
        )
        box = Box.objects.get(pk=1)
        self.assertIsNone(
            box.current_booking
        )  # actual end time should have been set by the lock
        self.assertTrue(
            box.locked
        )  # Box should be locked after user with permission locks
        self.assertIsNone(
            box.unlocked_by
        )  # Box's unlocked_by should be cleared by the lock

    def test_touch_user_with_permission_from_current_booking_lock(self):
        user = User.objects.get(id=2)
        ba = BillingAccount.objects.get(id=2)
        vehicle = Vehicle.objects.get(id=1)
        Booking.create_booking(
            user=user,
            vehicle=vehicle,
            billing_account=ba,
            start=timezone.now(),
            end=timezone.now() + timezone.timedelta(hours=1),
        )
        driverprofile = FullDriverProfile.create(user=user)
        driverprofile.approved_full_name = True
        driverprofile.approved_address = True
        driverprofile.approved_date_of_birth = True
        driverprofile.approved_licence_number = True
        driverprofile.approved_licence_issue_date = True
        driverprofile.approved_licence_expiry_date = True
        driverprofile.approved_licence_front = True
        driverprofile.approved_licence_back = True
        driverprofile.approved_licence_selfie = True
        driverprofile.approved_proof_of_address = True
        driverprofile.approved_driving_record = True
        driverprofile.approved_at = timezone.now() - timezone.timedelta(days=1)
        driverprofile.expires_at = timezone.now() + timezone.timedelta(days=30)
        driverprofile.save()
        payload = {"card_id": "04000000"}  # user's (booking owner) non operator card
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7B",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ab",
        )
        self.assertContains(
            response,
            '"debug": "lock because user with permission requested"',
            status_code=200,
        )
        box = Box.objects.get(pk=1)
        booking = Booking.objects.last()
        self.assertTrue(
            box.locked
        )  # Box should be locked after user with permission locks
        self.assertIsNone(
            box.current_booking
        )  # Box's current booking should be cleared
        self.assertIsNone(box.unlocked_by)  # Box's unlocked_by should have been cleared
        self.assertEqual(
            booking.state, Booking.STATE_INACTIVE
        )  # Booking should have been set to inactive by the lock
        self.assertIsNotNone(
            booking.actual_end_time
        )  # actual end time should have been set by the lock


@override_settings(STRIP_ERRORS_FROM_API_RESPONSE=False)
class ApiTouchUnlock(TestCase):
    fixtures = FIXTURES

    def test_touch_waiting_box_action(self):
        box = Box.objects.get(pk=3)
        time_to_expire = timezone.now() + timezone.timedelta(minutes=10)
        action = BoxAction(
            action="unlock",
            created_at=timezone.now(),
            expires_at=time_to_expire,
            box=box,
            user_id=1,
        )
        action.save()
        payload = {"card_id": "04000000"}  # neither card nor user is operator
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7C",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ac",
        )
        self.assertContains(
            response, '"debug": "perform waiting box_action unlock"', status_code=200
        )
        box_actions = BoxAction.objects.all()
        self.assertEqual(
            len(box_actions), 0
        )  # Waiting box action should have been deleted after being performed

    def test_touch_operator_unlock(self):
        # operator unlocks vehicle that doesn't have a current booking, should succeed and box should be unlocked at the end of the request
        payload = {"card_id": "01000000"}  # operator card
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7C",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ac",
        )
        self.assertContains(
            response, '"debug": "unlock because operator card"', status_code=200
        )
        box = Box.objects.get(pk=3)
        self.assertFalse(
            box.locked
        )  # Box should be unlocked after operator unlocks, even if there is no active booking

    def test_touch_user_with_permission_from_current_booking_unlock(self):
        user = User.objects.get(id=2)
        ba = BillingAccount.objects.get(id=2)
        vehicle = Vehicle.objects.get(id=2)
        Booking.create_booking(
            user=user,
            vehicle=vehicle,
            billing_account=ba,
            start=timezone.now(),
            end=timezone.now() + timezone.timedelta(hours=1),
        )
        driverprofile = FullDriverProfile.create(user=user)
        driverprofile.approved_full_name = True
        driverprofile.approved_address = True
        driverprofile.approved_date_of_birth = True
        driverprofile.approved_licence_number = True
        driverprofile.approved_licence_issue_date = True
        driverprofile.approved_licence_expiry_date = True
        driverprofile.approved_licence_front = True
        driverprofile.approved_licence_back = True
        driverprofile.approved_licence_selfie = True
        driverprofile.approved_proof_of_address = True
        driverprofile.approved_driving_record = True
        driverprofile.approved_at = timezone.now() - timezone.timedelta(days=1)
        driverprofile.expires_at = timezone.now() + timezone.timedelta(days=30)
        driverprofile.save()
        payload = {"card_id": "04000000"}  # user's (booking owner) non operator card
        response = self.client.post(
            TOUCH_URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CARSHARE_BOX_ID="7C",
            HTTP_X_CARSHARE_BOX_SECRET="12345678-9012-3456-7890-1234567890ac",
        )
        self.assertContains(
            response,
            '"debug": "unlock because user with permission requested"',
            status_code=200,
        )
        booking = Booking.objects.last()
        self.assertEqual(
            booking.state, Booking.STATE_ACTIVE
        )  # Booking should have been activated by the unlock
        self.assertIsNotNone(
            booking.actual_start_time
        )  # actual start time should have been set by the unlock
        self.assertIsNone(
            booking.actual_end_time
        )  # actual end time should have been cleared by the unlock
        box = Box.objects.get(pk=3)
        self.assertFalse(
            box.locked
        )  # Box should be unlocked after user with permission unlocks
        self.assertEqual(
            box.current_booking, booking
        )  # Box's current booking should be the booking that was just created
        self.assertEqual(
            box.unlocked_by.key, "4"
        )  # Box's unlocked_by should be the card that was used to unlock
