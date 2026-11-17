import argparse

from dre_network_monitor import NetworkMonitor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help = "Export statistics to a csv file")
    args = parser.parse_args()
    monitor = NetworkMonitor()
    if args.csv:
        count = monitor.export_csv(args.csv)
        print(f"{count} events were analyzed")
    result = monitor.summary()
    print("Network Performance Summary")
    print(
        f"{'Event':<15}"
        f"{'Count':>8}"
        f"{'Upload/Download Speed':>14}"
        f"{'Transfer Time':>14}"
        f"{'Response Time':>14}"
        f"{'Total MB':>14}"
    )

    for row in result:
        event, count, rate, duration, response, total = row

        rate = rate or 0
        duration = duration or 0
        response = response or 0
        total = total or 0

        print(
            f"{event:<15}"
            f"{count:>8}"
            f"{rate:>14.3f}"
            f"{duration:>14.4f}"
            f"{response:>14.3f}"
            f"{total / (1024 * 1024):>14.3f}"
        )


if __name__ == "__main__":
    main()