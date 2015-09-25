#!/usr/bin/env python

import db_wrapper

db_wrapper.init('188.166.85.96', 27017, None, None)

for event in db_wrapper.Event.get_all():
    print event.name