from flask import Flask

app = Flask(__name__)


@app.route('/icanhazip')
def icanhazip():
    return 'Hello, World!'
