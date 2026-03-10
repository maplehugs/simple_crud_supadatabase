import os
from html import escape

from dotenv import load_dotenv
from flask import Flask, redirect, request, url_for
from supabase import Client, create_client

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _db() -> Client:
    if not supabase:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_KEY en el entorno.")
    return supabase


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _render_page(todos: list[dict], error: str = "") -> str:
    html = "<h1>Todos</h1>"
    if error:
        html += f"<p>{escape(error)}</p>"

    html += """
    <form method='post' action='/todos/create'>
      <input type='text' name='name' placeholder='Nueva tarea' required>
      <button type='submit'>Agregar</button>
    </form>
    <hr>
    <ul>
    """

    for todo in todos:
        todo_id = todo["id"]
        name = escape(todo.get("name", ""))
        completed = bool(todo.get("completed", False))
        created_at = escape(str(todo.get("created_at", "")))
        checked = "checked" if completed else ""
        completed_label = "Hecha" if completed else "Pendiente"

        html += f"""
        <li>
          <form method='post' action='/todos/{todo_id}/toggle' style='display:inline;'>
            <input type='hidden' name='completed' value='{str(completed).lower()}'>
            <button type='submit'>Cambiar estado</button>
          </form>
          <input type='checkbox' disabled {checked}> {completed_label}

          <form method='post' action='/todos/{todo_id}/update' style='display:inline;'>
            <input type='text' name='name' value='{name}' required>
            <button type='submit'>Guardar</button>
          </form>

          <form method='post' action='/todos/{todo_id}/delete' style='display:inline;' onsubmit='return confirm("Eliminar tarea?")'>
            <button type='submit'>Eliminar</button>
          </form>
          <small>creada: {created_at}</small>
        </li>
        """

    html += "</ul>"
    return html


@app.route("/")
def index():
    error = request.args.get("error", "")
    try:
        response = _db().table("todos").select("*").order("created_at", desc=True).execute()
        todos = response.data or []
    except Exception as exc:  # pragma: no cover
        todos = []
        if not error:
            error = f"No se pudo leer la base de datos: {exc}"

    return _render_page(todos, error)


@app.post("/todos/create")
def create_todo():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("index", error="El nombre no puede estar vacio"))

    try:
        _db().table("todos").insert({"name": name, "completed": False}).execute()
    except Exception as exc:  # pragma: no cover
        return redirect(url_for("index", error=f"Error creando tarea: {exc}"))

    return redirect(url_for("index"))


@app.post("/todos/<int:todo_id>/update")
def update_todo(todo_id: int):
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("index", error="El nombre no puede estar vacio"))

    try:
        _db().table("todos").update({"name": name}).eq("id", todo_id).execute()
    except Exception as exc:  # pragma: no cover
        return redirect(url_for("index", error=f"Error actualizando tarea: {exc}"))

    return redirect(url_for("index"))


@app.post("/todos/<int:todo_id>/toggle")
def toggle_todo(todo_id: int):
    current_completed = _to_bool(request.form.get("completed", "false"))

    try:
        _db().table("todos").update({"completed": not current_completed}).eq("id", todo_id).execute()
    except Exception as exc:  # pragma: no cover
        return redirect(url_for("index", error=f"Error cambiando estado: {exc}"))

    return redirect(url_for("index"))


@app.post("/todos/<int:todo_id>/delete")
def delete_todo(todo_id: int):
    try:
        _db().table("todos").delete().eq("id", todo_id).execute()
    except Exception as exc:  # pragma: no cover
        return redirect(url_for("index", error=f"Error eliminando tarea: {exc}"))

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
