# app.py — Entrega 3 | Porta 5002
from flask import Flask, render_template
import config
from routes.pacientes    import pac_bp
from routes.atendimentos import atend_bp
from routes.prescricoes  import pres_bp
from routes.integracao   import integ_bp

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

app.register_blueprint(pac_bp)
app.register_blueprint(atend_bp)
app.register_blueprint(pres_bp)
app.register_blueprint(integ_bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
