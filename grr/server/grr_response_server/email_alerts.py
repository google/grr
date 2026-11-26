#!/usr/bin/env python
"""A simple wrapper to send email alerts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import re
import smtplib
import socket

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_core.lib.registry import MetaclassRegistry


class EmailNotSentError(Exception):
  """Exception raised when we fail to send an email."""


class EmailAlerterBase(metaclass=MetaclassRegistry):
  """The email alerter base class."""

  def RemoveHtmlTags(self, data: str) -> str:
    p = re.compile(r"<.*?>")
    return p.sub("", data)

  def AddEmailDomain(
      self, address: str | rdf_standard.DomainEmailAddress
  ) -> str:
    suffix = config.CONFIG["Logging.domain"]
    if isinstance(address, rdf_standard.DomainEmailAddress):
      address = str(address)
    if suffix and "@" not in address:
      return address + "@%s" % suffix
    return address

  def SplitEmailsAndAppendEmailDomain(
      self,
      address_list: (
          str
          | rdf_standard.DomainEmailAddress
          | Iterable[str | rdf_standard.DomainEmailAddress]
      ),
  ) -> list[str]:
    """Splits a string of comma-separated emails, appending default domain."""
    result = []
    # Process email addresses, and build up a list.
    if isinstance(address_list, rdf_standard.DomainEmailAddress):
      addresses: Iterable[str | rdf_standard.DomainEmailAddress] = [
          str(address_list)
      ]
    elif isinstance(address_list, str):
      addresses = [address for address in address_list.split(",") if address]
    else:
      addresses = address_list
    for address in addresses:
      result.append(self.AddEmailDomain(address))
    return result

  def SendEmail(
      self,
      to_addresses: (
          str
          | rdf_standard.DomainEmailAddress
          | Iterable[str | rdf_standard.DomainEmailAddress]
      ),
      from_address: str | rdf_standard.DomainEmailAddress,
      subject: str,
      message: str,
      attachments: Mapping[str, bytes] | None = None,
      is_html: bool = True,
      cc_addresses: (
          str
          | rdf_standard.DomainEmailAddress
          | Iterable[str | rdf_standard.DomainEmailAddress]
          | None
      ) = None,
      message_id: str | None = None,
      headers: Mapping[str, str] | None = None,
  ) -> None:
    """Sends an email."""
    raise NotImplementedError()


class SMTPEmailAlerter(EmailAlerterBase):

  def SendEmail(
      self,
      to_addresses: (
          str
          | rdf_standard.DomainEmailAddress
          | Iterable[str | rdf_standard.DomainEmailAddress]
      ),
      from_address: str | rdf_standard.DomainEmailAddress,
      subject: str,
      message: str,
      attachments: Mapping[str, bytes] | None = None,
      is_html: bool = True,
      cc_addresses: (
          str
          | rdf_standard.DomainEmailAddress
          | Iterable[str | rdf_standard.DomainEmailAddress]
          | None
      ) = None,
      message_id: str | None = None,
      headers: Mapping[str, str] | None = None,
  ) -> None:
    """This method sends an email notification.

    Args:
      to_addresses: blah@mycompany.com string, list of addresses as csv string,
        or rdf_standard.DomainEmailAddress
      from_address: blah@mycompany.com string
      subject: email subject string
      message: message contents string, as HTML or plain text
      attachments: iterable of filename string and file data tuples, e.g.
        {"/file/name/string": filedata}
      is_html: true if message is in HTML format
      cc_addresses: blah@mycompany.com string, or list of addresses as csv
        string
      message_id: smtp message_id. Used to enable conversation threading
      headers: dict of str-> str, headers to set

    Raises:
      EmailNotSentError: for problems connecting to smtp server.
    """
    headers = headers or {}
    msg = MIMEMultipart("alternative")
    if is_html:
      text = self.RemoveHtmlTags(message)
      part1 = MIMEText(text, "plain")
      msg.attach(part1)
      part2 = MIMEText(message, "html")
      msg.attach(part2)
    else:
      part1 = MIMEText(message, "plain")
      msg.attach(part1)

    if attachments:
      for file_name, file_data in attachments.items():
        part = MIMEBase("application", "octet-stream")
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", 'attachment; filename="%s"' % file_name
        )
        msg.attach(part)

    msg["Subject"] = subject

    from_addr = self.AddEmailDomain(from_address)
    to_addrs = self.SplitEmailsAndAppendEmailDomain(to_addresses)
    cc_addrs = self.SplitEmailsAndAppendEmailDomain(cc_addresses or "")

    msg["From"] = from_addr
    msg["To"] = ",".join(to_addrs)
    if cc_addrs:
      msg["CC"] = ",".join(cc_addrs)

    if message_id:
      msg.add_header("Message-ID", message_id)

    for header, value in headers.items():
      msg.add_header(header, value)

    try:
      s = smtplib.SMTP(
          config.CONFIG["Worker.smtp_server"],
          int(config.CONFIG["Worker.smtp_port"]),
      )
      s.ehlo()
      if config.CONFIG["Worker.smtp_starttls"]:
        s.starttls()
        s.ehlo()
      if (
          config.CONFIG["Worker.smtp_user"]
          and config.CONFIG["Worker.smtp_password"]
      ):
        s.login(
            config.CONFIG["Worker.smtp_user"],
            config.CONFIG["Worker.smtp_password"],
        )

      s.sendmail(from_addr, to_addrs + cc_addrs, msg.as_string())
      s.quit()
    except (socket.error, smtplib.SMTPException) as e:
      smtp_server = config.CONFIG["Worker.smtp_server"]
      raise EmailNotSentError(
          "Could not connect to SMTP server to send email. "
          "Please check config option Worker.smtp_server. "
          f"Currently set to {smtp_server}."
      ) from e


EMAIL_ALERTER: EmailAlerterBase | None = None


@utils.RunOnce
def InitializeEmailAlerterOnce() -> None:
  """Initializes e-mail alerts."""
  global EMAIL_ALERTER
  email_alerter_cls_name = config.CONFIG["Server.email_alerter_class"]
  logging.debug("Using email alerter: %s", email_alerter_cls_name)
  cls = EmailAlerterBase.GetPlugin(email_alerter_cls_name)

  EMAIL_ALERTER = cls()
