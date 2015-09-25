#!/usr/bin/env python

import db_wrapper

db_wrapper.init('188.166.85.96', 27017, None, None)

for u in db_wrapper.User.get_top(2):
    print '%s\t%f' % (u.telegram_id, u.rating)