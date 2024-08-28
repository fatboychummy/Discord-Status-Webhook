from dataclasses import dataclass
from discord.webhook import Webhook, WebhookMessage
from typing import List, Dict, Union
import json
import logging
import traceback

log = logging.getLogger("dsw.cache")

@dataclass
class CacheEntry:
  """
    One entry in the cache.

    Attributes:
      id: str
        The status id.
      message_id: str
        The message id.
      update_ids: List[str]
        The update ids.
  """
  id: str
  message_id: int
  update_ids: List[str]

Cache = Dict[str, CacheEntry] # A dictionary mapping status ids to CacheEntry objects.



class CacheManager:
  """
    Manages the cache of the status update messages that the webhook has sent.
  """

  def __init__(self, path: str, webhook: Webhook):
    """
      Initializes the cache manager.

      Parameters:
        path (str): The path to the cache file.
        webhook (Webhook): The webhook to use.
    """

    self.path = path
    self.cache = self.get_cache()
    self.webhook = webhook
  


  def get_cache(self) -> Cache:
    """
      Gets the cache of the status update messages that the webhook has sent.

      Returns:
        Cache: A dictionary mapping status ids to CacheEntry objects.
    """

    try:
      with open(self.path, "r") as file:
        data = json.load(file)

        return {entry["id"]: CacheEntry(**entry) for entry in data}
    except FileNotFoundError:
      log.warning("Cache file not found.")
      return {}
    except json.JSONDecodeError as e:
      log.error(f"Failed to decode cache file: {e}\n{traceback.format_exc()}")
      return {}
    except Exception as e:
      log.error(f"Failed to get cache: {e}\n{traceback.format_exc()}")
      return {}
  


  def save_cache(self):
    """
      Saves the cache of the status update messages that the webhook has sent.
    """

    try:
      with open(self.path, "w") as file:
        json.dump([entry.__dict__ for entry in self.cache.values()], file, indent=2)
    except Exception as e:
      log.error(f"Failed to save cache: {e}\n{traceback.format_exc()}")
      return
    


  async def get_message(self, message_id: str) -> WebhookMessage:
    """
      Gets a message from a webhook.

      Parameters:
        message_id (str): The message id to get.

      Returns:
        WebhookMessage: The message.
    """

    try:
      log.debug(f"Getting message {message_id}...")
      return await self.webhook.fetch_message(message_id)
    except Exception as e:
      log.error(f"Failed to get message {message_id}: {e}\n{traceback.format_exc()}")
      return None



  async def get_message_for_status(self, status_id: str) -> Union[WebhookMessage, None]:
    """
      Gets the message for a status id.

      Parameters:
        status_id (str): The status id to get the message for.

      Returns:
        WebhookMessage: The message if found in the cache.
        None: If the message is not found in the cache.
    """

    log.debug(f"Getting message for status {status_id}...")
    cache_entry = self.cache.get(status_id)
    if cache_entry is None:
      log.debug(f"Cache entry not found for status {status_id}.")
      return None

    log.debug(f"Cache entry found for status {status_id}.")
    return await self.get_message(cache_entry.message_id)



  def add_message(self, status_id: str, message_id: int, update_ids: List[str]):
    """
      Adds (or updates) a message to the cache.

      Parameters:
        status_id (str): The status id.
        message_id (int): The message id.
        update_ids (List[str]): The update ids.
    """

    log.debug(f"Adding message {message_id} to cache...")
    self.cache[status_id] = CacheEntry(status_id, message_id, update_ids)
    self.save_cache()
  


  def parse_message(self, entry_id: str):
    """
      Determines which updates have been sent in an embed.

      Parameters:
        entry_id (str): The entry id to parse the message
        message (WebhookMessage): The message to parse.
    """

    log.debug(f"Parsing message {entry_id}...")
    message = self.get_message_for_status(entry_id)

    if message is None:
      log.warning(f"Message {entry_id} not found.")
      return

    update_ids = []
    embed = message.embeds[0]

    for field in embed.fields:
      # The name of the field is not just the update ID, but has the format:
      # "Status (<timestamp>) - <update_id>"
      # Thus, we need to split it by " - " and get the last element.
      update_id = field.name.split(" - ")[-1]
      update_ids.append(update_id)
    
    self.cache[entry_id].update_ids = update_ids



  async def parse_messages(self):
    """
      Parses all the messages in the cache.
    """

    log.info("Parsing all messages...")
    for entry_id, entry in self.cache.items():
      self.parse_message(entry_id)



  def get_missing_statuses(self, status_id: str, update_ids: List[str]) -> List[str]:
    """
      Gets the missing updates for a status id (if any).

      Parameters:
        status_id (str): The status id to get the missing updates for.
        update_ids (List[str]): The update ids that have been sent.
      
      Returns:
        List[str]: The missing update ids.
        None: If the cache entry is not found.
    """

    cache_entry = self.cache.get(status_id)
    if cache_entry is None:
      return None
    
    missing_updates = []

    for update_id in update_ids:
      if update_id not in cache_entry.update_ids:
        missing_updates.append(update_id)
    
    return missing_updates