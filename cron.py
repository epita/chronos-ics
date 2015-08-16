#! /usr/bin/env python3

import os
import datetime
import logging
import concurrent.futures

from chronos import chronos


STUDENT_PROM = 2018
ASSISTANT_PROM = STUDENT_PROM - 2
CALDIR = 'calendars'
NUMWEEKS = 80


def get_calendar(promo, group):
    output = '{}/{}'.format(CALDIR, group)
    cal = chronos(promo, group, NUMWEEKS)
    with open('{}.ics'.format(output), 'wb') as out:
        out.write(cal.to_ical())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if not os.path.isdir(CALDIR):
        os.mkdir(CALDIR)
    logging.info("Doing update")
    logging.info(datetime.datetime.now().isoformat())

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for i in 'CSI GISTRE MTI SCIA SIGL SRS TCOM GITM'.split():
            executor.submit(get_calendar, ASSISTANT_PROM, i)

        for i in 'GRA GRB APPING1 APPING2 APPING3'.split():
            executor.submit(get_calendar, STUDENT_PROM, i)
