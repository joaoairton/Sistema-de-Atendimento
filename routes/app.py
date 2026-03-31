# app.py
# Ponto de entrada da aplicação.
# Responsabilidade única: criar o app Flask, registrar os blueprints e iniciar.

from flask import Flask, render_template
from app.config import SECRET_KEY
from routes.pacientes    import pacientes_bp
from routes.atendimentos import atendimentos_bp
from routes.prescricoes  import prescricoes_bp
from routes.exportacao   import exportacao_bp
from routes.api          import api_bp
from routes.importacao    import importacao_bp

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Registra todos os módulos de rota
app.register_blueprint(pacientes_bp)
app.register_blueprint(atendimentos_bp)
app.register_blueprint(prescricoes_bp)
app.register_blueprint(exportacao_bp)
app.register_blueprint(api_bp)
app.register_blueprint(importacao_bp)


# Dashboard — mantido aqui por ser a rota raiz
from datetime import date
from app.config import get_db, get_cursor

@app.route("/")
def index():
    db  = get_db()
    cur = get_cursor(db)
    try:
        cur.execute("SELECT COUNT(*) FROM paciente")
        total_pacientes = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM atendimento WHERE status = 'ABERTO'")
        total_abertos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM atendimento WHERE data_abertura = CURRENT_DATE")
        total_hoje = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM prescricao WHERE data_prescricao = CURRENT_DATE")
        total_prescricoes = cur.fetchone()[0]
    finally:
        cur.close(); db.close()

    return render_template("index.html",
        total_pacientes=total_pacientes,
        total_abertos=total_abertos,
        total_hoje=total_hoje,
        total_prescricoes=total_prescricoes)


if __name__ == "__main__":
    # debug=True apenas em desenvolvimento local
    app.run(debug=True, port=5001)
