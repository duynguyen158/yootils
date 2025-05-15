from base64 import urlsafe_b64encode
from collections.abc import Sequence
from email.message import EmailMessage

from asyncer import asyncify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def send_html_email(
    subject: str,
    body: str,
    sender: str,
    recipients: Sequence[str],
    cc: Sequence[str],
    bcc: Sequence[str],
    *,
    token: Credentials,
) -> None:
    """
    Sends an HTML email using the Gmail API.

    Args:
        subject: Subject of the email.
        body: Body of the email.
        sender: Sender of the email.
        recipients: Recipients of the email.
        cc: Carbon copy recipients of the email.
        bcc: Blind carbon copy recipients of the email.
        token: OAuth2 credentials for the Gmail API.

    Returns:
        None
    """
    service = build("gmail", "v1", credentials=token)

    message = EmailMessage()
    message["Subject"] = subject
    message.set_content(body, subtype="html")

    message["From"] = sender
    # All recipients are managed through Google Groups
    message["To"] = recipients
    message["Cc"] = cc
    message["Bcc"] = bcc

    encoded_message = urlsafe_b64encode(message.as_bytes()).decode()

    # Send the message
    request = (
        service.users().messages().send(userId="me", body={"raw": encoded_message})
    )
    request.execute()


async def send_html_email_async(
    subject: str,
    body: str,
    sender: str,
    recipients: Sequence[str],
    cc: Sequence[str],
    bcc: Sequence[str],
    *,
    token: Credentials,
) -> None:
    """
    Sends an HTML email using the Gmail API asynchronously.

    Args:
        subject: Subject of the email.
        body: Body of the email.
        sender: Sender of the email.
        recipients: Recipients of the email.
        cc: Carbon copy recipients of the email.
        bcc: Blind carbon copy recipients of the email.
        token: OAuth2 credentials for the Gmail API.

    Returns:
        None
    """
    service = await asyncify(build)("gmail", "v1", credentials=token)

    message = EmailMessage()
    message["Subject"] = subject
    message.set_content(body, subtype="html")

    message["From"] = sender
    # All recipients are managed through Google Groups
    message["To"] = recipients
    message["Cc"] = cc
    message["Bcc"] = bcc

    encoded_message = urlsafe_b64encode(message.as_bytes()).decode()

    # Send the message
    request = (
        service.users().messages().send(userId="me", body={"raw": encoded_message})
    )
    await asyncify(request.execute)()
