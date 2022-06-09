import datetime

from celery import shared_task


@shared_task(name="run_billing")
def run_billing():
    now = datetime.datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print(f"Running billing cycle at {current_time}")
    # TODO: Actually implement the brains of this function.
