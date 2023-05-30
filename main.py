from flask import Flask, render_template, request, redirect, url_for, session
import tiledb
from datetime import datetime
import numpy as np
from itertools import count

# Counter to generate unique IDs
id_counter = count(start=1)

def generate_unique_id():
    return next(id_counter)

app = Flask(__name__, static_folder='static')
app.secret_key = "your_secret_key"  # Set a secret key for session management

# TileDB array schema configuration
array_name = "notes_array"
attr_name_timestamp = "timestamp"
dim_name_user = "user"
dim_name_ID = "noteID"
attr_name_note = "note"
attr_name_category = "category"
session_user = "other"
categories_list = ["Personal", "Work", "Study", "Ideas", "Fitness"]


def create_tiledb_array():
    dom = tiledb.Domain(tiledb.Dim(name=dim_name_ID, domain=(0, 5000), dtype="uint64"),
                        tiledb.Dim(name=dim_name_user, domain=None, dtype="ascii"))
    attr = [tiledb.Attr(name=attr_name_note, dtype=str),
            tiledb.Attr(name=attr_name_category, dtype=str),
            tiledb.Attr(name=attr_name_timestamp, dtype=str)]
    schema = tiledb.ArraySchema(domain=dom, attrs=attr, sparse=True)
    tiledb.SparseArray.create(array_name, schema)


def insert_note_to_tiledb(note, category, user):
    with tiledb.SparseArray(array_name, mode="w") as arr:
        now = datetime.now()
        dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
        print(f"insert_note_to_tiledb:: now {dt_string}")
        arr[generate_unique_id(), user] = {attr_name_note: note,
                                           attr_name_category: category,
                                           attr_name_timestamp: dt_string}


def get_notes_from_tiledb():
    with tiledb.SparseArray(array_name, mode="r") as arr:
        print(session_user)
        if session_user == "admin":
            data = arr[:, :]
        else:
            data = arr[:, session_user]
        ids = data[dim_name_ID]
        notes = data[attr_name_note]
        categories = data[attr_name_category]
        timestamps = data[attr_name_timestamp]
    return ids, notes, categories, timestamps


def edit_note_in_tiledb(new_note, new_category, note_id, user):
    with tiledb.SparseArray(array_name, mode="w") as arr:
        now = datetime.now()
        dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
        arr[note_id, user] = {attr_name_note: new_note,
                              attr_name_category: new_category,
                              attr_name_timestamp: dt_string}


def remove_note_from_tileDB(note_id, user):
    with tiledb.SparseArray(array_name, mode="w") as arr:
        arr[note_id, user] = {attr_name_note: "null",
                              attr_name_category: "null",
                              attr_name_timestamp: "null"}


@app.route("/", methods=["GET", "POST"])
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        note = request.form["note"]
        category = request.form["category"]
        user = session["username"]
        insert_note_to_tiledb(note, category, user)
        return redirect(url_for("home"))
    else:
        if tiledb.object_type(array_name) == "array":
            ids, notes, categories, timestamps = get_notes_from_tiledb()
        else:
            create_tiledb_array()
            ids =[]
            notes = []
            categories = []
            timestamps = []
        zipped_notes_categories = zip(ids, notes, categories, timestamps)
        global categories_list
        return render_template("index.html", notes_categories=zipped_notes_categories, categories=categories_list)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        global session_user
        # Simple user authentication
        if username == "admin" and password == "admin123":
            session["username"] = "admin"
            session_user = session["username"]
        elif username == "user1" and password == "password1":
            session["username"] = "user1"
            session_user = session["username"]
        elif username == "user2" and password == "password2":
            session["username"] = "user2"
            session_user = session["username"]
        else:
            return render_template("login.html", message="Invalid username or password")
            session_user = "other"

        return redirect(url_for("home"))
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

@app.route("/edit/<int:note_id>", methods=["POST"])
def edit_note(note_id):
    updated_note = request.form["note"]
    updated_category = request.form["category"]
    edit_note_in_tiledb(updated_note, updated_category, note_id, session["username"])
    return redirect(url_for("home"))


@app.route("/delete/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    remove_note_from_tileDB(note_id, session["username"])
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run()
