#! /usr/bin/env python3

import os
import datetime
import concurrent.futures
import time

import jinja2

import chronos


def get_year():
    y = datetime.datetime.now().year
    return y + 2 if datetime.datetime.now().month < 7 else y + 3


STUDENT_PROM = get_year()
ASSISTANT_PROM = STUDENT_PROM - 2
OUTPUT = 'build'
CALDIR = os.path.join(OUTPUT, 'calendars')
NUMWEEKS = 80

GROUPS = ["GRA", "GRB", "APPING1", "APPING2", "APPING3"]
MAJORS = ["CSI", "MTI", "GISTRE", "SRS", "SIGL", "SCIA", "TCOM", "GITM"]


def get_calendar(promo, group):
    output = '{}/{}'.format(CALDIR, group)
    cal = chronos.chronos(promo, group, NUMWEEKS)
    with open('{}.ics'.format(output), 'wb') as out:
        out.write(cal.to_ical())


def update_index():
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
    template = env.get_template('index.html')

    groups = [
        {'title': 'Groups', 'cals': GROUPS},
        {'title': 'Major', 'cals': MAJORS},
    ]
    for group in groups:
        group['cals'] = map(lambda x: (x, time.ctime(
            os.path.getmtime('{}/{}.ics'.format(CALDIR, x)))), group['cals'])

    output = template.render(groups=groups)
    with open(os.path.join(OUTPUT, "index.html"), "w") as f:
        f.write(output)


if __name__ == '__main__':
    for d in [OUTPUT, CALDIR]:
        if not os.path.isdir(d):
            os.mkdir(d)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for i in MAJORS:
            executor.submit(get_calendar, ASSISTANT_PROM, i)
        for i in GROUPS:
            executor.submit(get_calendar, STUDENT_PROM, i)

    update_index()
