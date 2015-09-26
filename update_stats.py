#!/usr/bin/env python

import time
import math
import db_wrapper


def score_weight(predicted_score, true_score):
    p = predicted_score.split(':')
    t = true_score.split(':')
    score_diff = abs(int(p[0]) - int(t[0])) + abs(int(p[1]) - int(t[1]))
    return math.exp(-1.5 * score_diff)


def try_process_event():
    unprocessed_events = db_wrapper.Event.get_unprocessed_events()
    if len(unprocessed_events) == 0:
        print 'No unprocessed events'
        return

    event = unprocessed_events[0]

    print 'Starting score update for event %s' % event.event_id

    votes = event.get_votes()
    weights = [score_weight(votes[i].predicted_score, event.score) for i in range(len(votes))]

    weight_sum = sum(weights) + 1e-6
    normalized_weights = [w / weight_sum for w in weights]

    total_prize = float(len(votes))
    for i in range(len(votes)):
        prize = total_prize * normalized_weights[i]
        user = db_wrapper.User(votes[i].user_id)
        user.update_rating(user.rating + prize)

        print 'User %d updated' % user.telegram_id

    event.set_processed()
    print 'Score update completed for event %s' % event.event_id


def main():
    db_wrapper.init('188.166.85.96', 27017, None, None)

    while True:
        try:
            try_process_event()
        except Exception as e:
            print e
        finally:
            time.sleep(5)


if __name__ == '__main__':
    main()


