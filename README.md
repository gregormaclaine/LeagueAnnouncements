# League of Legends Discord bot

A Discord bot that allows you to track your own League of Legends accounts and announces to the server when you have made a particular achievement, such as losing 3 or more games in a row or getting a KDA < 1.

## List of commands:

```
/profile {player} {tag} - See your rank, mastery and favourite champs
/track {player} {tag} - Begin tracking achievements of this player
/untrack {index} - Stop tracking the player at this index in the list
/list {offset} - List all tracked players (15 at a time)

/claim_profile {index} - Links discord account to tracked player (Pings you when announcements involve you)
/unclaim_profile {index} - Unlinks discord account from tracked player

/set_channel {channel} {silent=false} - Set channel to which the announcements will be sent
/run_checks - Manually check for new announcements (This is done automatically every 5 minutes)

```

### Dev commands:

```
/track_many {users} - Bulk track multiple users (player#tag,player2#tag2...)

/autochecker status - Get information about the automatic checker
/autochecker pause - Pauses the automatic checker
/autochecker unpause - Unpauses the automatic checker
/autochecker start - Restarts the checker if it has shutdown due to an error
```

## Running the bot:

Your can run this bot using Docker

```bash
docker compose up -d
```

or local Python interpreter

```bash
pip install -r requirements.txt
python ./src/main.py
```

`.env` file should be located in the root directory. Alternatively, you can use shell environment variables.
