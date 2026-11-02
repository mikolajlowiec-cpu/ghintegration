# AWS Notes API

A small, authenticated serverless notes service intended as a hands-on target for threat-modeling exercises. It uses Amazon API Gateway HTTP API, Amazon Cognito, AWS Lambda, and Amazon DynamoDB.

## Architecture and data flow

1. A client obtains a Cognito JWT and sends it in the `Authorization` header.
2. API Gateway validates the token against the user pool and app client.
3. API Gateway invokes the Lambda function with the authenticated subject (`sub`) in the JWT claims.
4. The function uses that subject as the DynamoDB partition key for every read and write. The caller cannot supply or override the owner ID.
5. DynamoDB stores notes under `(ownerId, noteId)` and has point-in-time recovery enabled.

```text
Client -- JWT --> API Gateway -- verified claims --> Lambda -- scoped IAM --> DynamoDB
                         |                                |
                    Cognito User Pool                 ownerId = JWT sub
```

## API

All routes require a valid Cognito JWT:

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/notes` | List the caller's notes |
| `POST` | `/notes` | Create a note (`{"title":"...", "content":"..."}`) |
| `GET` | `/notes/{noteId}` | Read one of the caller's notes |
| `DELETE` | `/notes/{noteId}` | Delete one of the caller's notes |

## Deploy

Prerequisites: AWS SAM CLI, AWS CLI credentials for a development account, and a configured AWS region.

```sh
sam build
sam deploy --guided
```

The deployment outputs the API URL, Cognito user pool ID, and app client ID. Use a Cognito SDK or the AWS CLI to create a test user and obtain a JWT for that app client; send the token as `Authorization: Bearer <token>`.

## Run tests

The unit tests use only the Python standard library:

```sh
python3 -m unittest discover -s tests -v
```

## Threat-modeling prompts

- Which assets need protection (note contents, user identities, JWTs, and AWS credentials)?
- Where are the trust boundaries, and which component is responsible for validating each request?
- Can a user read, change, or delete another user's note? What tests or controls support the answer?
- What happens if a token is stolen, a Lambda dependency is compromised, or the API is abused at high volume?
- Are logging, monitoring, throttling, retention, and recovery adequate for the intended deployment?
- What risks come from the deployment operator's IAM permissions and the Cognito account-recovery flow?

This is a teaching sample, not a production-ready service. It omits operational controls such as API throttling, alarms, structured audit logging, deployment guardrails, and a user-facing sign-up/login interface. Review and adapt the template before deploying beyond a controlled development account.
