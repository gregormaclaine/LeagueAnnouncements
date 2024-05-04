import sys
import time

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('🔴 No script specified.')
        exit(1)

    script = sys.argv[1]
    start_time = time.time()

    if script == 'list':
        print('Available Scripts:')
        print(' - list')
        print(' - winrate')
    elif script == 'winrate':
        import scripts.build_winrate_breakdown
    else:
        print('🔴 Unknown script')
        exit(1)

    print(f'\n🟢 Script completed in {
          time.time() - start_time:.2f} seconds.')
    exit(0)
