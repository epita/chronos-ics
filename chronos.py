#! /usr/bin/env python3

import logging
import argparse
import re
import math
import datetime

import mechanicalsoup
import icalendar


ADE_ROOT = 'http://chronos.epita.net'
ROOM_MAPPING = {}
CLASS_MAPPING = {}
GROUPS = {
    'CSI': ("'trainee'", 1, 13, 15, 17),
    'GISTRE': ("'trainee'", 1, 13, 15, 18),
    'MTI': ("'trainee'", 1, 13, 15, 19),
    'SCIA': ("'trainee'", 1, 13, 15, 20),
    'SIGL': ("'trainee'", 1, 13, 15, 21),
    'SRS': ("'trainee'", 1, 13, 15, 22),
    'TCOM': ("'trainee'", 1, 13, 15, 23),
    'GITM': ("'trainee'", 1, 13, 15, 906),
    'GRA': ("'trainee'", 1, 13, 14, 1057),
    'GRB': ("'trainee'", 1, 13, 14, 1058),
    'APPING1': ("'trainee'", 1, 661, 709),
    'APPING2': ("'trainee'", 1, 661, 710),
    'APPING3': ("'trainee'", 1, 661, 689),
}


def compute_date_base(html, date):
    """
    Computes the Unix timestamp corresponding to the beginning of Chronos'
    week 0 from the result of piano.jsp, assuming there are no missing weeks :)
    """
    if not date:
        return 0

    dates = []
    for tag in html.soup.find_all('img'):
        dates.append(tag.get('alt'))

    maps = []
    for tag in html.soup.find_all('area'):
        m = re.match("javascript:push\((\d+), 'true'\)", tag.get('href'))
        if m.group(1):
            maps.append(m.group(1))

    for i in range(0, len(dates)):
        if dates[i] == date:
            return maps[i]

    return None


def compute_week_number(base, time):
    """
    Computes the Chronos' week number corresponding to a Unix timestamp.
    It needs the base reference to work
    """
    return math.floor((time - base) / (7 * 24 * 60 * 60))


def process_raw_data(items):
    """
    Process a raw class data and make it usable : time parsing, use of room
    and class name matching tables to make them readable and uniform
    """
    # Start date
    d1 = ' '.join(items[0:2])
    result = {
        'start': datetime.datetime.strptime(d1, '%d/%m/%Y %Hh%M'),
        'groups': items[4].split(),
        'prof': items[5],
    }

    # End date
    m = re.match('(\d+)h(?:(\d+)min)?', items[2])
    if m:
        delta = datetime.timedelta(hours=int(m.group(1)))
        if m.group(2):
            delta += datetime.timedelta(minutes=int(m.group(2)))
        result['end'] = result['start'] + delta
    else:
        m = re.match('(\d+)min', items[2])
        if m:
            delta = datetime.timedelta(minutes=int(m.group(1)))
            result['end'] = result['start'] + delta
        else:
            raise Exception('Unhandled duration format')

    # Class name
    if items[3] in CLASS_MAPPING.keys():
        result['name'] = CLASS_MAPPING[items[3]]
    else:
        result['name'] = items[3]

    # Room
    if items[6] in ROOM_MAPPING.keys():
        result['room'] = ROOM_MAPPING[items[6]]
    else:
        result['room'] = items[6]

    return result


def retrieve_class_list(html):
    """
    Retrieve a list of classes from the output of info.jsp (lower pane of the
    timetable display) It only retrieves the time, name of class and room,
    since they are the only really useful ones.
    """
    result = []
    for tr in html.soup.table.find_all('tr'):
        it = []
        for td in tr.find_all('td'):
            txt = td.string
            if txt:
                it.append(txt)
        if it:
            result.append(process_raw_data(it))
    return result


def find_tree_url(soup):
    """
    Find the tree pane URL
    """
    for frame in soup.select('frame'):
        if 'tree.jsp' in frame.get('src'):
            return '{}{}'.format(ADE_ROOT, frame.get('src'))
    return None

def walk_tree(agent, tree, path):
    """
    Walk the tree following the given path, and return the URL at the leaf
    """
    branch_select = 0

    while len(path) > 1:
        # get Tree
        tree_frame = agent.get(tree)
        assert tree_frame.status_code == 200

        found = 0

        if path[0] == "'branch'":
            branch_select = 1
            path = path[1:]
            continue

        for link in tree_frame.soup.find_all('a'):
            m = re.match('javascript:(.*)\(([^,]*),?.*\)', link.get('href'))

            if m.group(2) and m.group(2) == str(path[0]):
                tree = "{}/ade/standard/gui/tree.jsp?".format(ADE_ROOT)
                tree +="expand=false&forceLoad=false&reload=false&scroll=0&"

                if m.group(1) == "openCategory":
                    tree += "category=" + m.group(2)[1:-1]
                if m.group(1) == "openBranch":
                    tree += "branchId={}".format(m.group(2))
                path = path[1:]
                found = 1
                break

        if found == 0:
            return None

    if path[0]:
        selector = "selectId"
        if branch_select:
            selector = "selectBranchId"
        r = "{}/ade/standard/gui/tree.jsp?".format(ADE_ROOT)
        r += "{}={}&forceLoad=false&scroll=0".format(selector, path[0])
        return r
    else:
        raise Exception("Can't get calendar")


def connect_and_select(agent, date, path):
    """
    Connect to Chronos and select a node (given by its path), retrieve the time
    base and return it.
    """
    main_page = agent.get("{}/".format(ADE_ROOT))
    assert main_page.status_code == 200

    # Find the tree
    tree = find_tree_url(main_page.soup)
    assert tree != None

    # Find the leaf following the given path
    leaf = walk_tree(agent, tree, path)
    assert leaf != None

    # Access the leaf
    leaf_page = agent.get(leaf)
    assert leaf_page.status_code == 200

    # Get the time bar
    uri = "{}/ade/custom/modules/plannings/pianoWeeks.jsp".format(ADE_ROOT)
    time_bar = agent.get(uri)
    assert time_bar.status_code == 200

    # Return the computed week origin
    return compute_date_base(time_bar, date)


def retrieve_week_classes(agent, first, numweeks):
    """
    Retrieve the classes of a week given a Unix timestamp in this week.
    """
    # Set the weeks
    for i in range(0, numweeks):
        uri = "{}/ade/custom/modules/plannings/bounds.jsp?".format(ADE_ROOT)
        uri += "week={}".format(i + first)
        if i == 0:
            uri += "&reset=true"
        page = agent.get(uri)
        assert page.status_code == 200

    # Retrieve the content and parse it
    page = agent.get("{}/ade/custom/modules/plannings/info.jsp".format(ADE_ROOT))
    assert page.status_code == 200

    return retrieve_class_list(page)


def display_time_ical(dt=datetime.datetime.now()):
    """
    Display time in the iCal format
    """
    return dt.strftime('%Y%m%dT%H%M%S')


def ical_output(promo, group, date, classes):
    cal = icalendar.Calendar()
    cal.add('VERSION', '2.0')
    cal.add('PRODID', '-//Laboratoire Assistant <acu\@acu.epita.fr>//chronos.py//EN')

    for c in classes:
        event = icalendar.Event()

        event_condensed_name = '{}-{}'.format(c.get('name'), c.get('prof'))
        event_condensed_name = re.sub(r"[^\w]", "_", event_condensed_name)
        event['UID'] = 'chronos-{}-{}-{}'.format(
            promo, c.get('start'), event_condensed_name).replace(' ', '_')

        # date the event was created (reset to now)
        event['DTSTAMP'] = '{}'.format(display_time_ical())

        summary = '{}'.format(c.get('name'))
        if c.get('prof') != '-':
            summary += ' - {}'.format(c.get('prof'))
        summary += ' ({})'.format(c.get('room'))
        event['SUMMARY;CHARSET=UTF-8'] = '{}'.format(summary)

        description = "Cours: {}\\nProf: {}\\nSalle: {}\\nGroupes: {}".format(
            c.get('name'), c.get('prof'), c.get('room'),
            '-'.join(c.get('groups')))
        event['DESCRIPTION'] = description.replace(',', '\\,')
        event['DTSTART;TZID=Europe/Paris'] = display_time_ical(c.get('start'))
        event['DTEND;TZID=Europe/Paris'] = display_time_ical(c.get('end'))
        event['LOCATION:'] = c.get('room')
        cal.add_component(event)

    return cal


def chronos(promo, group, numweeks):
    agent = mechanicalsoup.Browser()
    try:
        path = GROUPS[group]
    except:
        logging.fatal("Can't find path for this calendar: {}".format(group))
        exit(2)
    first = connect_and_select(agent, None, path)
    classes = retrieve_week_classes(agent, first, numweeks)
    return ical_output(promo, group, None, classes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-promo")
    parser.add_argument("-group")
    parser.add_argument("-numweeks", type=int)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    cal = chronos(promo=args.promo, group=args.group, numweeks=args.numweeks)
    print(cal.to_ical().decode())
