from web import app
from flask import render_template, abort
import db_wrapper

@app.route('/', defaults={'user_id': 92155745})
@app.route('/<int:user_id>')
def index(user_id):
    user = db_wrapper.User(user_id)
    vote = user.get_last_vote_for_finished_event()
    if vote is None:
        abort(404)
    event = db_wrapper.Event(vote.event_id)

    full_name = user.name['first_name'] + ' ' + user.name['last_name']
    rating = int(user.rating * 100)
    rating_diff = int((user.rating - user.prev_rating) * 100)
    leaderboard_pos = user.get_leaderbord_index()
    predicted_score = vote.predicted_score
    actual_score = event.score
    team1_name = event.team1.name
    team1_flag = event.team1.flag
    team2_name = event.team2.name
    team2_flag = event.team2.flag

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
                           team2_flag=team2_flag)