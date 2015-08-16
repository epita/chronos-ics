#! /usr/bin/env python3

import os
import time
import flask


app = flask.Flask(__name__)


@app.route('/')
@app.route('/calendars/')
def index():
    groups = [
        {'title': 'Groups', 'cals': ["GRA", "GRB", "APPING1", "APPING2", "APPING3"]},
        {'title': 'Major', 'cals': ["CSI", "MTI", "GISTRE", "SRS", "SIGL", "SCIA", "TCOM", "GITM"]},
    ]
    for group in groups:
        group['cals'] = map(lambda x: (x, time.ctime(os.path.getmtime('calendars/{}.ics'.format(x)))), group['cals'])
    return flask.render_template('index.html', groups=groups)


@app.route('/calendars/<name>')
def send_calendar(name):
    return flask.send_from_directory('calendars', name)


if __name__ == '__main__':
    app.run(debug=True)
__author__ = 'satreix'
