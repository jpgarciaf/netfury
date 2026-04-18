"""
NetFury Web Dashboard - Punto de entrada principal.

Aplicacion Flask que muestra los resultados del
analisis de precios de ISPs.
"""

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    """Pagina principal del dashboard."""
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
