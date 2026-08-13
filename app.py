from flask import Flask
app=Flask(__name__)
@app.route('/')
def home():
    return 'HELLO ROUTEWISE'

@app.route('/about') #Browser mein URL ke aage /kuch-naam likhkar us specific route pe pahunch sakte ho
def about():
    return'YE MERA PEHLA FLASK PROJECT HAI'
if __name__=='__main__':
    app.run(debug=True)