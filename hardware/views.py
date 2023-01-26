import binascii
import logging
import struct

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from bookings.models import (
    Booking,
    get_current_booking_for_vehicle,
    user_can_access_booking,
)

from .decorators import require_authenticated_box, json_payload
from .models import Card, BoxAction

log = logging.getLogger(__name__)


def parse_card_id(card_id):
    return struct.unpack("<I", binascii.unhexlify(card_id))[0]


@csrf_exempt
@require_POST
@require_authenticated_box
@json_payload
def api_v1_telemetry(request, box, data):
    """View that is called by the box to share telemetry/do general keep-alive stuff."""

    response = {}

    # Handle box actions
    box_actions = BoxAction.objects.filter(
        Q(action=BoxAction.LOCK) | Q(action=BoxAction.UNLOCK),
        box=box,
        expires_at__gt=timezone.now(),
    ).order_by("created_at")

    if box_actions.count() > 0:
        box_action = box_actions.first()
        if box_action.action == BoxAction.LOCK:
            box_action.delete()
            response["action"] = "lock"
        elif box_action.action == BoxAction.UNLOCK:
            box_action.delete()
            response["action"] = "unlock"

    # Get the Supervisor Key List ETag from the headers.
    try:
        box_etag = int(request.headers.get("X-Carshare-Operator-Card-List-ETag", "0"))
    except ValueError:
        log.info(
            f"unable to parse X-Carshare-Operator-Card-List-ETag header for box {box.id}"
        )
        return JsonResponse(
            {"error": "unable to parse X-Carshare-Operator-Card-List-ETag header"},
            status=400,
        )

    # Get the ETag from the database too.
    server_etag = box.vehicle.operator_cards_etag

    if server_etag != box_etag:
        log.info(f"Operator Cards ETAG has changed for box {box.id}")
        response["operator_card_list"] = {
            "cards": [
                bytes.hex(struct.pack("<I", int(card.key)))
                for card in box.vehicle.operator_cards.all()
            ],
            "etag": server_etag,
        }

    # Handle the box's version header.
    firmware_version_header = int(
        request.headers.get("X-Carshare-Firmware-Version", "0")
    )
    if firmware_version_header == 0:
        log.warning(
            "Received a request from a box with firmware version 0 which should not happen."
        )

    else:
        # Update the actual box firmware version if it's changed.
        if firmware_version_header != box.firmware_version:
            box.firmware_version = firmware_version_header
            box.save()

        # See if we should tell the box to update it's firmware.
        if (
            firmware_version_header != box.desired_firmware_version.version
            and box.desired_firmware_version.version != 0
        ):
            log.info(
                f"Telling box {box.serial} [{box.id}] to update to firmware version {box.desired_firmware_version.version}"
            )
            response["firmware_update_url"] = request.build_absolute_uri(
                box.desired_firmware_version.bin_file.url
            )

    # If there's any telemetry, process it and record it.
    if "telemetry" in data:
        for k, v in data["telemetry"].items():
            log.debug(f"Telemetry data received from box {box.id}. {k}: {v}.")
        # FIXME: Actually save this data to the database somewhere.

    return JsonResponse(response)


@csrf_exempt
@require_POST
@require_authenticated_box
@json_payload
def api_v1_touch(request, box, data):
    """View that is called by the box when a card is touched on it."""

    # Check if we should short circuit this function because a box-action
    # is pending for this box.
    box_actions = BoxAction.objects.filter(
        Q(action=BoxAction.LOCK) | Q(action=BoxAction.UNLOCK),
        box=box,
        expires_at__gt=timezone.now(),
    ).order_by("created_at")

    if box_actions.count() > 0:
        box_action = box_actions.first()
        if box_action.action == BoxAction.LOCK:
            box_action.delete()
            return JsonResponse({"action": "lock"})
        elif box_action.action == BoxAction.UNLOCK:
            box_action.delete()
            return JsonResponse({"action": "unlock"})

    # Check a card ID has been provided.
    card_id = data.get("card_id", None)
    if not card_id:
        log.info("Missing card ID.")
        return JsonResponse({"error": "missing card_id"}, status=400)

    # Parse the card_id
    try:
        card_id = parse_card_id(card_id)
    except ValueError:
        log.info("unable to parse card_id as hex encoded integer")
        return JsonResponse(
            {"error": "unable to parse card_id"},
            status=400,
        )

    # Fetch the card
    try:
        card = Card.objects.get(key=card_id)
    except ObjectDoesNotExist:
        log.debug(f"No card with ID {card_id} found in the database")
        return JsonResponse({"action": "reject"})

    # Fetch the vehicle
    vehicle = box.vehicle
    if not vehicle:
        log.info(f"Box {box.id} is not assigned to any vehicle.")
        return JsonResponse(
            {"error": "box is not assigned to any vehicle", "action": "reject"}
        )

    # Fetch the current booking for this vehicle.
    booking = get_current_booking_for_vehicle(vehicle)
    log.debug(f"Fetched booking: {booking} for vehicle {vehicle.id}.")

    # FIXME: If an operator opens a car during a user's booking, then closes it late,
    #        the user can end up being treated as a late return. This needs to be
    #        fixed as could end up with user getting texts or fines for lateness.
    #        To do that I think we have to distinguish between "operator" access
    #        and emergency backup card access.

    # First handle the case where this is an operator card for the vehicle.
    if card in vehicle.operator_cards.all():
        if box.locked:
            # Unlocking the box.
            if booking:
                box.current_booking = booking
                box.unlocked_by = card
                booking.state = Booking.STATE_ACTIVE
                if booking.actual_start_time is None:
                    booking.actual_start_time = timezone.now()
                booking.actual_end_time = None
                booking.save()
            box.locked = False
            box.save()
            return JsonResponse({"action": "unlock"})

        else:
            # Locking the box.
            if box.current_booking:
                # If the box has a current booking then close that out with the locking.
                box.current_booking.state = Booking.STATE_INACTIVE
                box.current_booking.actual_end_time = timezone.now()
                box.current_booking.save()
            elif booking:
                # If the box didn't have a current booking set, but there's a booking running now, close that out.
                booking.state = Booking.STATE_INACTIVE
                booking.actual_end_time = timezone.now()
                booking.save()

            box.locked = True
            box.current_booking = None
            box.unlocked_by = None
            box.save()
            return JsonResponse({"action": "lock"})

    # Handle the cases where it is not an operator card being used.
    if box.locked:
        # To unlock, the card must be for a booking that hasn't ended yet.
        if booking is None:
            return JsonResponse({"action": "reject"})

        # Verify that the user has the right to unlock the booking.
        if not user_can_access_booking(card.user, booking):
            return JsonResponse({"action": "reject"})

        if booking.state in Booking.ALLOW_USER_UNLOCK_STATES:
            box.locked = False
            box.current_booking = booking
            box.unlocked_by = card
            box.save()
            booking.state = Booking.STATE_ACTIVE
            if booking.actual_start_time is None:
                booking.actual_start_time = timezone.now()
            booking.actual_end_time = None
            booking.save()
            return JsonResponse({"action": "unlock"})

        # If in doubt, don't unlock.
        return JsonResponse({"action": "reject"})

    # Handle the "lock" case for a non-operator.
    else:
        # First up, try and close out the booking that's set as currently active if it belongs to this user.
        if box.current_booking and user_can_access_booking(card.user, booking):
            box.current_booking.state = Booking.STATE_INACTIVE
            box.current_booking.actual_end_time = timezone.now()
            box.current_booking.save()
            box.locked = True
            box.current_booking = None
            box.unlocked_by = None
            box.save()
            return JsonResponse({"action": "lock"})

        # Failing that, see if the booking that's supposed to be now can trigger a lock.
        elif booking:
            if not user_can_access_booking(card.user, booking):
                return JsonResponse({"action": "reject"})
            box.locked = True
            box.current_booking = None
            box.unlocked_by = None
            box.save()
            booking.state = Booking.STATE_INACTIVE
            booking.actual_end_time = timezone.now()
            booking.save()
            return JsonResponse({"action": "lock"})

        # If in doubt, reject.
        return JsonResponse({"action": "reject"})

    # If in doubt, reject.
    return JsonResponse({"action": "reject"})
