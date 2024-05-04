import csv
import time
import asyncio
import config
from utils import cache_info
from riot import RiotAPI, RiotComputer
from embed_generator import champion_name

start_time = time.time()

CONFIG = config.get_config()
api = RiotAPI(CONFIG.RIOT_TOKEN, CONFIG.SERVER,
              CONFIG.REGION, 3)
computer = RiotComputer(api)

puuids = {}

names = ['Im Not From Here#9969', 'koreanman in uk#EUW', 'Reanction14#EUW', 'PhilsyCasual#CCP', 'PunjabPepsi#EUW', 'Alfais#AT1',
         'Syren#UoU', 'femboyheal#gay', 'D0M0V0N#CBT', 'KAPPAMAC#546', 'Strilou#EUW', 'hide on borsch#EUW', 'Wordsbo#EUW', 'VoidRaider53#EUW']

for name in names:
    account = asyncio.run(api.get_riot_account_puuid(*name.split('#')))
    if err := account.error():
        print(name, 'had error:', err)
        exit(1)
    puuids[account.data['puuid']] = name

result = asyncio.run(computer.calculate_champ_breakdown(puuids.keys()))
print('\nCompiled Results:')
for r in result:
    print(f": {puuids.get(r.puuid)} ({champion_name[r.champion_id]})",
          f"- WR {r.winrate() * 100:.2f}%, {r.games()} Games")

with open('temp/computer output.csv', 'w') as f:
    print(': --> All saved to ./temp/computer output.csv')
    writer = csv.writer(f)
    writer.writerow(['puuid', 'summoner', 'champion', 'winrate', 'games'])
    writer.writerows(
        [r.puuid, puuids.get(r.puuid), champion_name[r.champion_id],
         f'{r.winrate() * 100:.2f}%', r.games()]
        for r in result
    )

print('\nCache Info:')
max_len = max(len(f) for f in cache_info.keys()) + 2
for func, info in cache_info.items():
    if info['hits'] == 0 and info['misses'] == 0:
        continue
    print(f": {func}{' ' * (max_len - len(func))}-",
          f"{info['hits']} Hits,\t{info['misses']} Misses")

print(f'\nComputations completed in {time.time() - start_time:.2f} seconds.')
