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

"""In this file we define constants that can be used by client and server."""



# Special folders we want to report back for each user. The format here is:
# registry key, folder name (relative to ProfileImagePath), protobuf name.
profile_folders = [("AppData", "Application Data", "app_data"),
                   ("Cache",
                    "AppData\\Local\\Microsoft\\Windows\\"
                    "Temporary Internet Files",
                    "cache"),
                   ("Cookies", "Cookies", "cookies"),
                   ("Desktop", "Desktop", "desktop"),
                   ("Favorites", "Favorites", "favorites"),
                   ("History",
                    "AppData\\Local\\Microsoft\\Windows\\History",
                    "history"),
                   ("Local AppData", "AppData\\Roaming", "local_app_data"),
                   ("Local Settings", "Local Settings", "local_settings"),
                   ("My Music", "Music", "my_music"),
                   ("My Pictures", "Pictures", "my_pictures"),
                   ("My Video", "Videos", "my_video"),
                   ("NetHood", "NetHood", "net_hood"),
                   ("Personal", "Documents", "personal"),
                   ("PrintHood", "PrintHood", "print_hood"),
                   ("Programs",
                    "AppData\\Roaming\\Microsoft\\Windows\\"
                    "Start Menu\\Programs",
                    "programs"),
                   ("Recent", "Recent", "recent"),
                   ("SendTo", "SendTo", "send_to"),
                   ("Start Menu",
                    "AppData\\Roaming\\Microsoft\\Windows\\Start Menu",
                    "start_menu"),
                   ("Startup",
                    "AppData\\Roaming\\Microsoft\\Windows\\"
                    "Start Menu\\Programs\\Startup",
                    "startup"),
                   ("Templates", "Templates", "templates")]


MAJOR_VERSION_WINDOWS_VISTA = 6
