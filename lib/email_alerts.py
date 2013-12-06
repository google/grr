#!/usr/bin/env python
"""A simple wrapper to send email alerts."""



from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import re
import smtplib
import socket

from grr.lib import config_lib
from grr.lib import utils


def RemoveHtmlTags(data):
  p = re.compile(r"<.*?>")
  return p.sub("", data)


def SendEmail(to_addresses, from_address, subject, message, attachments=None,
              is_html=True):
  """This method sends an email notification."""
  msg = MIMEMultipart("alternative")
  if is_html:
    text = RemoveHtmlTags(message)
    part1 = MIMEText(text, "plain")
    msg.attach(part1)
    part2 = MIMEText(message, "html")
    msg.attach(part2)
  else:
    part1 = MIMEText(message, "plain")
    msg.attach(part1)

  if attachments:
    for file_name, file_data in attachments.iteritems():
      part = MIMEBase("application", "octet-stream")
      part.set_payload(file_data)
      encoders.encode_base64(part)
      part.add_header("Content-Disposition",
                      "attachment; filename=\"%s\"" % file_name)
      msg.attach(part)

  msg["Subject"] = subject
  msg["From"] = from_address
  msg["To"] = to_addresses

  try:
    s = smtplib.SMTP(config_lib.CONFIG["Worker.smtp_server"],
                     int(config_lib.CONFIG["Worker.smtp_port"]))
    s.sendmail(from_address, [to_addresses], msg.as_string())
    s.quit()
  except (socket.error, smtplib.SMTPException) as e:
    raise RuntimeError("Could not connect to SMTP server to send email. Please "
                       "check config option Worker.smtp_server. Currently set "
                       "to %s. Error: %s" %
                       (config_lib.CONFIG["Worker.smtp_server"], e))


