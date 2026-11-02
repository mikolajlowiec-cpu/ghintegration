import json
import os
from uuid import uuid4


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _owner_id(event):
    try:
        return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    except (KeyError, TypeError):
        return None


def _table():
    import boto3

    return boto3.resource("dynamodb").Table(os.environ["NOTES_TABLE"])


def _owner_key_condition(owner_id):
    from boto3.dynamodb.conditions import Key

    return Key("ownerId").eq(owner_id)


def handler(event, context):
    owner_id = _owner_id(event)
    if not owner_id:
        return _response(401, {"message": "Unauthorized"})

    method = event.get("requestContext", {}).get("http", {}).get("method")
    path_parameters = event.get("pathParameters") or {}
    note_id = path_parameters.get("noteId")
    table = _table()

    if method == "GET" and not note_id:
        result = table.query(
            KeyConditionExpression=_owner_key_condition(owner_id),
            ExpressionAttributeValues={":ownerId": owner_id},
        )
        return _response(200, {"notes": result.get("Items", [])})

    if method == "POST" and not note_id:
        try:
            payload = json.loads(event.get("body") or "")
        except (json.JSONDecodeError, TypeError):
            return _response(400, {"message": "Request body must be valid JSON"})
        if not isinstance(payload, dict):
            return _response(400, {"message": "Request body must be a JSON object"})

        title = payload.get("title")
        content = payload.get("content")
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            return _response(400, {"message": "title must be a non-empty string of at most 200 characters"})
        if not isinstance(content, str) or len(content) > 10000:
            return _response(400, {"message": "content must be a string of at most 10000 characters"})

        note = {
            "ownerId": owner_id,
            "noteId": str(uuid4()),
            "title": title.strip(),
            "content": content,
        }
        table.put_item(Item=note)
        return _response(201, {"note": note})

    if method == "GET" and note_id:
        result = table.get_item(Key={"ownerId": owner_id, "noteId": note_id})
        note = result.get("Item")
        if note is None:
            return _response(404, {"message": "Note not found"})
        return _response(200, {"note": note})

    if method == "DELETE" and note_id:
        result = table.delete_item(
            Key={"ownerId": owner_id, "noteId": note_id},
            ReturnValues="ALL_OLD",
        )
        if "Attributes" not in result:
            return _response(404, {"message": "Note not found"})
        return _response(204, {})

    return _response(404, {"message": "Route not found"})
