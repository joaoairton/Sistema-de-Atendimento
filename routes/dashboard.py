"""
routes/dashboard.py — Rota da pagina inicial.
"""

from flask import Blueprint, render_template
from datetime import date
from config import get_db, get_cursor

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    """Pagina inicial com os 4 contadores em tempo real."""
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
