import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "brewlog_secret_key"

DATABASE = "database.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    with open("schema.sql") as f:
        conn.executescript(f.read())
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()

        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Username or email already exists."

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        return "Invalid email or password."

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "")

    conn = get_db_connection()

    if search:
        recipes = conn.execute(
            """
            SELECT * FROM recipes
            WHERE user_id = ?
            AND title LIKE ?
            ORDER BY favorite DESC, id DESC
            """,
            (session["user_id"], f"%{search}%")
        ).fetchall()
    else:
        recipes = conn.execute(
            """
            SELECT * FROM recipes
            WHERE user_id = ?
            ORDER BY favorite DESC, id DESC
            """,
            (session["user_id"],)
        ).fetchall()

    conn.close()

    return render_template("dashboard.html", recipes=recipes, search=search)


@app.route("/add", methods=["GET", "POST"])
def add_recipe():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        ingredients = request.form["ingredients"]
        instructions = request.form["instructions"]
        cost = request.form["cost"]
        recipe_type = request.form["type"]

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO recipes
            (title, category, ingredients, instructions, cost, type, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                category,
                ingredients,
                instructions,
                cost,
                recipe_type,
                session["user_id"],
            )
        )
        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("add_recipe.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_recipe(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    recipe = conn.execute(
        "SELECT * FROM recipes WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    ).fetchone()

    if not recipe:
        conn.close()
        return "Recipe not found."

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        ingredients = request.form["ingredients"]
        instructions = request.form["instructions"]
        cost = request.form["cost"]
        recipe_type = request.form["type"]

        conn.execute(
            """
            UPDATE recipes
            SET title = ?, category = ?, ingredients = ?, instructions = ?, cost = ?, type = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                title,
                category,
                ingredients,
                instructions,
                cost,
                recipe_type,
                id,
                session["user_id"],
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("edit_recipe.html", recipe=recipe)


@app.route("/delete/<int:id>")
def delete_recipe(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM recipes WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/favorite/<int:id>")
def favorite_recipe(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    recipe = conn.execute(
        "SELECT favorite FROM recipes WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    ).fetchone()

    if not recipe:
        conn.close()
        return "Recipe not found."

    new_value = 0 if recipe["favorite"] == 1 else 1

    conn.execute(
        "UPDATE recipes SET favorite = ? WHERE id = ? AND user_id = ?",
        (new_value, id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    # init_db()
    app.run(debug=True)