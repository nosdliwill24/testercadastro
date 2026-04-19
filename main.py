import sqlite3
import hashlib
import os
import secrets
from datetime import datetime
from nicegui import ui, app

# ─── Banco de dados ────────────────────────────────────────────────────────────

DB_PATH = os.environ.get("DB_PATH", "users.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT    UNIQUE NOT NULL,
                email     TEXT    UNIQUE NOT NULL,
                password  TEXT    NOT NULL,
                created_at TEXT   DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

# ─── Helpers de auth ───────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False

def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    if len(username) < 3:
        return False, "Nome de usuário muito curto (mínimo 3 caracteres)."
    if len(password) < 6:
        return False, "Senha muito curta (mínimo 6 caracteres)."
    if "@" not in email:
        return False, "E-mail inválido."
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username.strip(), email.strip().lower(), hash_password(password)),
            )
            conn.commit()
        return True, "Conta criada com sucesso!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Nome de usuário já em uso."
        return False, "E-mail já cadastrado."

def login_user(email: str, password: str) -> tuple[bool, dict | str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    if not row:
        return False, "E-mail não encontrado."
    if not verify_password(password, row["password"]):
        return False, "Senha incorreta."
    return True, dict(row)

def get_user_notes(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def add_note(user_id: int, content: str):
    with get_db() as conn:
        conn.execute("INSERT INTO notes (user_id, content) VALUES (?, ?)", (user_id, content))
        conn.commit()

def delete_note(note_id: int, user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        conn.commit()

# ─── Estilo global ─────────────────────────────────────────────────────────────

STYLE = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

* { box-sizing: border-box; }

body {
    margin: 0;
    font-family: 'DM Sans', sans-serif;
    background: #0f1117;
    color: #e8eaf0;
    min-height: 100vh;
}

.auth-card {
    background: #1a1d27;
    border: 1px solid #2a2d3a;
    border-radius: 16px;
    padding: 40px;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.5);
}

.brand-title {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: #fff;
    margin: 0 0 4px 0;
}

.brand-sub {
    font-size: 14px;
    color: #666980;
    margin: 0 0 32px 0;
}

.field-label {
    font-size: 13px;
    font-weight: 500;
    color: #9395a5;
    margin-bottom: 6px;
    display: block;
}

.nicegui-input .q-field__control {
    background: #0f1117 !important;
    border: 1px solid #2a2d3a !important;
    border-radius: 10px !important;
    color: #e8eaf0 !important;
}

.nicegui-input .q-field__control:hover {
    border-color: #4f52d3 !important;
}

.btn-primary {
    background: #4f52d3 !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    height: 48px !important;
    letter-spacing: 0.2px;
    transition: background 0.2s;
    width: 100%;
}

.btn-primary:hover {
    background: #3d40b5 !important;
}

.link-btn {
    color: #7b7ef5 !important;
    font-size: 13px !important;
    text-decoration: none;
    cursor: pointer;
}

.link-btn:hover { color: #a0a3ff !important; }

.divider-line {
    border: none;
    border-top: 1px solid #2a2d3a;
    margin: 20px 0;
}

/* Dashboard */
.dash-sidebar {
    width: 240px;
    background: #1a1d27;
    border-right: 1px solid #2a2d3a;
    min-height: 100vh;
    padding: 24px 16px;
}

.dash-content {
    flex: 1;
    padding: 32px;
    overflow-y: auto;
}

.dash-title {
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    margin: 0;
}

.stat-card {
    background: #1a1d27;
    border: 1px solid #2a2d3a;
    border-radius: 12px;
    padding: 20px 24px;
}

.stat-label {
    font-size: 12px;
    font-weight: 500;
    color: #666980;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stat-value {
    font-size: 32px;
    font-weight: 700;
    color: #fff;
    font-family: 'DM Mono', monospace;
}

.note-item {
    background: #1a1d27;
    border: 1px solid #2a2d3a;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}

.note-item:hover { border-color: #4f52d3; }

.nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: #9395a5;
    transition: all 0.15s;
    text-decoration: none;
    width: 100%;
}

.nav-item:hover {
    background: #252836;
    color: #e8eaf0;
}

.nav-item.active {
    background: #252836;
    color: #7b7ef5;
}

.chip-accent {
    background: rgba(79, 82, 211, 0.15);
    color: #7b7ef5;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 600;
}

.error-msg {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #f87171;
}

.success-msg {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #4ade80;
}
"""

# ─── Página de Login ────────────────────────────────────────────────────────────

@ui.page("/")
def page_login():
    ui.add_head_html(f"<style>{STYLE}</style>")

    # Redireciona se já logado
    user = app.storage.user.get("user")
    if user:
        ui.navigate.to("/dashboard")
        return

    with ui.column().classes("items-center justify-center").style("min-height:100vh; width:100%"):
        with ui.element("div").classes("auth-card"):

            # Brand
            ui.html('<p class="brand-title">👤  AuthApp</p>')
            ui.html('<p class="brand-sub">Entre na sua conta para continuar</p>')

            msg_area = ui.column().style("width:100%; margin-bottom:12px")

            def show_msg(text, tipo="error"):
                msg_area.clear()
                with msg_area:
                    ui.html(f'<div class="{tipo}-msg">{text}</div>')

            # Campos
            ui.html('<span class="field-label">E-mail</span>')
            email_input = ui.input(placeholder="seu@email.com").props(
                'type=email outlined dense'
            ).classes("nicegui-input w-full").style("margin-bottom:16px")

            ui.html('<span class="field-label">Senha</span>')
            password_input = ui.input(placeholder="••••••••").props(
                'type=password outlined dense'
            ).classes("nicegui-input w-full").style("margin-bottom:24px")

            def do_login():
                ok, result = login_user(email_input.value, password_input.value)
                if ok:
                    app.storage.user["user"] = result
                    ui.navigate.to("/dashboard")
                else:
                    show_msg(result)

            password_input.on("keydown.enter", do_login)

            ui.button("Entrar", on_click=do_login).classes("btn-primary")

            ui.html('<hr class="divider-line">')

            with ui.row().classes("justify-center items-center gap-1"):
                ui.html('<span style="font-size:13px; color:#666980">Não tem conta?</span>')
                ui.link("Cadastre-se", "/register").classes("link-btn")


# ─── Página de Cadastro ─────────────────────────────────────────────────────────

@ui.page("/register")
def page_register():
    ui.add_head_html(f"<style>{STYLE}</style>")

    user = app.storage.user.get("user")
    if user:
        ui.navigate.to("/dashboard")
        return

    with ui.column().classes("items-center justify-center").style("min-height:100vh; width:100%"):
        with ui.element("div").classes("auth-card"):

            ui.html('<p class="brand-title">✨  Criar Conta</p>')
            ui.html('<p class="brand-sub">Preencha os dados para se cadastrar</p>')

            msg_area = ui.column().style("width:100%; margin-bottom:12px")

            def show_msg(text, tipo="error"):
                msg_area.clear()
                with msg_area:
                    ui.html(f'<div class="{tipo}-msg">{text}</div>')

            ui.html('<span class="field-label">Nome de usuário</span>')
            username_input = ui.input(placeholder="seunome").props(
                'outlined dense'
            ).classes("nicegui-input w-full").style("margin-bottom:16px")

            ui.html('<span class="field-label">E-mail</span>')
            email_input = ui.input(placeholder="seu@email.com").props(
                'type=email outlined dense'
            ).classes("nicegui-input w-full").style("margin-bottom:16px")

            ui.html('<span class="field-label">Senha</span>')
            password_input = ui.input(placeholder="Mínimo 6 caracteres").props(
                'type=password outlined dense'
            ).classes("nicegui-input w-full").style("margin-bottom:24px")

            def do_register():
                ok, msg = register_user(
                    username_input.value,
                    email_input.value,
                    password_input.value,
                )
                if ok:
                    show_msg(msg, "success")
                    ui.timer(1.5, lambda: ui.navigate.to("/"), once=True)
                else:
                    show_msg(msg)

            ui.button("Criar conta", on_click=do_register).classes("btn-primary")

            ui.html('<hr class="divider-line">')

            with ui.row().classes("justify-center items-center gap-1"):
                ui.html('<span style="font-size:13px; color:#666980">Já tem conta?</span>')
                ui.link("Faça login", "/").classes("link-btn")


# ─── Dashboard (app protegido) ──────────────────────────────────────────────────

@ui.page("/dashboard")
def page_dashboard():
    ui.add_head_html(f"<style>{STYLE}</style>")

    user = app.storage.user.get("user")
    if not user:
        ui.navigate.to("/")
        return

    user_id = user["id"]
    username = user["username"]
    created_at = user.get("created_at", "")[:10]

    def do_logout():
        app.storage.user.clear()
        ui.navigate.to("/")

    with ui.row().style("width:100%; min-height:100vh; gap:0"):

        # ── Sidebar ──
        with ui.column().classes("dash-sidebar").style("gap:4px"):
            ui.html(f'''
                <div style="margin-bottom:28px">
                    <p style="font-size:18px; font-weight:700; color:#fff; margin:0 0 2px">
                        AuthApp
                    </p>
                    <p style="font-size:12px; color:#4f52d3; margin:0; font-weight:600">
                        Dashboard
                    </p>
                </div>
            ''')

            ui.html('<a class="nav-item active">📋  Minhas notas</a>')
            ui.html('<a class="nav-item">📊  Estatísticas</a>')
            ui.html('<a class="nav-item">⚙️  Configurações</a>')

            ui.element("div").style("flex:1")

            with ui.column().style("gap:4px; margin-top:auto"):
                ui.html(f'''
                    <div style="padding:12px 14px; background:#252836; border-radius:8px; margin-bottom:8px">
                        <p style="margin:0; font-size:13px; font-weight:600; color:#e8eaf0">
                            @{username}
                        </p>
                        <p style="margin:0; font-size:11px; color:#666980">
                            Desde {created_at}
                        </p>
                    </div>
                ''')
                ui.button("Sair", on_click=do_logout).props("flat").style(
                    "width:100%; color:#f87171; font-size:13px; border-radius:8px"
                )

        # ── Conteúdo ──
        with ui.column().classes("dash-content").style("gap:0"):

            # Header
            with ui.row().classes("items-center justify-between").style("margin-bottom:28px"):
                ui.html(f'<p class="dash-title">Olá, {username}! 👋</p>')
                with ui.row().classes("items-center gap-2"):
                    now = datetime.now().strftime("%d/%m/%Y")
                    ui.html(f'<span style="font-size:13px; color:#666980">{now}</span>')

            # Stats
            notes_data = get_user_notes(user_id)
            with ui.row().classes("gap-4").style("margin-bottom:28px; width:100%"):
                for label, val, icon in [
                    ("Notas criadas", len(notes_data), "📝"),
                    ("Usuário desde", created_at, "📅"),
                    ("Status", "Ativo", "✅"),
                ]:
                    with ui.element("div").classes("stat-card").style("flex:1"):
                        ui.html(f'<p class="stat-label">{icon}  {label}</p>')
                        ui.html(f'<p class="stat-value" style="font-size:24px">{val}</p>')

            # Notas
            ui.html('''
                <p style="font-size:16px; font-weight:600; color:#fff; margin:0 0 12px">
                    📋  Minhas notas
                </p>
            ''')

            notes_container = ui.column().style("width:100%; gap:0")

            def refresh_notes():
                notes_container.clear()
                data = get_user_notes(user_id)
                with notes_container:
                    if not data:
                        ui.html('''
                            <div style="text-align:center; padding:40px; color:#666980">
                                <p style="font-size:32px; margin:0 0 8px">📭</p>
                                <p style="margin:0; font-size:14px">Nenhuma nota ainda. Crie a primeira!</p>
                            </div>
                        ''')
                    for note in data:
                        dt = note["created_at"][:16].replace("T", " ")
                        with ui.element("div").classes("note-item"):
                            with ui.row().classes("items-start justify-between"):
                                with ui.column().style("gap:2px; flex:1"):
                                    ui.html(f'<p style="margin:0; font-size:14px; color:#e8eaf0">{note["content"]}</p>')
                                    ui.html(f'<p style="margin:4px 0 0; font-size:11px; color:#666980">{dt}</p>')
                                def make_delete(nid):
                                    def fn():
                                        delete_note(nid, user_id)
                                        refresh_notes()
                                    return fn
                                ui.button(icon="delete", on_click=make_delete(note["id"])).props(
                                    "flat round size=sm"
                                ).style("color:#ef4444; margin-top:-4px")

            refresh_notes()

            # Input nova nota
            ui.html('<div style="height:16px"></div>')
            with ui.row().classes("items-center gap-2").style("width:100%"):
                new_note = ui.input(placeholder="Escreva uma nota...").props(
                    'outlined dense'
                ).classes("nicegui-input").style("flex:1")

                def add():
                    if new_note.value.strip():
                        add_note(user_id, new_note.value.strip())
                        new_note.value = ""
                        refresh_notes()

                new_note.on("keydown.enter", add)
                ui.button("Adicionar", on_click=add).props("unelevated").style(
                    "background:#4f52d3; color:white; border-radius:10px; height:40px; font-weight:600"
                )


# ─── Inicialização ──────────────────────────────────────────────────────────────

init_db()

ui.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8080)),
    storage_secret=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
    title="AuthApp",
    favicon="👤",
    dark=True,
)
