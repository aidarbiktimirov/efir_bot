#!/usr/bin/env python

import db_wrapper

db_wrapper.init('188.166.85.96', 27017, None, None)

print list(db_wrapper.Event.get_events_with_no_start_notification())
print list(db_wrapper.Event.get_events_with_no_score_notification())