from locust import HttpUser, task, between
import random
import uuid
import time
from datetime import datetime, timezone


class EventPulseUser(HttpUser):
    wait_time = between(0.1, 0.5)
    headers = {"X-API-Key": "test_api_key_123"}

    counter = 0

    @task(100)
    def ingest_event(self):
        self.__class__.counter += 1

        nano_time = int(time.time() * 1_000_000_000)
        unique_event_id = f"evt-{nano_time}-{self.__class__.counter}-{uuid.uuid4().hex[:8]}"

        event_name = random.choice([
            "payment.failed",
            "user.login",
            "order.created",
            "payment.success",
            "user.logout"
        ])

        with self.client.post(
                "/ingest",
                json={
                    "event_name": event_name,
                    "payload": {
                        "user_id": random.randint(1, 100000),
                        "event_id": unique_event_id,
                        "session_id": uuid.uuid4().hex,
                        "request_counter": self.__class__.counter,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                headers=self.headers,
                catch_response=True
        ) as response:
            if response.status_code == 409:
                response.failure(f"Conflict (409): Event already exists - {unique_event_id}")
            elif response.status_code != 200 and response.status_code != 201:
                response.failure(f"Unexpected status: {response.status_code}")
            else:
                response.success()
