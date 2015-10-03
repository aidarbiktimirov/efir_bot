from web import app
from flask import render_template, abort
import db_wrapper

def rating_to_show(rating):
    return int(rating * 100)

def get_full_name(user):
    first_name = user.name['first_name']
    last_name = user.name['last_name']
    if first_name is None and last_name is None:
        return 'Unknown'
    if first_name is None:
        return last_name
    if last_name is None:
        return first_name
    return first_name + ' ' + last_name

class LeaderboardUserInfo:
    def __init__(self, user, position):
        self.user = user
        self.position = position
        self.rating = rating_to_show(user.rating)
        self.name = get_full_name(user)

@app.route('/')
def leaderboard():
    page_num = 0
    page_size = 100
    leaderboard = db_wrapper.User.get_top((page_num + 1) * page_size)[page_num * page_size:]
    if not leaderboard:
        abort(404)
    leaderboard_user_info = [LeaderboardUserInfo(leaderboard[i], i+1) for i in range(len(leaderboard))]
    return render_template('leaderboard.html', leaderboard=leaderboard_user_info)

@app.route('/<int:user_id>')
def index(user_id):
    user = db_wrapper.User(user_id)
    vote = user.get_last_vote_for_finished_event()
    event = db_wrapper.Event(vote.event_id)
    next_events = db_wrapper.Event.get_upcoming_events()
    next_event = next_events[0] if len(next_events) > 0 else None
    if vote is None or next_event is None:
        abort(404)

    full_name = get_full_name(user)
    rating = int(user.rating * 100)
    rating_diff = int((user.rating - user.prev_rating) * 100)
    leaderboard_pos = user.get_leaderbord_index()
    predicted_score = vote.predicted_score
    actual_score = event.score
    team1_name = event.team1.name
    team1_flag = event.team1.flag
    team2_name = event.team2.name
    team2_flag = event.team2.flag
    next_event_team1_name = next_event.team1.name
    next_event_team1_flag = next_event.team1.flag
    next_event_team2_name = next_event.team2.name
    next_event_team2_flag = next_event.team2.flag

    date_format = '%B %-d, %Y'
    event_date = event.vote_until.strftime(date_format)
    next_event_date = next_event.vote_until.strftime(date_format)

    p = predicted_score.split(':')
    t = actual_score.split(':')
    score_diff = abs(int(p[0]) - int(t[0])) + abs(int(p[1]) - int(t[1]))
    status_line = 'I knew it!' if score_diff == 0 else 'Almost got it!' if score_diff == 1 else 'Hope I\'ll do better next time!'

    return render_template('index.html',
                           name=full_name,
                           rating=rating,
                           rating_diff=rating_diff,
                           leaderboard_pos=leaderboard_pos,
                           leaderboard_size=db_wrapper.User.count(),
                           predicted_score=predicted_score,
                           actual_score=actual_score,
                           team1_name=team1_name,
                           team1_flag=team1_flag,
                           team2_name=team2_name,
                           team2_flag=team2_flag,
                           next_event_team1_name=next_event_team1_name,
                           next_event_team1_flag=next_event_team1_flag,
                           next_event_team2_name=next_event_team2_name,
                           next_event_team2_flag=next_event_team2_flag,
                           event_date=event_date,
                           next_event_date=next_event_date,
                           status_line=status_line)