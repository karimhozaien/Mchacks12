from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/hello')
def hello():
    return jsonify({'message': 'Hello from Flask! (This is a response from the backend 11111)'})


@app.route('/api/bye')
def hello_name():
    return jsonify({'message': 'Bye from Flask! (This is a response from the backend 11111)'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)
