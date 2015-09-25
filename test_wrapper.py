#!/usr/bin/env python

import db_wrapper

db_wrapper.init('188.166.85.96', 27017, None, None)

print db_wrapper.User(31337).get_leaderbord_index()
print db_wrapper.User(31338).get_leaderbord_index()