#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A simple wrapper to send email alerts."""



from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import re
import smtplib

from grr.client import conf as flags

flags.DEFINE_string("smtp_server", "localhost",
                    "The smpt server for sending email alerts.")

flags.DEFINE_integer("smtp_port", 25,
                     "The smtp server port.")

FLAGS = flags.FLAGS


def RemoveHtmlTags(data):
  p = re.compile(r"<.*?>")
  return p.sub("", data)


def SendEmail(to_addresses, from_address, subject, message, is_html=True):
  """This method sends an email notification."""

  if is_html:
    msg = MIMEMultipart("alternative")
    text = RemoveHtmlTags(message)
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(message, "html")
    msg.attach(part1)
    msg.attach(part2)
  else:
    msg = MIMEText(message)

  msg["Subject"] = subject
  msg["From"] = from_address
  msg["To"] = to_addresses

  s = smtplib.SMTP(FLAGS.smtp_server, FLAGS.smtp_port)
  s.sendmail(from_address, [to_addresses], msg.as_string())
  s.quit()


