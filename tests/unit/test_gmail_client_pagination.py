import base64

from src import gmail_client


class _FakeRequest:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class _FakeMessages:
    def __init__(self, list_responses, message_payloads):
        self.list_responses = list_responses
        self.message_payloads = message_payloads
        self.list_calls = []

    def list(self, **kwargs):
        self.list_calls.append(kwargs)
        token = kwargs.get("pageToken")
        response = self.list_responses[token]
        return _FakeRequest(response)

    def get(self, userId, id, format):  # noqa: A002 - match API signature
        return _FakeRequest(self.message_payloads[id])


class _FakeUsers:
    def __init__(self, messages):
        self._messages = messages

    def messages(self):
        return self._messages


class _FakeService:
    def __init__(self, messages):
        self._users = _FakeUsers(messages)

    def users(self):
        return self._users


def _message_payload(message_id, subject, sender, body_text):
    encoded = base64.urlsafe_b64encode(body_text.encode("utf-8")).decode("ascii")
    return {
        "id": message_id,
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": "Tue, 10 Feb 2026 10:00:00 +0000"},
            ],
            "body": {"data": encoded},
        },
    }


def test_fetch_flight_emails_paginates(monkeypatch):
    list_responses = {
        None: {"messages": [{"id": "msg-1"}], "nextPageToken": "page-2"},
        "page-2": {"messages": [{"id": "msg-2"}]},
    }
    payloads = {
        "msg-1": _message_payload("msg-1", "Flight 1", "airline@example.com", "Body 1"),
        "msg-2": _message_payload("msg-2", "Flight 2", "airline@example.com", "Body 2"),
    }
    messages = _FakeMessages(list_responses, payloads)
    service = _FakeService(messages)

    monkeypatch.setattr(gmail_client, "get_gmail_service", lambda: service)

    emails = gmail_client.fetch_flight_emails(2026, 30)

    assert [email["id"] for email in emails] == ["msg-1", "msg-2"]
    assert len(messages.list_calls) == 2
