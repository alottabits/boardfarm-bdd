#!/bin/sh
# Application Response Time endpoint — reflects request timestamp
# Used by QoEClient.measure_productivity() for TTFB measurement
printf "Content-Type: application/json\r\n\r\n"
python3 -c "import time; print('{\"timestamp\":' + str(int(time.time()*1000)) + '}')"
