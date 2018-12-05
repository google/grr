#!/usr/bin/env python
"""A simple wrapper to send email alerts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import logging
import re
import smtplib
import socket


from future.utils import iteritems
from future.utils import string_types
from future.utils import with_metaclass

from grr_response_core import config
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import standard as rdf_standard


class EmailAlerterBase(with_metaclass(registry.MetaclassRegistry, object)):
  """The email alerter base class."""

  def RemoveHtmlTags(self, data):
    p = re.compile(r"<.*?>")
    return p.sub("", data)

  def AddEmailDomain(self, address):
    suffix = config.CONFIG["Logging.domain"]
    if isinstance(address, rdf_standard.DomainEmailAddress):
      address = str(address)
    if suffix and "@" not in address:
      return address + "@%s" % suffix
    return address

  def SplitEmailsAndAppendEmailDomain(self, address_list):
    """Splits a string of comma-separated emails, appending default domain."""
    result = []
    # Process email addresses, and build up a list.
    if isinstance(address_list, rdf_standard.DomainEmailAddress):
      address_list = [str(address_list)]
    elif isinstance(address_list, string_types):
      address_list = [address for address in address_list.split(",") if address]
    for address in address_list:
      result.append(self.AddEmailDomain(address))
    return result

  def SendEmail(self,
                to_addresses,
                from_address,
                subject,
                message,
                attachments=None,
                is_html=True,
                cc_addresses=None,
                message_id=None,
                headers=None):
    raise NotImplementedError()


class SMTPEmailAlerter(EmailAlerterBase):

  def SendEmail(self,
                to_addresses,
                from_address,
                subject,
                message,
                attachments=None,
                is_html=True,
                cc_addresses=None,
                message_id=None,
                headers=None):
    """This method sends an email notification.

    Args:
      to_addresses: blah@mycompany.com string, list of addresses as csv string,
                    or rdf_standard.DomainEmailAddress
      from_address: blah@mycompany.com string
      subject: email subject string
      message: message contents string, as HTML or plain text
      attachments: iterable of filename string and file data tuples,
                   e.g. {"/file/name/string": filedata}
      is_html: true if message is in HTML format
      cc_addresses: blah@mycompany.com string, or list of addresses as
                    csv string
      message_id: smtp message_id. Used to enable conversation threading
      headers: dict of str-> str, headers to set
    Raises:
      RuntimeError: for problems connecting to smtp server.
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
      for file_name, file_data in iteritems(attachments):
        part = MIMEBase("application", "octet-stream")
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition",
                        "attachment; filename=\"%s\"" % file_name)
        msg.attach(part)

    msg["Subject"] = subject

    from_address = self.AddEmailDomain(from_address)
    to_addresses = self.SplitEmailsAndAppendEmailDomain(to_addresses)
    cc_addresses = self.SplitEmailsAndAppendEmailDomain(cc_addresses or "")

    msg["From"] = from_address
    msg["To"] = ",".join(to_addresses)
    if cc_addresses:
      msg["CC"] = ",".join(cc_addresses)

    if message_id:
      msg.add_header("Message-ID", message_id)

    for header, value in iteritems(headers):
      msg.add_header(header, value)

    try:
      s = smtplib.SMTP(config.CONFIG["Worker.smtp_server"],
                       int(config.CONFIG["Worker.smtp_port"]))
      s.ehlo()
      if config.CONFIG["Worker.smtp_starttls"]:
        s.starttls()
        s.ehlo()
      if (config.CONFIG["Worker.smtp_user"] and
          config.CONFIG["Worker.smtp_password"]):
        s.login(config.CONFIG["Worker.smtp_user"],
                config.CONFIG["Worker.smtp_password"])

      s.sendmail(from_address, to_addresses + cc_addresses, msg.as_string())
      s.quit()
    except (socket.error, smtplib.SMTPException) as e:
      raise RuntimeError("Could not connect to SMTP server to send email. "
                         "Please check config option Worker.smtp_server. "
                         "Currently set to %s. Error: %s" %
                         (config.CONFIG["Worker.smtp_server"], e))


EMAIL_ALERTER = None


class EmailAlerterInit(registry.InitHook):

  def RunOnce(self):
    global EMAIL_ALERTER
    email_alerter_cls_name = config.CONFIG["Server.email_alerter_class"]
    logging.debug("Using email alerter: %s", email_alerter_cls_name)
    cls = EmailAlerterBase.GetPlugin(email_alerter_cls_name)

    EMAIL_ALERTER = cls()
