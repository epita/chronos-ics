# Chronos ICS

[![Build Status](https://travis-ci.org/epita/chronos-ics.svg?branch=master)](https://travis-ci.org/epita/chronos-ics)
[![Requirements Status](https://requires.io/github/epita/chronos-ics/requirements.svg?branch=master)](https://requires.io/github/epita/chronos-ics/requirements/?branch=master)

Provide ICS files for students @ EPITA (http://chronos.epita.net/).

Our school happens to use ADE Entreprise to advertise students schedules. It is usable but tedious to use as is. This project scraps its web pages and creates the calendar files that can be exposed to students and used to back Google Calendar, Apple iCal and so on.

## Install

```
pip install -r requirements.txt
```
## Run

- generate the calendars and the index file using `cron.py`;
- `cp` generated files to a path served by your reverse proxy as static files.
