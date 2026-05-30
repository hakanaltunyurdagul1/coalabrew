import unittest
import os
import tempfile
import sqlite3
from app import app


class CoalaBrewTestCase(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        app.config["TESTING"] = True
        app.config["DATABASE"] = self.db_path
        app.secret_key = "test_secret"
        self.client = app.test_client()

        # Veritabanını oluştur
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT,
                ingredients TEXT,
                instructions TEXT,
                cost REAL,
                type TEXT,
                favorite INTEGER DEFAULT 0,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        conn.commit()
        conn.close()

        import app as app_module
        app_module.DATABASE = self.db_path

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    # -------------------------
    # US1 - User Registration
    # -------------------------
    def test_register_page_loads(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)

    def test_register_success(self):
        response = self.client.post("/register", data={
            "username": "testuser",
            "email": "test@test.com",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_register_duplicate_user(self):
        self.client.post("/register", data={
            "username": "testuser",
            "email": "test@test.com",
            "password": "password123"
        })
        response = self.client.post("/register", data={
            "username": "testuser",
            "email": "test@test.com",
            "password": "password123"
        })
        self.assertIn(b"already exists", response.data)

    # -------------------------
    # US2 - User Login
    # -------------------------
    def test_login_page_loads(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        self.client.post("/register", data={
            "username": "testuser",
            "email": "test@test.com",
            "password": "password123"
        })
        response = self.client.post("/login", data={
            "email": "test@test.com",
            "password": "password123"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_login_invalid_credentials(self):
        response = self.client.post("/login", data={
            "email": "wrong@test.com",
            "password": "wrongpassword"
        })
        self.assertIn(b"Invalid", response.data)

    def test_logout(self):
        response = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    # -------------------------
    # US3 - Create Recipe
    # -------------------------
    def test_add_recipe_requires_login(self):
        response = self.client.get("/add", follow_redirects=True)
        self.assertIn(b"login", response.data.lower())

    def test_add_recipe_success(self):
        self._login()
        response = self.client.post("/add", data={
            "title": "Espresso",
            "category": "Hot",
            "ingredients": "Coffee, Water",
            "instructions": "Brew it",
            "cost": "5",
            "type": "Hot"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    # -------------------------
    # US4 - Edit/Delete Recipe
    # -------------------------
    def test_edit_recipe_not_found(self):
        self._login()
        response = self.client.get("/edit/999")
        self.assertIn(b"not found", response.data.lower())

    def test_delete_recipe_requires_login(self):
        response = self.client.get("/delete/1", follow_redirects=True)
        self.assertIn(b"login", response.data.lower())

    def test_delete_recipe_success(self):
        self._login()
        self.client.post("/add", data={
            "title": "Latte",
            "category": "Hot",
            "ingredients": "Milk, Coffee",
            "instructions": "Mix",
            "cost": "7",
            "type": "Hot"
        })
        response = self.client.get("/delete/1", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    # -------------------------
    # US5 - Search Recipes
    # -------------------------
    def test_search_recipes(self):
        self._login()
        self.client.post("/add", data={
            "title": "Cappuccino",
            "category": "Hot",
            "ingredients": "Milk, Espresso",
            "instructions": "Froth milk",
            "cost": "6",
            "type": "Hot"
        })
        response = self.client.get("/dashboard?search=Cappuccino")
        self.assertIn(b"Cappuccino", response.data)

    def test_search_no_results(self):
        self._login()
        response = self.client.get("/dashboard?search=XYZnonexistent")
        self.assertEqual(response.status_code, 200)

    # -------------------------
    # US6 - Favorite Recipes
    # -------------------------
    def test_favorite_requires_login(self):
        response = self.client.get("/favorite/1", follow_redirects=True)
        self.assertIn(b"login", response.data.lower())

    def test_favorite_not_found(self):
        self._login()
        response = self.client.get("/favorite/999")
        self.assertIn(b"not found", response.data.lower())

    def test_favorite_toggle(self):
        self._login()
        self.client.post("/add", data={
            "title": "Mocha",
            "category": "Hot",
            "ingredients": "Chocolate, Coffee",
            "instructions": "Mix",
            "cost": "8",
            "type": "Hot"
        })
        response = self.client.get("/favorite/1", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    # -------------------------
    # Helper
    # -------------------------
    def _login(self):
        self.client.post("/register", data={
            "username": "testuser",
            "email": "test@test.com",
            "password": "password123"
        })
        self.client.post("/login", data={
            "email": "test@test.com",
            "password": "password123"
        })


if __name__ == "__main__":
    unittest.main()