#!/usr/bin/env python

import db_wrapper

db_wrapper.init('188.166.85.96', 27017, None, None)

print db_wrapper.User(92155745).get_votes()
print db_wrapper.User(92155745).get_last_vote_for_finished_event().predicted_score