webhook = dict(
  # The URL of your Discord webhook.
  url        = "",

  # The username the webhook will use.
  username   = "Status",

  # The avatar URL the webhook will use. If blank, will just use a default
  # discord avatar.
  avatar_url = "",
)

statuses = dict(
  # The maximum age to actually monitor a status for. If a status is older than
  # this, it will not be monitored. Default is 30 days.
  max_age = 60 * 60 * 24 * 30, # 60 seconds * 60 minutes * 24 hours * 30 days
)

embeds = dict(
  status = dict(
    resolved      = 0x06a51b, # Default Green (#06a51b)
    monitoring    = 0xa3a506, # Default Yellow (#a3a506)
    identified    = 0xa55806, # Default Orange (#a55806)
    investigating = 0xa50626, # Default Red (#a50626)
    other         = 0xa506a3, # Default Purple (#a506a3)
  ),

  # The discord timestamp format, i.e: ":(t|T|d|D|f|F|R)"
  # "" <empty string>: Discord's default ("November 28, 2018 9:01 AM"/"28 November 2018 09:01")
  # ":t": Short time ("9:01 AM")
  # ":T": Long time ("9:01:01 AM")
  # ":d": Short date ("11/28/2018")
  # ":D": Long date ("November 28, 2018")
  # ":f": Short date/time ("11/28/2018 9:01 AM")
  # ":F": Long date/time ("November 28, 2018 9:01 AM")
  # ":R" (Default): Relative time ("2 months ago")
  #
  # Values taken from LeviSnoot's Gist:
  #  --> https://gist.github.com/LeviSnoot/d9147767abeef2f770e9ddcd91eb85aa
  # Check it out for more info, it is a useful resource.
  timestamp_format = ":R"
)

api = dict(
  # Default: "https://discordstatus.com/api/v2/incidents.json"
  # It is recommended you do not change this, unless you know what you are doing.
  url = "https://discordstatus.com/api/v2/incidents.json"
)

import logging
log = dict(
  # The log level to use. Default is WARN.
  log_level = logging.DEBUG,

  # The log file to write to. If empty string, will not write a log file at all.
  log_file  = "discord-status.log",

  # The mode to open the log file in. Default is: "a". Modes are as follows:
  # - "w": Write mode. Will overwrite the file every time the script is run.
  # - "a": Append mode. Will append to the file every time the script is run.
  #        This can result in rather large log files if on log levels at or
  #        below logging.INFO, since old data is not removed.
  log_file_mode = "w",

  # The log format to use. Default is:
  # "%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s"
  log_format = "%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",

  # The date format to use. Default is: "%Y-%m-%d %H:%M:%S"
  date_format = "%Y-%m-%d %H:%M:%S",
)