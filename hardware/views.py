from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .decorators import require_authenticated_box, json_payload


@csrf_exempt
@require_POST
@require_authenticated_box
@json_payload
def api_v1_telemetry(request, box, data):
    """View that is called by the box to share telemetry/do general keep-alive stuff."""

    response = {}

    # Get the Supervisor Key List ETag from the headers.
    box_etag = int(request.headers.get("X-Carshare-Operator-Card-List-ETag", "0"))

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

    # TODO: Respond based on whether the card is an operator card or has a valid booking.

    response = {
        "action": "reject",
    }
    return JsonResponse(response)
