# Author: Matthew Wilbern (Fatboychummy)
# Description: Small script to send Discord Status updates to a webhook.
# Dependencies: discord.py
# Usage: python3 main.py
# 
# Copyright 2024 Matthew Wilbern
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



from discord.webhook import Webhook
from discord.embeds import Embed
from datetime import datetime
from dateutil import parser
import aiohttp
import logging
import asyncio
import requests
import pathlib
import traceback

import config
import cache

if config.log["log_file"] == "":
  # No log file is wanted, just log to console.
  logging.basicConfig(
    level=config.log["log_level"],
    format=config.log["log_format"],
    datefmt=config.log["date_format"]
  )
else:
  # A log file is wanted, so we should append to it.
  logging.basicConfig(
    level=config.log["log_level"],
    format=config.log["log_format"],
    datefmt=config.log["date_format"],

    filename=config.log["log_file"],
    filemode=config.log["log_file_mode"]
  )

path = pathlib.Path(__file__).parent.absolute()
cache_manager: cache.CacheManager = None

main = logging.getLogger("dsw")

async def get_statuses():
  """
    Gets all the status updates from discordstatus.com.
  """

  try:
    main.info(f"Getting statuses from {config.api['url']}...")
    response = await asyncio.to_thread(requests.get, url=config.api["url"])
    return response.json()["incidents"]
  except Exception as e:
    main.error(f"Failed to get statuses: {e}\n{traceback.format_exc()}")
    return None


def build_embed(incident: dict) -> Embed:
  """
    Builds an embed from an incident.

    Parameters:
      incident (dict): The incident to build the embed from.
  """

  embed = Embed(
    title=incident["name"],
    url=incident["shortlink"],
    description=f"Impact: {incident['impact']}\nAffected Components: {', '.join([component['name'] for component in incident['components']])}",
    timestamp=parser.isoparse(incident["created_at"]),
  )

  # Iterate over incidents backwards, since they are stored in reverse order.
  for update in reversed(incident["incident_updates"]):
    """
    {
      "id": "v3276k3xgpkm",
      "status": "investigating",
      "body": "All services back to normal except the activities shelf which has been temporarily disabled",
      "incident_id": "wlf7gks7nb1m",
      "created_at": "2024-08-27T15:01:36.337-07:00",
      "updated_at": "2024-08-27T15:01:36.337-07:00",
      "display_at": "2024-08-27T15:01:36.337-07:00",
      "affected_components": [],
      "deliver_notifications": true,
      "custom_tweet": null,
      "tweet_id": null
    },
    """
    
    embed.add_field(
      name=f"{update['status'].capitalize()} (<t:{int(parser.isoparse(update['created_at']).timestamp())}{config.embeds['timestamp_format']}>) - {update['id']}",
      value=update["body"][:1024],
      inline=False
    )

  embed.set_footer(text=incident["id"])

  if incident["status"] == "resolved":
    embed.colour = config.embeds["status"]["resolved"]
  elif incident["status"] == "monitoring":
    embed.colour = config.embeds["status"]["monitoring"]
  elif incident["status"] == "identified":
    embed.colour = config.embeds["status"]["identified"]
  elif incident["status"] == "investigating":
    embed.colour = config.embeds["status"]["investigating"]
  else:
    embed.colour = config.embeds["status"]["other"]

  return embed



async def post_status(webhook: Webhook, incident: dict):
  """
    If it is determined that the message doesn't exist, sends a new status update.

    Parameters:
      webhook (Webhook): The webhook to post the status update to.
      incident (dict): The incident to post.
  """

  """
  {
    "id": "wlf7gks7nb1m",
    "name": "Increased API Latency",
    "status": "investigating",
    "created_at": "2024-08-27T13:15:35.796-07:00",
    "updated_at": "2024-08-27T15:01:36.340-07:00",
    "monitoring_at": null,
    "resolved_at": null,
    "impact": "minor",
    "shortlink": "https://stspg.io/ntfpn88g01pl",
    "started_at": "2024-08-27T13:15:35.790-07:00",
    "page_id": "srhpyqt94yxb",
    "incident_updates": [],
    "components": [],
    "reminder_intervals": null
  },
  """

  main.info(f"Posting new status {incident['id']}...")

  main.debug(f"Posting embed for incident {incident['id']}...")
  message = await webhook.send(
    embed=build_embed(incident),
    username=config.webhook["username"],
    avatar_url=config.webhook["avatar_url"],
    wait=True
  )
  main.info(f"Posted new incident {incident['id']} as {message.id}.")
  cache_manager.add_message(incident["id"], message.id, [update["id"] for update in incident["incident_updates"]])



async def edit_missing_statuses(webhook: Webhook, incident):
  """
    Edits a pre-existing message with the missing updates.
    First checks if an edit is needed, then edits the missing updates.

    Parameters:
      webhook (Webhook): The webhook to post the updates to.
      incident (dict): The incident to post the missing updates for.
  """
  status_id = incident["id"]
  missing_updates = cache_manager.get_missing_statuses(status_id, [update["id"] for update in incident["incident_updates"]])

  if missing_updates is None:
    main.warning(f"No cache entry found for status {status_id}.")
    main.warning("Posting new status instead.")
    await post_status(webhook, status_id)
    return

  if len(missing_updates) == 0:
    # Nothing to be done.
    main.debug(f"No missing updates for status {status_id}.")
    return
  
  main.info(f"Editing status {status_id} with missing updates...")
  message = await cache_manager.get_message_for_status(status_id)

  if message is None:
    main.warning(f"Message not found for status {status_id}.")
    main.warning("Posting new status instead.")
    await post_status(webhook, status_id)
    return
  
  main.debug(f"Actually editing message {message.id} for status {status_id}...")
  embed = build_embed(incident)
  await message.edit(embed=embed)

  main.info(f"Edited status {status_id} with missing updates.")
  cache_manager.add_message(status_id, message.id, [update["id"] for update in incident["incident_updates"]])



async def run_webhook():
  """
    Runs the webhook to send the status updates.
  """

  try:
    async with aiohttp.ClientSession() as session:
      webhook = Webhook.from_url(config.webhook["url"], session=session)

      global cache_manager
      cache_manager = cache.CacheManager(path / "cache.json", webhook)
      
      while True:
        incidents = await get_statuses()
        if incidents is None:
          await asyncio.sleep(60)
          continue

        for incident in reversed(incidents):
          # Skip if this incident is older than the max age.
          time = int(parser.isoparse(incident['created_at']).timestamp())

          if int(datetime.now().timestamp()) - time > config.statuses["max_age"]:
            main.debug(f"Skipping incident {incident['id']} as it is older than the max age.")
            continue

          update_ids = []
          for update in incident["incident_updates"]:
            update_ids.append(update["id"])

          incident_id = incident["id"]
          if await cache_manager.get_message_for_status(incident_id):
            await edit_missing_statuses(webhook, incident)
          else:
            await post_status(webhook, incident)

        await asyncio.sleep(60)  

  except Exception as e:
    main.error(f"Failed to run webhook: {e}\n{traceback.format_exc()}")
    return



if __name__ == "__main__":
  main.info("Starting Discord Status webhook...")
  asyncio.run(run_webhook())