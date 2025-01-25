from flask import Flask, render_template
app = Flask(__name__)

import admin

@app.route('/')
def app_introduction():

    return render_template('index.html', person='John Doe')


@app.route('/heatmap')
def heatmap():
    return render_template('heatmap.html')

if __name__ == '__main__':
    app.run()
