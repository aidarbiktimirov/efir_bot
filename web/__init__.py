from flask import Flask
app = Flask(__name__)

import db_wrapper
db_wrapper.init('188.166.85.96', 27017, None, None)

from web import views