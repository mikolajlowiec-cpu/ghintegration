import json
import unittest
from unittest.mock import patch

from src import app


class FakeTable:
    def __init__(self):
        self.items = {}

    def query(self, KeyConditionExpression, ExpressionAttributeValues):
        owner_id = ExpressionAttributeValues[":ownerId"]
        return {
            "Items": [
                item for item in self.items.values() if item["ownerId"] == owner_id
            ]
        }

    def put_item(self, Item):
        self.items[(Item["ownerId"], Item["noteId"])] = Item

    def get_item(self, Key):
        item = self.items.get((Key["ownerId"], Key["noteId"]))
        return {"Item": item} if item else {}

    def delete_item(self, Key, ReturnValues):
        item = self.items.pop((Key["ownerId"], Key["noteId"]), None)
        return {"Attributes": item} if item else {}


def api_event(method, path_parameters=None, body=None, owner_id="user-1"):
    return {
        "requestContext": {
            "http": {"method": method},
            "authorizer": {"jwt": {"claims": {"sub": owner_id}}},
        },
        "pathParameters": path_parameters,
        "body": body,
    }


class NotesHandlerTests(unittest.TestCase):
    def setUp(self):
        self.table = FakeTable()
        self.table_patch = patch("src.app._table", return_value=self.table)
        self.table_patch.start()
        self.addCleanup(self.table_patch.stop)
        condition_patch = patch("src.app._owner_key_condition", side_effect=lambda owner_id: owner_id)
        condition_patch.start()
        self.addCleanup(condition_patch.stop)

    def test_create_and_list_notes(self):
        created = app.handler(
            api_event("POST", body=json.dumps({"title": " Plan ", "content": "Ship it"})),
            None,
        )
        self.assertEqual(created["statusCode"], 201)
        note = json.loads(created["body"])["note"]
        self.assertEqual(note["title"], "Plan")

        listed = app.handler(api_event("GET"), None)
        self.assertEqual(json.loads(listed["body"])["notes"], [note])

    def test_note_is_only_visible_to_its_owner(self):
        self.table.put_item(
            Item={"ownerId": "user-1", "noteId": "note-1", "title": "Private", "content": ""}
        )
        response = app.handler(
            api_event("GET", {"noteId": "note-1"}, owner_id="user-2"),
            None,
        )
        self.assertEqual(response["statusCode"], 404)

    def test_rejects_invalid_note(self):
        response = app.handler(
            api_event("POST", body=json.dumps({"title": " ", "content": "text"})),
            None,
        )
        self.assertEqual(response["statusCode"], 400)

    def test_rejects_missing_identity(self):
        response = app.handler(
            {"requestContext": {"http": {"method": "GET"}}},
            None,
        )
        self.assertEqual(response["statusCode"], 401)


if __name__ == "__main__":
    unittest.main()
