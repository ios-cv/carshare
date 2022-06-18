from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from bookings.models import Booking, get_current_booking_for_vehicle

from .decorators import require_authenticated_box, json_payload
from .models import Card


@csrf_exempt
@require_POST
@require_authenticated_box
@json_payload
def api_v1_telemetry(request, box, data):
    """View that is called by the box to share telemetry/do general keep-alive stuff."""

    response = {}

    # Get the Supervisor Key List ETag from the headers.
    try:
        box_etag = int(request.headers.get("X-Carshare-Operator-Card-List-ETag", "0"))
    except ValueError:
        return JsonResponse(
            {"error": "unable to parse X-Carshare-Operator-Card-List-ETag header"},
            status=400,
        )

    # Get the ETag from the database too.
    server_etag = box.vehicle.operator_cards_etag

    if server_etag != box_etag:
        response["operator_card_list"] = {
            "cards": [card.key for card in box.vehicle.operator_cards.all()],
            "etag": server_etag,
        }

    # If there's any telemetry, process it and record it.
    if "telemetry" in data:
        for k, v in data["telemetry"].items():
            print(f"Telemetry data received from box {box.id}. {k}: {v}.")
        # FIXME: Actually save this data to the database somewhere.

    return JsonResponse(response)


@csrf_exempt
@require_POST
@require_authenticated_box
@json_payload
def api_v1_touch(request, box, data):
    """View that is called by the box when a card is touched on it."""

    # Check a card ID has been provided.
    card_id = data.get("card_id", None)
    if not card_id:
        return JsonResponse({"error": "missing card_id"}, status=400)

    # Fetch the card
    try:
        card = Card.objects.get(key=card_id)
    except ObjectDoesNotExist:
        return JsonResponse({"error": "card ID not found"}, status=401)

    # Fetch the vehicle
    vehicle = box.vehicle
    if not vehicle:
        return JsonResponse(
            {"error": "box is not assigned to any vehicle", "action": "reject"}
        )

    # If the card is an operator card for this vehicle, allow lock/unlock regardless of anything else
    if card in vehicle.operator_cards.all():
        if box.locked:
            box.locked = False
            box.save()
            # TODO: Update other box state parameters.
            return JsonResponse({"action": "unlock"})
        else:
            box.locked = True
            box.save()
            # TODO: Update other box state parameters
            return JsonResponse({"action": "lock"})

    # Retrieve the current booking for this car.
    # FIXME: If the car is being returned late this won't find a booking. Need to handle
    #        that case properly, by always sending a "lock" command.
    booking = get_current_booking_for_vehicle(vehicle)
    print(f"Fetched booking for vehicle: {booking}.")

    # TODO: If there is no current booking, reject.
    # FIXME: What to do if someone returns it late? We should allow lock but not allow unlock.
    #        Therefore, if the current state is "unlocked" then we should allow the user who is currently in their
    #        rental to unlock the car???
    #        Car rental state probably needs to be "locked: boolean, current_booking: booking_id (only set if unlocked), unlocked_by: card_id"

    # If there is a current booking, check if the card belongs to the user who has this booking.
    if card.user != booking.user:
        return JsonResponse({"action": "reject"})

    # We now know the card belongs to the correct user. See whether we are starting or ending the booking.
    if box.locked:
        if booking.state in Booking.ALLOW_USER_UNLOCK_STATES:
            box.locked = False
            box.current_booking = booking
            box.unlocked_by = card
            box.save()
            booking.state = Booking.STATE_ACTIVE
            return JsonResponse({"action": "unlock"})
        else:
            return JsonResponse({"action": "reject"})

    else:
        box.locked = True
        box.current_booking = None
        box.unlocked_by = None
        box.save()
        return JsonResponse({"action": "lock"})

    # TODO: In future, check if they belong to the same billing account, to allow access to delegated users.

    return JsonResponse({"action": "reject"})
