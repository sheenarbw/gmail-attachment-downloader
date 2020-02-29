import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path
import os
import base64

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def main(label_we_want, email):
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """

    print("===============================================")
    print("===============================================")
    print("Please sign in as: ")
    print(email)
    print("===============================================")
    print("===============================================")

    store_dir = Path("download") / email
    os.makedirs(store_dir, exist_ok=True)

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("gmail", "v1", credentials=creds)

    # Call the Gmail API to find the right label
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    if not labels:
        print("No labels found.")
        return

    chosen_labels = [d for d in labels if d["name"].lower() == label_we_want.lower()]
    assert (
        len(chosen_labels) != 0
    ), f"label {label_we_want} not found. We only have: {labels}"

    assert len(chosen_labels) == 1, f"multiple matching labels: {chosen_labels}"

    label = chosen_labels[
        0
    ]  # should look something like: {'id': 'Label_39', 'name': 'TAX REQUIREMENT', 'messageListVisibility': 'show', 'labelListVisibility': 'labelShow', 'type': 'user'}

    # Now use it to find the messages within that label
    # GET https://www.googleapis.com/gmail/v1/users/userId/messages

    print("getting messages...")
    messages = []
    message_result = (  # dict_keys(['messages', 'nextPageToken', 'resultSizeEstimate'])
        service.users().messages().list(userId="me", labelIds=[label["id"]]).execute()
    )
    messages.extend(message_result["messages"])

    while "nextPageToken" in message_result and message_result["nextPageToken"]:
        print("getting next page of messages")
        message_result = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=[label["id"]],
                pageToken=message_result["nextPageToken"],
            )
            .execute()
        )
        messages.extend(message_result["messages"])

    for message in messages:

        # service.users().messages().attachments().get(
        #     userId="me", messageId=message["id"]
        # )

        full_message = (
            service.users().messages().get(userId="me", id=message["id"]).execute()
        )
        # dict_keys(['id', 'threadId', 'labelIds', 'snippet', 'historyId', 'internalDate', 'payload', 'sizeEstimate'])
        subject = [
            d for d in full_message["payload"]["headers"] if d["name"] == "Subject"
        ][0]["value"]
        date = [d for d in full_message["payload"]["headers"] if d["name"] == "Date"][
            0
        ]["value"]

        print(f"processing: {date} - {subject}")

        if "payload" in full_message and "parts" in full_message["payload"]:
            print("downloading attachments")
            for part in full_message["payload"]["parts"]:
                # part.keys() => dict_keys(['partId', 'mimeType', 'filename', 'headers', 'body'])
                if part["filename"]:
                    path = store_dir / f"{date} - {subject} - {part['filename']}"
                    print(f"...saving to: {path}")

                    attachment = (
                        service.users()
                        .messages()
                        .attachments()
                        .get(
                            userId="me",
                            id=part["body"]["attachmentId"],
                            messageId=message["id"],
                        )
                        .execute()
                    )

                    file_data = base64.urlsafe_b64decode(
                        attachment["data"].encode("UTF-8")
                    )

                    f = open(path, "wb")
                    f.write(file_data)
                    f.close()
        else:
            print("no attachments")


if __name__ == "__main__":


    # main("YOUR LABEL", "your.name@gmail.domain")

