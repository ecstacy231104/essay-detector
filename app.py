from flask import Flask, render_template, request
from detector import analyze

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    essay_text = ""
    if request.method == "POST":
        essay_text = request.form.get("essay", "")
        if essay_text.strip():
            result = analyze(essay_text)
    return render_template("index.html", result=result, essay_text=essay_text)


if __name__ == "__main__":
    app.run(debug=False, port=5000)