#!/usr/bin/env python

# Copyright 2011 Google Inc.
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

"""This is a place to define the flags for the various grr servers."""



from grr.client import conf as flags

flags.DEFINE_integer("max_queue_size", 500,
                     "Maximum number of messages to queue for the client.")

flags.DEFINE_integer("max_receiver_threads", 10,
                     "Maximum number of threads to use for receivers.")

flags.DEFINE_integer("max_retransmission_time", 10,
                     "Maximum number of times we are allowed to "
                     "retransmit a request until it fails.")

flags.DEFINE_integer("message_expiry_time", 600,
                     "Maximum time messages remain valid within the system.")

flags.DEFINE_string("server_cert", "grr/keys/test/server.pem",
                    "The path to the server public key and certificate.")

flags.DEFINE_string("server_private_key", "grr/keys/test/server-priv.pem",
                    "The path to the server private key.")
