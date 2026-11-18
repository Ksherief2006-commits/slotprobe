# slotprobe

7-day measurement of public Trusted Traveler slot-endpoint availability from a cloud runner. Read-only, 1 request/sec, 12 locations every 10 min. Sends no messages. Results go to the data branch as data.csv; summarize with python3 summarize.py data.csv. Not affiliated with CBP.
