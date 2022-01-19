import json
import random

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def bonk(request):
    """View that is called by the box to ask what to do after a card has been bonked."""
    print(request.body)

    if request.method == "POST":
        j = json.loads(request.body)

        card = j.get("card_id", None)
        if card is None:
            action = "ignore"
        elif card == "0193fcf49a":
            action = "lock"
        elif card == "8804902e32":
            action = "unlock"
        else:
            action = "ignore"

    else:
        action = "ignore"

    response = {"action": action}
    print(response)

    return JsonResponse(response)
