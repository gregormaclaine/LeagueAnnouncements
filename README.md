# League of Legends Discord bot

A Discord bot that allows you to track your own League of Legends accounts and announces to the server when you have made a particular achievement, such as losing 3 or more games in a row or getting a KDA < 1.

## Usage

After adding the bot to your server, first run `/set_channel` and choose where you want the announcements to be sent to. You can find the channel ID by right-clicking on a channel when you have Discord developer settings switched on.

Then use the `/track` command to start tracking your League summoner profiles. From now, when you make an achievement, the bot will send a message to your chosen channel.

If you want to be pinged when it makes an announcement related to you, use the `/claim_profile` command to link your discord name to the profile. To find the index of the profile, you can call the `/list` command.

## List of Commands

```
/profile {player} {tag} - See your rank, mastery and favourite champs
/track {player} {tag} - Begin tracking achievements of this player
/untrack {index} - Stop tracking the player at this index in the list
/list {offset} - List all tracked players (15 at a time)

/claim_profile {index} - Links discord account to tracked player (Pings you when announcements involve you)
/unclaim_profile {index} - Unlinks discord account from tracked player
/who_claims {index} - Get list of users who have claimed an account

/set_channel {channel} {silent=false} - Set channel to which the announcements will be sent
/run_checks - Manually check for new announcements (This is done automatically every 5 minutes)

```

### Dev Commands

```
/track_many {users} - Bulk track multiple users (player#tag,player2#tag2...)

/autochecker status - Get information about the automatic checker
/autochecker pause - Pauses the automatic checker
/autochecker unpause - Unpauses the automatic checker
/autochecker start - Restarts the checker if it has shutdown due to an error
```

## Running The Bot

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

### Hosting

I recommend using [Railway.app](https://railway.app/) to host the bot, as the bot uses very little resources so easily fits into their generous trial tier. The configuration for persistent storage is already set up to be used with Railway Volume storage, but does also work for other generic hosting platforms.

## Disclaimer

This bot is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
