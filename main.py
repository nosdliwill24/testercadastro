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
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT    UNIQUE NOT NULL,
                email      TEXT    UNIQUE NOT NULL,
                password   TEXT    NOT NULL,
                is_admin   INTEGER DEFAULT 0,
                created_at TEXT    DEFAULT (datetime('now'))
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

        # Migração: adiciona is_admin se o banco já existia sem ela
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

        # Primeiro usuário cadastrado vira admin automaticamente
        first = conn.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1").fetchone()
        if first:
            conn.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (first["id"],))
            conn.commit()

# ─── Auth ──────────────────────────────────────────────────────────────────────

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
            count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
            is_admin = 1 if count == 0 else 0
            conn.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
                (username.strip(), email.strip().lower(), hash_password(password), is_admin),
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

# ─── Notas ─────────────────────────────────────────────────────────────────────

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

# ─── Admin ─────────────────────────────────────────────────────────────────────

def get_all_users() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT u.id, u.username, u.email, u.is_admin, u.created_at,
                   COUNT(n.id) as note_count
            FROM users u
            LEFT JOIN notes n ON n.user_id = u.id
            GROUP BY u.id
            ORDER BY u.id ASC
        """).fetchall()
    return [dict(r) for r in rows]

def toggle_admin(user_id: int, current_is_admin: int):
    new_val = 0 if current_is_admin else 1
    with get_db() as conn:
        conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (new_val, user_id))
        conn.commit()

def delete_user(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM notes WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

def get_stats() -> dict:
    with get_db() as conn:
        users  = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        notes  = conn.execute("SELECT COUNT(*) as c FROM notes").fetchone()["c"]
        admins = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=1").fetchone()["c"]
        newest = conn.execute("SELECT username FROM users ORDER BY id DESC LIMIT 1").fetchone()
    return {
        "users": users, "notes": notes, "admins": admins,
        "newest": newest["username"] if newest else "—",
    }

# ─── Estilo ────────────────────────────────────────────────────────────────────

STYLE = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
* { box-sizing: border-box; }
body { margin:0; font-family:'DM Sans',sans-serif; background:#0f1117; color:#e8eaf0; min-height:100vh; }

.auth-card { background:#1a1d27; border:1px solid #2a2d3a; border-radius:16px; padding:40px; width:100%; max-width:420px; box-shadow:0 24px 64px rgba(0,0,0,.5); }
.brand-title { font-size:28px; font-weight:700; letter-spacing:-.5px; color:#fff; margin:0 0 4px; }
.brand-sub { font-size:14px; color:#666980; margin:0 0 32px; }
.field-label { font-size:13px; font-weight:500; color:#9395a5; margin-bottom:6px; display:block; }

.nicegui-input .q-field__control { background:#0f1117 !important; border:1px solid #2a2d3a !important; border-radius:10px !important; color:#e8eaf0 !important; }
.nicegui-input .q-field__control:hover { border-color:#4f52d3 !important; }

.btn-primary { background:#4f52d3 !important; color:white !important; border-radius:10px !important; font-weight:600 !important; font-size:15px !important; height:48px !important; width:100%; }
.btn-primary:hover { background:#3d40b5 !important; }
.link-btn { color:#7b7ef5 !important; font-size:13px !important; text-decoration:none; cursor:pointer; }
.divider-line { border:none; border-top:1px solid #2a2d3a; margin:20px 0; }

.dash-sidebar { width:240px; background:#1a1d27; border-right:1px solid #2a2d3a; min-height:100vh; padding:24px 16px; flex-shrink:0; }
.dash-content { flex:1; padding:32px; overflow-y:auto; }
.dash-title { font-size:22px; font-weight:700; color:#fff; margin:0; }

.nav-item { display:flex; align-items:center; gap:10px; padding:10px 14px; border-radius:8px; cursor:pointer; font-size:14px; font-weight:500; color:#9395a5; transition:all .15s; text-decoration:none; width:100%; margin-bottom:2px; }
.nav-item:hover { background:#252836; color:#e8eaf0; }
.nav-item.active { background:#252836; color:#7b7ef5; }

.stat-card { background:#1a1d27; border:1px solid #2a2d3a; border-radius:12px; padding:20px 24px; }
.stat-label { font-size:12px; font-weight:500; color:#666980; text-transform:uppercase; letter-spacing:.5px; margin:0 0 4px; }
.stat-value { font-size:28px; font-weight:700; color:#fff; font-family:'DM Mono',monospace; margin:0; }

.note-item { background:#1a1d27; border:1px solid #2a2d3a; border-radius:10px; padding:14px 16px; margin-bottom:10px; transition:border-color .2s; }
.note-item:hover { border-color:#4f52d3; }

.error-msg { background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.3); border-radius:8px; padding:10px 14px; font-size:13px; color:#f87171; }
.success-msg { background:rgba(34,197,94,.1); border:1px solid rgba(34,197,94,.3); border-radius:8px; padding:10px 14px; font-size:13px; color:#4ade80; }

.table-wrap { background:#1a1d27; border:1px solid #2a2d3a; border-radius:12px; overflow:hidden; }
.admin-table { width:100%; border-collapse:collapse; font-size:14px; }
.admin-table th { text-align:left; padding:10px 16px; font-size:11px; font-weight:600; color:#666980; text-transform:uppercase; letter-spacing:.5px; border-bottom:1px solid #2a2d3a; }
.admin-table td { padding:13px 16px; border-bottom:1px solid #1e2130; color:#e8eaf0; vertical-align:middle; }
.admin-table tr:last-child td { border-bottom:none; }
.admin-table tr:hover td { background:#1e2130; }

.badge-admin { background:rgba(79,82,211,.2); color:#7b7ef5; border:1px solid rgba(79,82,211,.4); border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }
.badge-user { background:rgba(102,105,128,.15); color:#9395a5; border:1px solid #2a2d3a; border-radius:6px; padding:2px 8px; font-size:11px; font-weight:600; }
"""

# ─── Sidebar reutilizável ───────────────────────────────────────────────────────

def build_sidebar(username: str, created_at: str, is_admin: bool, active: str = "dashboard"):
    def do_logout():
        app.storage.user.clear()
        ui.navigate.to("/")

    with ui.column().classes("dash-sidebar").style("gap:0"):
        ui.html(f'''
            <div style="margin-bottom:28px">
                <p style="font-size:18px;font-weight:700;color:#fff;margin:0 0 2px">AuthApp</p>
                <p style="font-size:12px;color:#4f52d3;margin:0;font-weight:600">{"Admin" if is_admin else "Dashboard"}</p>
            </div>
        ''')

        ui.html(f'<a class="nav-item {"active" if active=="dashboard" else ""}" href="/dashboard">📋  Minhas notas</a>')

        if is_admin:
            ui.html(f'<a class="nav-item {"active" if active=="admin" else ""}" href="/admin">🛡️  Painel Admin</a>')

        ui.element("div").style("flex:1; min-height:40px")

        ui.html(f'''
            <div style="padding:12px 14px;background:#252836;border-radius:8px;margin-bottom:8px">
                <p style="margin:0;font-size:13px;font-weight:600;color:#e8eaf0">@{username}</p>
                <p style="margin:2px 0 0;font-size:11px;color:#666980">Desde {created_at}</p>
                {"<p style='margin:4px 0 0;font-size:11px;color:#7b7ef5;font-weight:600'>⚡ Admin</p>" if is_admin else ""}
            </div>
        ''')
        ui.button("Sair", on_click=do_logout).props("flat").style(
            "width:100%;color:#f87171;font-size:13px;border-radius:8px"
        )

# ─── Login ─────────────────────────────────────────────────────────────────────

@ui.page("/")
def page_login():
    ui.add_head_html(f"<style>{STYLE}</style>")
    if app.storage.user.get("user"):
        ui.navigate.to("/dashboard"); return

    with ui.column().classes("items-center justify-center").style("min-height:100vh;width:100%"):
        with ui.element("div").classes("auth-card"):
            ui.html('<p class="brand-title">👤  AuthApp</p>')
            ui.html('<p class="brand-sub">Entre na sua conta para continuar</p>')

            msg_area = ui.column().style("width:100%;margin-bottom:12px")
            def show_msg(text, tipo="error"):
                msg_area.clear()
                with msg_area:
                    ui.html(f'<div class="{tipo}-msg">{text}</div>')

            ui.html('<span class="field-label">E-mail</span>')
            email_in = ui.input(placeholder="seu@email.com").props('type=email outlined dense').classes("nicegui-input w-full").style("margin-bottom:16px")
            ui.html('<span class="field-label">Senha</span>')
            pass_in  = ui.input(placeholder="••••••••").props('type=password outlined dense').classes("nicegui-input w-full").style("margin-bottom:24px")

            def do_login():
                ok, result = login_user(email_in.value, pass_in.value)
                if ok:
                    app.storage.user["user"] = result
                    ui.navigate.to("/dashboard")
                else:
                    show_msg(result)

            pass_in.on("keydown.enter", do_login)
            ui.button("Entrar", on_click=do_login).classes("btn-primary")
            ui.html('<hr class="divider-line">')
            with ui.row().classes("justify-center items-center gap-1"):
                ui.html('<span style="font-size:13px;color:#666980">Não tem conta?</span>')
                ui.link("Cadastre-se", "/register").classes("link-btn")

# ─── Cadastro ──────────────────────────────────────────────────────────────────

@ui.page("/register")
def page_register():
    ui.add_head_html(f"<style>{STYLE}</style>")
    if app.storage.user.get("user"):
        ui.navigate.to("/dashboard"); return

    with ui.column().classes("items-center justify-center").style("min-height:100vh;width:100%"):
        with ui.element("div").classes("auth-card"):
            ui.html('<p class="brand-title">✨  Criar Conta</p>')
            ui.html('<p class="brand-sub">Preencha os dados para se cadastrar</p>')

            msg_area = ui.column().style("width:100%;margin-bottom:12px")
            def show_msg(text, tipo="error"):
                msg_area.clear()
                with msg_area:
                    ui.html(f'<div class="{tipo}-msg">{text}</div>')

            ui.html('<span class="field-label">Nome de usuário</span>')
            user_in = ui.input(placeholder="seunome").props('outlined dense').classes("nicegui-input w-full").style("margin-bottom:16px")
            ui.html('<span class="field-label">E-mail</span>')
            email_in = ui.input(placeholder="seu@email.com").props('type=email outlined dense').classes("nicegui-input w-full").style("margin-bottom:16px")
            ui.html('<span class="field-label">Senha</span>')
            pass_in  = ui.input(placeholder="Mínimo 6 caracteres").props('type=password outlined dense').classes("nicegui-input w-full").style("margin-bottom:24px")

            def do_register():
                ok, msg = register_user(user_in.value, email_in.value, pass_in.value)
                if ok:
                    show_msg(msg, "success")
                    ui.timer(1.5, lambda: ui.navigate.to("/"), once=True)
                else:
                    show_msg(msg)

            ui.button("Criar conta", on_click=do_register).classes("btn-primary")
            ui.html('<hr class="divider-line">')
            with ui.row().classes("justify-center items-center gap-1"):
                ui.html('<span style="font-size:13px;color:#666980">Já tem conta?</span>')
                ui.link("Faça login", "/").classes("link-btn")

# ─── Dashboard ─────────────────────────────────────────────────────────────────

@ui.page("/dashboard")
def page_dashboard():
    ui.add_head_html(f"<style>{STYLE}</style>")
    user = app.storage.user.get("user")
    if not user:
        ui.navigate.to("/"); return

    user_id    = user["id"]
    username   = user["username"]
    created_at = user.get("created_at", "")[:10]
    is_admin   = bool(user.get("is_admin", 0))

    with ui.row().style("width:100%;min-height:100vh;gap:0"):
        build_sidebar(username, created_at, is_admin, active="dashboard")

        with ui.column().classes("dash-content").style("gap:0"):
            with ui.row().classes("items-center justify-between").style("margin-bottom:28px"):
                ui.html(f'<p class="dash-title">Olá, {username}! 👋</p>')
                ui.html(f'<span style="font-size:13px;color:#666980">{datetime.now().strftime("%d/%m/%Y")}</span>')

            notes_data = get_user_notes(user_id)
            with ui.row().classes("gap-4").style("margin-bottom:28px;width:100%"):
                for label, val, icon in [
                    ("Notas criadas", len(notes_data), "📝"),
                    ("Usuário desde", created_at, "📅"),
                    ("Status", "Admin" if is_admin else "Ativo", "⚡" if is_admin else "✅"),
                ]:
                    with ui.element("div").classes("stat-card").style("flex:1"):
                        ui.html(f'<p class="stat-label">{icon}  {label}</p>')
                        ui.html(f'<p class="stat-value" style="font-size:24px">{val}</p>')

            ui.html('<p style="font-size:16px;font-weight:600;color:#fff;margin:0 0 12px">📋  Minhas notas</p>')
            notes_container = ui.column().style("width:100%;gap:0")

            def refresh_notes():
                notes_container.clear()
                data = get_user_notes(user_id)
                with notes_container:
                    if not data:
                        ui.html('<div style="text-align:center;padding:40px;color:#666980"><p style="font-size:32px;margin:0 0 8px">📭</p><p style="margin:0;font-size:14px">Nenhuma nota ainda. Crie a primeira!</p></div>')
                    for note in data:
                        dt = note["created_at"][:16].replace("T", " ")
                        with ui.element("div").classes("note-item"):
                            with ui.row().classes("items-start justify-between"):
                                with ui.column().style("gap:2px;flex:1"):
                                    ui.html(f'<p style="margin:0;font-size:14px;color:#e8eaf0">{note["content"]}</p>')
                                    ui.html(f'<p style="margin:4px 0 0;font-size:11px;color:#666980">{dt}</p>')
                                def make_delete(nid):
                                    def fn():
                                        delete_note(nid, user_id)
                                        refresh_notes()
                                    return fn
                                ui.button(icon="delete", on_click=make_delete(note["id"])).props("flat round size=sm").style("color:#ef4444")

            refresh_notes()

            ui.html('<div style="height:16px"></div>')
            with ui.row().classes("items-center gap-2").style("width:100%"):
                new_note = ui.input(placeholder="Escreva uma nota...").props('outlined dense').classes("nicegui-input").style("flex:1")
                def add_new():
                    if new_note.value.strip():
                        add_note(user_id, new_note.value.strip())
                        new_note.value = ""
                        refresh_notes()
                new_note.on("keydown.enter", add_new)
                ui.button("Adicionar", on_click=add_new).props("unelevated").style(
                    "background:#4f52d3;color:white;border-radius:10px;height:40px;font-weight:600"
                )

# ─── Painel Admin ───────────────────────────────────────────────────────────────

@ui.page("/admin")
def page_admin():
    ui.add_head_html(f"<style>{STYLE}</style>")
    user = app.storage.user.get("user")
    if not user:
        ui.navigate.to("/"); return
    if not user.get("is_admin"):
        ui.navigate.to("/dashboard"); return

    username   = user["username"]
    created_at = user.get("created_at", "")[:10]
    my_id      = user["id"]

    with ui.row().style("width:100%;min-height:100vh;gap:0"):
        build_sidebar(username, created_at, True, active="admin")

        with ui.column().classes("dash-content").style("gap:0"):
            with ui.row().classes("items-center justify-between").style("margin-bottom:28px"):
                ui.html('<p class="dash-title">🛡️  Painel Admin</p>')
                ui.html(f'<span style="font-size:13px;color:#666980">{datetime.now().strftime("%d/%m/%Y %H:%M")}</span>')

            stats_row       = ui.row().classes("gap-4").style("margin-bottom:28px;width:100%")
            table_container = ui.column().style("width:100%")

            def refresh_all():
                # ── Stats ──
                stats_row.clear()
                s = get_stats()
                with stats_row:
                    for label, val, icon, color in [
                        ("Usuários",      s["users"],  "👥", "#7b7ef5"),
                        ("Notas totais",  s["notes"],  "📝", "#4ade80"),
                        ("Admins",        s["admins"], "⚡", "#facc15"),
                        ("Último cadastro", s["newest"], "🆕", "#60a5fa"),
                    ]:
                        with ui.element("div").classes("stat-card").style("flex:1"):
                            ui.html(f'<p class="stat-label">{icon}  {label}</p>')
                            ui.html(f'<p class="stat-value" style="font-size:20px;color:{color}">{val}</p>')

                # ── Tabela ──
                table_container.clear()
                users = get_all_users()

                with table_container:
                    with ui.row().classes("items-center justify-between").style("margin-bottom:12px"):
                        ui.html(f'<p style="font-size:16px;font-weight:600;color:#fff;margin:0">Usuários cadastrados <span style="color:#666980;font-size:13px">({len(users)} total)</span></p>')
                        ui.button(icon="refresh", on_click=refresh_all).props("flat round").style("color:#9395a5")

                    with ui.element("div").classes("table-wrap"):
                        # Cabeçalho + linhas em HTML puro para visual limpo
                        rows_html = ""
                        for u in users:
                            dt    = u["created_at"][:16].replace("T", " ") if u["created_at"] else "—"
                            badge = '<span class="badge-admin">Admin</span>' if u["is_admin"] else '<span class="badge-user">Usuário</span>'
                            me_tag = ' <span style="font-size:10px;color:#666980">(você)</span>' if u["id"] == my_id else ""
                            rows_html += f"""
                            <tr>
                              <td style="font-family:'DM Mono',monospace;color:#666980;font-size:12px">#{u['id']}</td>
                              <td><strong>@{u['username']}</strong>{me_tag}</td>
                              <td style="color:#9395a5">{u['email']}</td>
                              <td>{badge}</td>
                              <td style="font-family:'DM Mono',monospace;font-size:12px;color:#9395a5">{dt}</td>
                              <td style="text-align:center;color:#7b7ef5;font-weight:700">{u['note_count']}</td>
                            </tr>"""

                        ui.html(f"""
                        <table class="admin-table">
                          <thead><tr>
                            <th>#</th><th>Usuário</th><th>E-mail</th>
                            <th>Papel</th><th>Cadastro</th><th>Notas</th>
                          </tr></thead>
                          <tbody>{rows_html}</tbody>
                        </table>""")

                    # Ações (botões NiceGUI por linha)
                    ui.html('<p style="font-size:13px;font-weight:600;color:#9395a5;margin:16px 0 8px;text-transform:uppercase;letter-spacing:.5px">Ações por usuário</p>')
                    with ui.element("div").classes("table-wrap").style("margin-top:0"):
                        for u in users:
                            uid   = u["id"]
                            uname = u["username"]
                            is_adm = u["is_admin"]
                            me    = uid == my_id

                            with ui.row().classes("items-center").style(
                                "padding:10px 16px;border-bottom:1px solid #1e2130;gap:12px"
                            ):
                                ui.html(f'<span style="font-size:13px;color:#e8eaf0;font-weight:500;min-width:140px">@{uname}</span>')
                                ui.html(f'<span style="flex:1;font-size:12px;color:#666980">{u["email"]}</span>')

                                def make_toggle(uid=uid, is_adm=is_adm, uname=uname):
                                    def fn():
                                        if uid == my_id:
                                            ui.notify("Não é possível alterar seu próprio admin.", type="warning")
                                            return
                                        toggle_admin(uid, is_adm)
                                        ui.notify(
                                            f"@{uname} {'removido dos admins' if is_adm else 'promovido a admin'}.",
                                            type="positive" if not is_adm else "warning",
                                        )
                                        refresh_all()
                                    return fn

                                def make_delete(uid=uid, uname=uname):
                                    def fn():
                                        if uid == my_id:
                                            ui.notify("Não é possível excluir sua própria conta aqui.", type="warning")
                                            return
                                        delete_user(uid)
                                        ui.notify(f"Usuário @{uname} excluído.", type="negative")
                                        refresh_all()
                                    return fn

                                lbl = "⬇️ Remover admin" if is_adm else "⬆️ Tornar admin"
                                cor = "#f59e0b" if is_adm else "#7b7ef5"
                                ui.button(lbl, on_click=make_toggle()).props("flat size=sm").style(
                                    f"color:{cor};font-size:12px"
                                ).set_enabled(not me)

                                ui.button("🗑️ Excluir", on_click=make_delete()).props("flat size=sm").style(
                                    "color:#ef4444;font-size:12px"
                                ).set_enabled(not me)

            refresh_all()

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
