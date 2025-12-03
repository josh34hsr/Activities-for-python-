import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
import hashlib
import os
import sys
import logging
from datetime import datetime

# ---------------- Logging Setup ----------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recipe_manager.log'),
        logging.StreamHandler()
    ]
)

# ---------------- Custom Exceptions ----------------
class RecipeManagerError(Exception):
    """Base exception class for recipe manager"""
    pass

class DatabaseError(RecipeManagerError):
    """Database-related errors"""
    pass

class ValidationError(RecipeManagerError):
    """Input validation errors"""
    pass

# ---------------- Configuration ----------------
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = ""
DB_NAME = "recipe_db"

CREATE_ADMIN_PASSPHRASE = "CREATE_ADMIN_2025"

# ---------------- Helper Functions ----------------
def sha256(s: str) -> str:
    """Secure password hashing"""
    return hashlib.sha256(s.encode()).hexdigest()

def center(win, w=1000, h=600):
    """Center window on screen"""
    win.update_idletasks()
    ws = win.winfo_screenwidth()
    hs = win.winfo_screenheight()
    x = (ws // 2) - (w // 2)
    y = (hs // 2) - (h // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")

# ---------------- Input Validation System ----------------
class Validator:
    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username with proper error handling"""
        if not username or not username.strip():
            raise ValidationError("Username cannot be empty")
        
        username = username.strip()
        
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        
        if len(username) > 50:
            raise ValidationError("Username cannot exceed 50 characters")
        
        if not all(c.isalnum() or c in ('_', '-') for c in username):
            raise ValidationError("Username can only contain letters, numbers, underscores, and hyphens")
        
        return username

    @staticmethod
    def validate_password(password: str) -> str:
        """Validate password with proper error handling"""
        if not password:
            raise ValidationError("Password cannot be empty")
        
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")
        
        if len(password) > 100:
            raise ValidationError("Password cannot exceed 100 characters")
        
        return password

    @staticmethod
    def validate_recipe_title(title: str) -> str:
        """Validate recipe title"""
        if not title or not title.strip():
            raise ValidationError("Recipe title cannot be empty")
        
        title = title.strip()
        
        if len(title) > 200:
            raise ValidationError("Recipe title cannot exceed 200 characters")
        
        return title

    @staticmethod
    def validate_instructions(instructions: str) -> str:
        """Validate recipe instructions"""
        if not instructions or not instructions.strip():
            raise ValidationError("Instructions cannot be empty")
        
        instructions = instructions.strip()
        
        if len(instructions) > 65535:
            raise ValidationError("Instructions are too long (maximum 65,535 characters)")
        
        return instructions

    @staticmethod
    def validate_prep_time(prep_time: str) -> int:
        """Validate preparation time"""
        if not prep_time or not prep_time.strip():
            raise ValidationError("Preparation time cannot be empty")
        
        try:
            time = int(prep_time.strip())
            if time <= 0:
                raise ValidationError("Preparation time must be a positive number")
            if time > 1440:  # 24 hours in minutes
                raise ValidationError("Preparation time cannot exceed 24 hours (1440 minutes)")
            return time
        except ValueError:
            raise ValidationError("Preparation time must be a valid number")

    @staticmethod
    def validate_ingredient(ingredient: str, quantity: str) -> tuple:
        """Validate ingredient and quantity"""
        ingredient = ingredient.strip() if ingredient else ""
        quantity = quantity.strip() if quantity else ""
        
        if not ingredient:
            raise ValidationError("Ingredient name cannot be empty")
        
        if len(ingredient) > 100:
            raise ValidationError("Ingredient name is too long (maximum 100 characters)")
        
        if len(quantity) > 50:
            raise ValidationError("Quantity description is too long (maximum 50 characters)")
        
        return ingredient, quantity

# ---------------- Enhanced Database Class with Error Handling ----------------
class Database:
    def __init__(self):
        self.conf = {"host": DB_HOST, "user": DB_USER, "password": DB_PASS}
        self.conn = None
        self.cur = None
        self.connect_and_init()

    def connect_and_init(self):
        """Establish database connection with comprehensive error handling"""
        try:
            # Initial connection without database
            self.conn = mysql.connector.connect(**self.conf)
            self.cur = self.conn.cursor()
            
            # Create database if it doesn't exist
            self.cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            self.conn.commit()
            
            # Close and reconnect with database
            self.cur.close()
            self.conn.close()
            
            # Reconnect with the specific database
            self.conn = mysql.connector.connect(
                database=DB_NAME, 
                **self.conf
            )
            self.cur = self.conn.cursor(buffered=True)
            
            # Create all tables
            self._create_tables()
            logging.info("Database connection and initialization successful")
            return
                
        except mysql.connector.Error as e:
            error_msg = f"Cannot connect to database"
            logging.critical(error_msg)
            messagebox.showerror(
                "Database Connection Error",
                f"{error_msg}\n\n"
                f"Error: {e}\n\n"
                f"Please ensure:\n"
                f"• MySQL server is running in XAMPP\n"
                f"• Database credentials are correct\n"
                f"• You have necessary permissions"
            )
            sys.exit(1)

    def _create_tables(self):
        """Create all required tables with updated schema"""
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('user','admin') DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL,
                recipe_count INT DEFAULT 0
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS recipes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                instructions TEXT,
                views INT DEFAULT 0,
                prep_time INT DEFAULT 0,
                created_by VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
                status ENUM('active', 'deleted') DEFAULT 'active',
                INDEX idx_created_by (created_by),
                INDEX idx_created_at (created_at),
                INDEX idx_views (views)
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                recipe_count INT DEFAULT 0
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS recipe_categories (
                recipe_id INT,
                category_id INT,
                PRIMARY KEY (recipe_id, category_id),
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                recipe_id INT NOT NULL,
                ingredient VARCHAR(255) NOT NULL,
                quantity VARCHAR(255) NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS recipe_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                recipe_id INT,
                username VARCHAR(255),
                event_type ENUM('view', 'edit', 'delete', 'create') NOT NULL,
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS user_recipe_views (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                recipe_id INT NOT NULL,
                view_count INT DEFAULT 0,
                last_viewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_recipe (username, recipe_id),
                FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            """
        ]
        
        for table_sql in tables:
            try:
                self.cur.execute(table_sql)
                self.conn.commit()
            except mysql.connector.Error as e:
                logging.error(f"Failed to create table: {e}")
                # Don't raise error, continue with other tables

    def execute_safe(self, query: str, params: tuple = None, operation: str = "execute"):
        """Safe database execution with comprehensive error handling"""
        try:
            if params:
                self.cur.execute(query, params)
            else:
                self.cur.execute(query)
            
            if operation == "fetchone":
                return self.cur.fetchone()
            elif operation == "fetchall":
                return self.cur.fetchall()
            elif operation == "commit":
                self.conn.commit()
                return True
            elif operation == "lastrowid":
                self.conn.commit()
                return self.cur.lastrowid
            else:
                self.conn.commit()
                return True
                
        except mysql.connector.Error as e:
            logging.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")

    def log_recipe_event(self, recipe_id, username, event_type):
        """Log recipe events"""
        try:
            self.execute_safe(
                "INSERT INTO recipe_events (recipe_id, username, event_type) VALUES (%s, %s, %s)",
                (recipe_id, username, event_type)
            )
        except Exception as e:
            logging.error(f"Failed to log recipe event: {e}")

    # User methods
    def register_user(self, username, password, role="user"):
        try:
            username = Validator.validate_username(username)
            password = Validator.validate_password(password)
            
            # Check if username already exists
            existing = self.execute_safe(
                "SELECT id FROM users WHERE username=%s", 
                (username,), 
                "fetchone"
            )
            
            if existing:
                raise DatabaseError("Username already exists")
            
            result = self.execute_safe(
                "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
                (username, sha256(password), role),
                "lastrowid"
            )
            
            if result:
                logging.info(f"User '{username}' registered successfully with role '{role}'")
                return True
            else:
                return False
                
        except ValidationError as e:
            logging.warning(f"Registration validation failed: {e}")
            raise  # Re-raise to be caught by the UI
        except DatabaseError as e:
            logging.error(f"Database error during registration: {e}")
            raise  # Re-raise to be caught by the UI
        except Exception as e:
            logging.error(f"Unexpected error during registration: {e}")
            return False

    def login_user(self, username, password):
        try:
            username = Validator.validate_username(username)
            password = Validator.validate_password(password)
            
            result = self.execute_safe(
                "SELECT password_hash, role FROM users WHERE username=%s", 
                (username,), 
                "fetchone"
            )
            
            if not result:
                logging.warning(f"Failed login attempt for non-existent user: {username}")
                return None
            
            if result[0] == sha256(password):
                # Update last login timestamp
                self.execute_safe(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = %s",
                    (username,)
                )
                logging.info(f"Successful login for user: {username}")
                return result[1]
            else:
                logging.warning(f"Failed login attempt for user: {username}")
                return None
                
        except ValidationError as e:
            logging.warning(f"Login validation failed: {e}")
            return None
        except DatabaseError as e:
            logging.error(f"Database error during login: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error during login: {e}")
            return None

    # Category methods
    def add_category(self, name):
        try:
            if not name or not name.strip():
                raise ValidationError("Category name cannot be empty")
            
            name = name.strip()
            
            # Check if category already exists
            existing = self.execute_safe(
                "SELECT id FROM categories WHERE name = %s", 
                (name,), 
                "fetchone"
            )
            
            if existing:
                logging.info(f"Category '{name}' already exists with ID: {existing[0]}")
                return existing[0]  # Return existing ID
            
            # Insert new category
            result = self.execute_safe(
                "INSERT INTO categories (name) VALUES (%s)",
                (name,),
                "lastrowid"
            )
            logging.info(f"New category '{name}' added with ID: {result}")
            return result
        except DatabaseError as e:
            logging.error(f"Failed to add category '{name}': {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error adding category '{name}': {e}")
            return None

    def all_categories(self):
        try:
            return self.execute_safe(
                "SELECT id, name FROM categories ORDER BY name ASC", 
                operation="fetchall"
            ) or []
        except DatabaseError as e:
            logging.error(f"Failed to fetch categories: {e}")
            return []

    def recipes_by_category(self, category_id=None):
        """Get recipes by category, or all if no category specified"""
        try:
            if category_id:
                return self.execute_safe(
                    """
                    SELECT r.id, r.title, r.instructions, r.views, 
                           r.created_by, r.created_at, r.prep_time
                    FROM recipes r
                    JOIN recipe_categories rc ON r.id = rc.recipe_id
                    WHERE rc.category_id = %s AND r.status = 'active'
                    ORDER BY r.created_at DESC
                    """,
                    (category_id,),
                    operation="fetchall"
                ) or []
            else:
                return self.execute_safe(
                    "SELECT id, title, instructions, views, created_by, created_at, prep_time FROM recipes WHERE status = 'active' ORDER BY created_at DESC",
                    operation="fetchall"
                ) or []
        except DatabaseError as e:
            logging.error(f"Failed to fetch recipes by category: {e}")
            return []

    # Recipe methods
    def add_recipe(self, title, instructions, created_by="unknown", category_ids=None, ingredients=None, prep_time=0):
        try:
            title = Validator.validate_recipe_title(title)
            instructions = Validator.validate_instructions(instructions)
            prep_time = Validator.validate_prep_time(str(prep_time)) if prep_time else 0
            
            result = self.execute_safe(
                "INSERT INTO recipes (title, instructions, created_by, prep_time) VALUES (%s,%s,%s,%s)",
                (title, instructions, created_by, prep_time),
                "lastrowid"
            )
            rid = result
            
            # Update user's recipe count
            self.execute_safe(
                "UPDATE users SET recipe_count = recipe_count + 1 WHERE username = %s",
                (created_by,)
            )
            
            # Log recipe creation event
            self.log_recipe_event(rid, created_by, 'create')
            
            # Add categories with proper validation
            if category_ids and category_ids != ['']:
                for cid in category_ids:
                    try:
                        # Ensure cid is an integer
                        cid_int = int(cid)
                        
                        # First check if category exists
                        category_check = self.execute_safe(
                            "SELECT id FROM categories WHERE id = %s",
                            (cid_int,),
                            "fetchone"
                        )
                        
                        if category_check:
                            # Insert into junction table
                            self.execute_safe(
                                "INSERT INTO recipe_categories (recipe_id, category_id) VALUES (%s, %s)", 
                                (rid, cid_int)
                            )
                            
                            # Update category count
                            self.execute_safe(
                                "UPDATE categories SET recipe_count = recipe_count + 1 WHERE id = %s",
                                (cid_int,)
                            )
                            logging.info(f"Added recipe {rid} to category {cid_int}")
                        else:
                            logging.warning(f"Category ID {cid_int} does not exist")
                            
                    except (ValueError, DatabaseError) as e:
                        logging.error(f"Failed to add recipe to category {cid}: {e}")
                        continue
            else:
                logging.info(f"Recipe {rid} added without categories")
            
            if ingredients:
                for ing, qty in ingredients:
                    try:
                        ing, qty = Validator.validate_ingredient(ing, qty)
                        self.execute_safe(
                            "INSERT INTO recipe_ingredients (recipe_id, ingredient, quantity) VALUES (%s,%s,%s)", 
                            (rid, ing, qty)
                        )
                    except (ValidationError, DatabaseError) as e:
                        logging.error(f"Failed to add ingredient '{ing}': {e}")
                        continue
            
            logging.info(f"Recipe '{title}' added successfully with ID: {rid}")
            return rid
        except (ValidationError, DatabaseError) as e:
            logging.error(f"Failed to add recipe: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error adding recipe: {e}")
            raise

    def update_recipe(self, recipe_id, title, instructions, category_ids=None, ingredients=None, prep_time=0):
        """Update existing recipe"""
        try:
            title = Validator.validate_recipe_title(title)
            instructions = Validator.validate_instructions(instructions)
            prep_time = Validator.validate_prep_time(str(prep_time)) if prep_time else 0
            
            # Update recipe
            self.execute_safe(
                """
                UPDATE recipes 
                SET title=%s, instructions=%s, prep_time=%s, updated_at=CURRENT_TIMESTAMP 
                WHERE id=%s
                """,
                (title, instructions, prep_time, recipe_id)
            )
            
            # Update categories
            if category_ids is not None:
                # Remove old categories
                self.execute_safe(
                    "DELETE FROM recipe_categories WHERE recipe_id=%s",
                    (recipe_id,)
                )
                
                # Add new categories with validation
                if category_ids and category_ids != ['']:
                    for cid in category_ids:
                        try:
                            cid_int = int(cid)
                            
                            # Check if category exists
                            category_check = self.execute_safe(
                                "SELECT id FROM categories WHERE id = %s",
                                (cid_int,),
                                "fetchone"
                            )
                            
                            if category_check:
                                self.execute_safe(
                                    "INSERT INTO recipe_categories (recipe_id, category_id) VALUES (%s,%s)", 
                                    (recipe_id, cid_int)
                                )
                            else:
                                logging.warning(f"Category ID {cid_int} does not exist")
                        except (ValueError, DatabaseError) as e:
                            logging.error(f"Failed to add category {cid} to recipe {recipe_id}: {e}")
                            continue
            
            # Update ingredients if provided
            if ingredients is not None:
                # Remove old ingredients
                self.execute_safe(
                    "DELETE FROM recipe_ingredients WHERE recipe_id=%s",
                    (recipe_id,)
                )
                
                # Add new ingredients
                for ing, qty in ingredients:
                    try:
                        ing, qty = Validator.validate_ingredient(ing, qty)
                        self.execute_safe(
                            "INSERT INTO recipe_ingredients (recipe_id, ingredient, quantity) VALUES (%s,%s,%s)", 
                            (recipe_id, ing, qty)
                        )
                    except (ValidationError, DatabaseError) as e:
                        logging.error(f"Failed to add ingredient '{ing}': {e}")
                        continue
            
            # Log edit event
            self.log_recipe_event(recipe_id, "user", 'edit')
            logging.info(f"Recipe {recipe_id} updated successfully")
            
            return True
        except (ValidationError, DatabaseError) as e:
            logging.error(f"Failed to update recipe: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error updating recipe: {e}")
            return False

    def delete_recipe(self, recipe_id, username):
        """Soft delete recipe"""
        try:
            # Get recipe info before deletion
            recipe = self.get_recipe(recipe_id)
            if not recipe:
                return False
            
            # Soft delete (mark as deleted)
            self.execute_safe(
                "UPDATE recipes SET status='deleted' WHERE id=%s",
                (recipe_id,)
            )
            
            # Update user's recipe count
            self.execute_safe(
                "UPDATE users SET recipe_count = recipe_count - 1 WHERE username = %s",
                (recipe['meta'][4],)
            )
            
            # Delete from user_recipe_views
            self.execute_safe(
                "DELETE FROM user_recipe_views WHERE recipe_id=%s",
                (recipe_id,)
            )
            
            # Log deletion event
            self.log_recipe_event(recipe_id, username, 'delete')
            logging.info(f"Recipe {recipe_id} deleted by user {username}")
            
            return True
        except DatabaseError as e:
            logging.error(f"Failed to delete recipe: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error deleting recipe: {e}")
            return False

    def get_recipe(self, rid):
        try:
            recipe = self.execute_safe(
                "SELECT id, title, instructions, views, created_by, created_at, prep_time FROM recipes WHERE id=%s AND status='active'", 
                (rid,), 
                "fetchone"
            )
            if not recipe:
                return None

            cats = self.execute_safe(
                "SELECT c.id, c.name FROM categories c JOIN recipe_categories rc ON c.id=rc.category_id WHERE rc.recipe_id=%s", 
                (rid,), 
                "fetchall"
            ) or []
            
            ingredients = self.execute_safe(
                "SELECT ingredient, quantity FROM recipe_ingredients WHERE recipe_id=%s", 
                (rid,), 
                "fetchall"
            ) or []
            
            return {"meta": recipe, "categories": cats, "ingredients": ingredients}
        except DatabaseError as e:
            logging.error(f"Failed to get recipe {rid}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error getting recipe {rid}: {e}")
            return None

    def all_recipes(self, limit=1000):
        try:
            return self.execute_safe(
                "SELECT id, title, instructions, views, created_by, created_at, prep_time FROM recipes WHERE status='active' ORDER BY created_at DESC LIMIT %s", 
                (limit,), 
                "fetchall"
            ) or []
        except DatabaseError as e:
            logging.error(f"Failed to fetch all recipes: {e}")
            return []

    def recent_recipes(self, limit=10):
        try:
            return self.execute_safe(
                "SELECT id, title, created_by, created_at, views, prep_time FROM recipes WHERE status='active' ORDER BY created_at DESC LIMIT %s", 
                (limit,), 
                "fetchall"
            ) or []
        except DatabaseError as e:
            logging.error(f"Failed to fetch recent recipes: {e}")
            return []

    def most_viewed_recipes(self, limit=10):
        try:
            return self.execute_safe(
                "SELECT id, title, views, created_by, prep_time FROM recipes WHERE status='active' ORDER BY views DESC LIMIT %s", 
                (limit,), 
                "fetchall"
            ) or []
        except DatabaseError as e:
            logging.error(f"Failed to fetch most viewed recipes: {e}")
            return []

    def increment_view(self, rid, username):
        """Increment view count for a recipe with user-specific tracking"""
        try:
            # Increment global view count
            self.execute_safe("UPDATE recipes SET views = views + 1 WHERE id=%s", (rid,))
            
            # Track user-specific view
            # Check if user has viewed this recipe before
            existing = self.execute_safe(
                "SELECT view_count FROM user_recipe_views WHERE username=%s AND recipe_id=%s",
                (username, rid),
                "fetchone"
            )
            
            if existing:
                # Update existing view count
                self.execute_safe(
                    "UPDATE user_recipe_views SET view_count = view_count + 1, last_viewed=CURRENT_TIMESTAMP WHERE username=%s AND recipe_id=%s",
                    (username, rid)
                )
            else:
                # Create new user-specific view record
                self.execute_safe(
                    "INSERT INTO user_recipe_views (username, recipe_id, view_count) VALUES (%s, %s, 1)",
                    (username, rid)
                )
            
            # Log recipe view event
            self.log_recipe_event(rid, username, 'view')
        except DatabaseError as e:
            logging.error(f"Failed to increment view for recipe {rid}: {e}")

    # User recipes methods for admin
    def get_user_recipes(self, username):
        """Get all recipes created by a specific user"""
        try:
            return self.execute_safe(
                "SELECT id, title, views, created_at, prep_time FROM recipes WHERE created_by=%s AND status='active' ORDER BY created_at DESC",
                (username,),
                "fetchall"
            ) or []
        except DatabaseError as e:
            logging.error(f"Failed to get recipes for user {username}: {e}")
            return []

    # Admin methods
    def get_system_stats(self):
        """Get basic system statistics"""
        try:
            stats = {}
            
            # Basic counts
            stats['total_users'] = self.execute_safe(
                "SELECT COUNT(*) FROM users",
                operation="fetchone"
            )[0] or 0
            
            stats['total_recipes'] = self.execute_safe(
                "SELECT COUNT(*) FROM recipes WHERE status='active'",
                operation="fetchone"
            )[0] or 0
            
            stats['total_categories'] = self.execute_safe(
                "SELECT COUNT(*) FROM categories",
                operation="fetchone"
            )[0] or 0
            
            stats['total_views'] = self.execute_safe(
                "SELECT SUM(views) FROM recipes WHERE status='active'",
                operation="fetchone"
            )[0] or 0
            
            # Recent activity
            stats['recent_activity'] = self.execute_safe(
                "SELECT COUNT(*) FROM recipe_events WHERE event_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
                operation="fetchone"
            )[0] or 0
            
            stats['recent_recipes'] = self.execute_safe(
                "SELECT COUNT(*) FROM recipes WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND status='active'",
                operation="fetchone"
            )[0] or 0
            
            # Most active users
            stats['top_users'] = self.execute_safe(
                """
                SELECT created_by, COUNT(*) as recipe_count, SUM(views) as total_views
                FROM recipes 
                WHERE status='active'
                GROUP BY created_by
                ORDER BY recipe_count DESC
                LIMIT 5
                """,
                operation="fetchall"
            ) or []
            
            return stats
            
        except DatabaseError as e:
            logging.error(f"Failed to get system stats: {e}")
            return {}
        except Exception as e:
            logging.error(f"Unexpected error getting system stats: {e}")
            return {}

    def get_all_users(self):
        """Get all users for admin view"""
        try:
            return self.execute_safe(
                "SELECT id, username, role, created_at, last_login, recipe_count FROM users ORDER BY created_at DESC",
                operation="fetchall"
            ) or []
        except DatabaseError as e:
            logging.error(f"Failed to get all users: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error getting all users: {e}")
            return []

    def search_users(self, query):
        """Search users by username - FIXED FOR EXACT MATCHES"""
        try:
            if not query or not query.strip():
                return self.get_all_users()
                
            query = query.strip()
            
            # Search for exact match or starts with - case insensitive
            qlike = f"{query}%"
            
            return self.execute_safe(
                "SELECT id, username, role, created_at, last_login, recipe_count FROM users WHERE LOWER(username) LIKE LOWER(%s) ORDER BY username ASC",
                (qlike,),
                "fetchall"
            ) or []
        except DatabaseError as e:
            logging.error(f"Failed to search users for '{query}': {e}")
            return []

# ---------------- Modern UI Components ----------------
class ModernButton(tk.Button):
    """Modern styled button with hover effects"""
    def __init__(self, master=None, **kwargs):
        default_style = {
            'bg': '#4CAF50',
            'fg': 'white',
            'font': ('Segoe UI', 10),
            'relief': 'flat',
            'bd': 0,
            'padx': 20,
            'pady': 10,
            'cursor': 'hand2'
        }
        default_style.update(kwargs)
        super().__init__(master, **default_style)
        
        self.default_bg = default_style['bg']
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, e):
        if self['state'] != 'disabled':
            self.configure(bg='#45a049')
    
    def _on_leave(self, e):
        if self['state'] != 'disabled':
            self.configure(bg=self.default_bg)

class ModernEntry(tk.Entry):
    """Modern styled entry field"""
    def __init__(self, master=None, **kwargs):
        default_style = {
            'font': ('Segoe UI', 10),
            'relief': 'flat',
            'bd': 1,
            'bg': 'white',
            'highlightthickness': 1
        }
        default_style.update(kwargs)
        super().__init__(master, **default_style)

# ---------------- Recipe App ----------------
class RecipeApp:
    def __init__(self, root, db: Database, username="user", user_role="user"):
        self.root = root
        self.db = db
        self.username = username
        self.user_role = user_role
        self.root.title(f"Recipe Manager — {username}")
        center(self.root, 1200, 700)
        self.build_ui()
        
    def build_ui(self):
        # Configure main window
        self.root.configure(bg='#f8f9fa')
        
        # Create modern sidebar
        self.sidebar = tk.Frame(self.root, bg="#2c3e50", width=250)
        self.sidebar.pack(side="left", fill="y", padx=0)
        self.sidebar.pack_propagate(False)
        
        # Sidebar content
        role_icon = "👑" if self.user_role == "admin" else "👤"
        tk.Label(self.sidebar, text=f"{role_icon} {self.username}", 
                fg="white", bg="#2c3e50", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))
        
        tk.Label(self.sidebar, text="Recipe Manager", 
                fg="#ecf0f1", bg="#2c3e50", font=("Segoe UI", 10)).pack(pady=(0, 20))
        
        # Navigation buttons
        nav_buttons = [
            ("📊 Dashboard", self.show_dashboard),
            ("➕ Add Recipe", self.show_add_recipe_window),
            ("📖 All Recipes", self.show_all_recipes_window),
        ]
        
        if self.user_role == "admin":
            nav_buttons.append(("⚙️ Admin Panel", self.show_admin_window))
        
        nav_buttons.append(("🚪 Logout", self.logout))
        
        for text, command in nav_buttons:
            btn = ModernButton(self.sidebar, text=text, width=22, height=2, 
                             command=command, bg="#34495e", font=("Segoe UI", 11))
            btn.pack(pady=6, padx=15)
        
        # Main content area
        self.main = tk.Frame(self.root, bg="#f8f9fa")
        self.main.pack(side="right", fill="both", expand=True)
        
        # Show dashboard initially
        self.show_dashboard()
    
    def clear_main(self):
        """Clear the main content area"""
        for widget in self.main.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        """Show dashboard with user-specific stats"""
        self.clear_main()
        
        # Header
        header_frame = tk.Frame(self.main, bg="#f8f9fa", padx=20, pady=15)
        header_frame.pack(fill="x")
        
        welcome_text = f"👑 Welcome, {self.username}!" if self.user_role == "admin" else f"👤 Welcome, {self.username}!"
        tk.Label(header_frame, text=welcome_text, 
                font=("Segoe UI", 24, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(anchor="w")
        
        tk.Label(header_frame, text="Your recipe management dashboard", 
                font=("Segoe UI", 12), bg="#f8f9fa", fg="#7f8c8d").pack(anchor="w", pady=(0, 10))
        
        # Stats cards - Only show total recipes
        stats_frame = tk.Frame(self.main, bg="#f8f9fa")
        stats_frame.pack(fill="x", pady=20, padx=20)
        
        # Get system-wide stats
        total_recipes = len(self.db.all_recipes())
        
        stats_data = [
            ("Total Recipes", total_recipes, "#3498db", "📋"),
        ]
        
        for i, (title, value, color, icon) in enumerate(stats_data):
            card = tk.Frame(stats_frame, bg="white", bd=1, relief="solid", padx=15, pady=15)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            stats_frame.columnconfigure(i, weight=1)
            
            # Icon
            tk.Label(card, text=icon, font=("Segoe UI", 24), 
                   bg="white", fg=color).pack(anchor="w")
            
            # Value
            tk.Label(card, text=str(value), font=("Segoe UI", 20, "bold"), 
                   bg="white", fg="#2c3e50").pack(anchor="w", pady=(5, 0))
            
            # Title
            tk.Label(card, text=title, font=("Segoe UI", 10), 
                   bg="white", fg="#7f8c8d").pack(anchor="w")
        
        # Recent and Popular sections
        content_frame = tk.Frame(self.main, bg="#f8f9fa")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Recent recipes
        recent_frame = tk.LabelFrame(content_frame, text="📝 Recent Recipes", 
                                   font=("Segoe UI", 14, "bold"), bg="#f8f9fa", padx=15, pady=10)
        recent_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.populate_recipe_list(recent_frame, self.db.recent_recipes(5))
        
        # Most viewed recipes (system-wide)
        popular_frame = tk.LabelFrame(content_frame, text="🔥 Most Popular", 
                                    font=("Segoe UI", 14, "bold"), bg="#f8f9fa", padx=15, pady=10)
        popular_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.populate_recipe_list(popular_frame, self.db.most_viewed_recipes(5))
    
    def populate_recipe_list(self, parent, recipes):
        """Populate a frame with recipe list"""
        for widget in parent.winfo_children():
            widget.destroy()
        
        if not recipes:
            tk.Label(parent, text="No recipes found", font=("Segoe UI", 11), 
                   bg="#f8f9fa", fg="#7f8c8d").pack(pady=20)
            return
        
        canvas = tk.Canvas(parent, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for recipe in recipes:
            rid = recipe[0]
            title = recipe[1]
            
            # Correct column indexing for different query results
            if len(recipe) == 6:  # recent_recipes query
                created_by = recipe[2]
                created_at = recipe[3]
                views = recipe[4] if recipe[4] is not None else 0
                prep_time = recipe[5] if recipe[5] is not None else 0
            elif len(recipe) == 5:  # most_viewed_recipes query
                views = recipe[2] if recipe[2] is not None else 0
                created_by = recipe[3]
                prep_time = recipe[4] if recipe[4] is not None else 0
                created_at = "N/A"
            else:
                created_by = "Unknown"
                created_at = "N/A"
                views = 0
                prep_time = 0
            
            card = tk.Frame(scrollable_frame, bg="white", bd=1, relief="solid", padx=12, pady=10)
            card.pack(fill="x", pady=5)
            
            # Recipe title
            title_label = tk.Label(card, text=title, font=("Segoe UI", 12, "bold"), 
                                 bg="white", anchor="w")
            title_label.pack(fill="x")
            
            # Recipe info
            info_text = f"👤 {created_by}"
            if prep_time:
                info_text += f" | ⏱ {prep_time}min"
            if views:
                info_text += f" | 👁 {views} views"
                
            tk.Label(card, text=info_text, font=("Segoe UI", 9), 
                   bg="white", fg="#7f8c8d", anchor="w").pack(fill="x", pady=(2, 5))
            
            # View button
            btn_frame = tk.Frame(card, bg="white")
            btn_frame.pack(anchor="e")
            
            ModernButton(btn_frame, text="View Recipe", command=lambda r=rid: self.view_recipe_window(r),
                       bg="#3498db", font=("Segoe UI", 9), padx=10, pady=3).pack(side="left", padx=2)
            
            if created_by == self.username or self.user_role == "admin":
                ModernButton(btn_frame, text="Edit", command=lambda r=rid: self.edit_recipe_window(r),
                           bg="#f39c12", font=("Segoe UI", 9), padx=10, pady=3).pack(side="left", padx=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_add_recipe_window(self):
        """Show add recipe window with scrollable ingredients section"""
        win = tk.Toplevel(self.root)
        win.title("Add New Recipe")
        win.configure(bg='#f8f9fa')
        center(win, 800, 700)
        win.transient(self.root)  # Make window modal
        win.grab_set()  # Make window modal
        
        # Create scrollable frame for the entire window
        main_frame = tk.Frame(win, bg="#f8f9fa")
        main_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(main_frame, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        tk.Label(scrollable_frame, text="➕ Add New Recipe", 
                font=("Segoe UI", 20, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(anchor="w", padx=20, pady=(15, 10))
        
        # Form container
        form_frame = tk.Frame(scrollable_frame, bg="white", bd=1, relief="solid", padx=20, pady=20)
        form_frame.pack(fill="x", padx=20, pady=10)
        
        # Recipe Title
        tk.Label(form_frame, text="Recipe Title *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=0, column=0, sticky="w", pady=(0, 5))
        title_entry = ModernEntry(form_frame, width=50)
        title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        title_entry.focus()
        
        # Preparation Time
        tk.Label(form_frame, text="Preparation Time (minutes) *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=2, column=0, sticky="w", pady=(0, 5))
        prep_time_entry = ModernEntry(form_frame, width=15)
        prep_time_entry.grid(row=3, column=0, sticky="w", pady=(0, 15))
        prep_time_entry.insert(0, "30")
        
        # Categories
        tk.Label(form_frame, text="Categories", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=4, column=0, sticky="w", pady=(0, 5))
        
        # Category selection frame
        cat_frame = tk.Frame(form_frame, bg="white")
        cat_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # Existing categories
        all_categories = self.db.all_categories()
        cat_vars = {}
        
        # Create cat_check_frame even if empty
        cat_check_frame = tk.Frame(cat_frame, bg="white")
        cat_check_frame.pack(fill="x", pady=5)
        
        if all_categories:
            tk.Label(cat_frame, text="Select existing categories:", 
                    font=("Segoe UI", 10), bg="white").pack(anchor="w", pady=(0, 5))
            
            for cid, cname in all_categories:
                var = tk.IntVar()
                cb = tk.Checkbutton(cat_check_frame, text=cname, variable=var,
                                  font=("Segoe UI", 9), bg="white")
                cb.pack(side="left", padx=10)
                cat_vars[cid] = var
        else:
            # If no categories exist, show a message
            tk.Label(cat_check_frame, text="No categories yet. Add one below!", 
                    font=("Segoe UI", 9), bg="white", fg="#7f8c8d").pack(pady=5)
        
        # Add new category
        tk.Label(cat_frame, text="Or add new category:", 
                font=("Segoe UI", 10), bg="white").pack(anchor="w", pady=(10, 5))
        
        new_cat_frame = tk.Frame(cat_frame, bg="white")
        new_cat_frame.pack(fill="x")
        
        new_cat_entry = ModernEntry(new_cat_frame, width=30)
        new_cat_entry.pack(side="left", fill="x", expand=True)
        
        def add_new_category():
            try:
                category_name = new_cat_entry.get().strip()
                if not category_name:
                    messagebox.showwarning("Input Error", "Please enter a category name")
                    return
                
                cid = self.db.add_category(category_name)
                if cid:
                    # Clear the "no categories" message if it exists
                    for widget in cat_check_frame.winfo_children():
                        if isinstance(widget, tk.Label) and "No categories" in widget.cget("text"):
                            widget.destroy()
                    
                    # Remove the "Select existing categories:" label if it doesn't exist yet
                    if not all_categories:
                        # Add the label for existing categories
                        tk.Label(cat_frame, text="Select existing categories:", 
                                font=("Segoe UI", 10), bg="white").pack(anchor="w", pady=(0, 5), before=cat_check_frame)
                    
                    # Add checkbox for new category
                    var = tk.IntVar()
                    cb = tk.Checkbutton(cat_check_frame, text=category_name, variable=var,
                                      font=("Segoe UI", 9), bg="white")
                    cb.pack(side="left", padx=10)
                    cat_vars[cid] = var
                    new_cat_entry.delete(0, tk.END)
                    messagebox.showinfo("Success", f"Category '{category_name}' added!")
                else:
                    messagebox.showinfo("Info", f"Category '{category_name}' already exists")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add category: {e}")
        
        ModernButton(new_cat_frame, text="Add Category", command=add_new_category,
                   bg="#9b59b6", padx=15).pack(side="left", padx=5)
        
        # Ingredients with scrollable section
        tk.Label(form_frame, text="Ingredients *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=6, column=0, sticky="w", pady=(0, 5))
        
        # Ingredients container with scrollbar
        ingredients_container = tk.Frame(form_frame, bg="white", height=200)
        ingredients_container.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
        
        # Create canvas and scrollbar for ingredients
        ingredients_canvas = tk.Canvas(ingredients_container, bg="white", highlightthickness=0)
        ingredients_scrollbar = ttk.Scrollbar(ingredients_container, orient="vertical", command=ingredients_canvas.yview)
        ingredients_scrollable_frame = tk.Frame(ingredients_canvas, bg="white")
        
        ingredients_scrollable_frame.bind("<Configure>", lambda e: ingredients_canvas.configure(scrollregion=ingredients_canvas.bbox("all")))
        ingredients_canvas.create_window((0, 0), window=ingredients_scrollable_frame, anchor="nw")
        ingredients_canvas.configure(yscrollcommand=ingredients_scrollbar.set)
        
        ingredients_list = []
        
        def add_ingredient_field(ingredient="", quantity=""):
            frame = tk.Frame(ingredients_scrollable_frame, bg="white")
            frame.pack(fill="x", pady=2, padx=5)
            
            tk.Label(frame, text="Ingredient:", bg="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
            
            ing_entry = ModernEntry(frame, width=25)
            ing_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
            if ingredient:
                ing_entry.insert(0, ingredient)
            
            tk.Label(frame, text="Quantity:", bg="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
            
            qty_entry = ModernEntry(frame, width=20)
            qty_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
            if quantity:
                qty_entry.insert(0, quantity)
            
            def remove_field():
                frame.destroy()
                if (ing_entry, qty_entry) in ingredients_list:
                    ingredients_list.remove((ing_entry, qty_entry))
            
            ModernButton(frame, text="✕ Remove", command=remove_field,
                       bg="#e74c3c", font=("Segoe UI", 9), padx=10).pack(side="left")
            
            ingredients_list.append((ing_entry, qty_entry))
        
        # Add first ingredient field
        add_ingredient_field()
        
        # Button to add more ingredients (outside the scrollable area)
        button_frame = tk.Frame(ingredients_container, bg="white")
        button_frame.pack(side="bottom", fill="x", pady=(5, 0))
        
        ModernButton(button_frame, text="➕ Add Another Ingredient", 
                   command=lambda: add_ingredient_field(),
                   bg="#34495e", font=("Segoe UI", 9)).pack(pady=5)
        
        # Pack ingredients canvas and scrollbar
        ingredients_canvas.pack(side="left", fill="both", expand=True)
        ingredients_scrollbar.pack(side="right", fill="y")
        
        # Instructions
        tk.Label(form_frame, text="Instructions *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=8, column=0, sticky="w", pady=(0, 5))
        
        instructions_text = tk.Text(form_frame, height=10, width=60, font=("Segoe UI", 10), wrap="word")
        instructions_text.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        # Buttons frame (outside form)
        button_frame = tk.Frame(scrollable_frame, bg="#f8f9fa")
        button_frame.pack(pady=20)
        
        def save_recipe():
            try:
                # Validate all inputs
                title = Validator.validate_recipe_title(title_entry.get())
                instructions = Validator.validate_instructions(instructions_text.get("1.0", tk.END))
                prep_time = Validator.validate_prep_time(prep_time_entry.get())
                
                # Get selected categories
                selected_categories = [int(cid) for cid, var in cat_vars.items() if var.get() == 1]
                
                # Get ingredients
                ingredients = []
                for ing_entry, qty_entry in ingredients_list:
                    ing = ing_entry.get().strip()
                    qty = qty_entry.get().strip()
                    if ing:
                        ing, qty = Validator.validate_ingredient(ing, qty)
                        ingredients.append((ing, qty))
                
                if not ingredients:
                    raise ValidationError("At least one ingredient is required")
                
                # Add recipe to database
                recipe_id = self.db.add_recipe(
                    title=title,
                    instructions=instructions,
                    created_by=self.username,
                    category_ids=selected_categories,
                    ingredients=ingredients,
                    prep_time=prep_time
                )
                
                if recipe_id:
                    messagebox.showinfo("Success", f"Recipe '{title}' added successfully!")
                    win.destroy()
                    self.show_dashboard()  # Refresh dashboard
                else:
                    messagebox.showerror("Error", "Failed to add recipe")
                    
            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add recipe: {e}")
        
        ModernButton(button_frame, text="💾 Save Recipe", command=save_recipe,
                   bg="#27ae60", font=("Segoe UI", 12), pady=12, padx=20).pack(side="left", padx=5)
        
        ModernButton(button_frame, text="Cancel", command=win.destroy,
                   bg="#95a5a6", font=("Segoe UI", 12), pady=12, padx=20).pack(side="left", padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_all_recipes_window(self):
        """Show all recipes window with category filtering"""
        win = tk.Toplevel(self.root)
        win.title("All Recipes")
        win.configure(bg='#f8f9fa')
        center(win, 1000, 700)
        win.transient(self.root)  # Make window modal
        win.grab_set()  # Make window modal
        
        # Header
        header_frame = tk.Frame(win, bg="#f8f9fa", padx=20, pady=15)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="📖 All Recipes", 
                font=("Segoe UI", 20, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(side="left")
        
        # Filter frame - ONLY CATEGORY FILTER
        filter_frame = tk.Frame(header_frame, bg="#f8f9fa")
        filter_frame.pack(side="right", fill="x")
        
        # Category filter dropdown
        tk.Label(filter_frame, text="Filter by Category:", 
                font=("Segoe UI", 10), bg="#f8f9fa").pack(side="left", padx=(0, 10))
        
        categories = self.db.all_categories()
        category_var = tk.StringVar(value="All Categories")
        
        category_options = ["All Categories", "Recent Recipes", "Most Popular"]
        category_options.extend([cat[1] for cat in categories])
        
        category_menu = ttk.Combobox(filter_frame, textvariable=category_var, 
                                   values=category_options, width=20, state="readonly")
        category_menu.pack(side="left", padx=(0, 10))
        
        def filter_recipes():
            category_filter = category_var.get()
            
            if category_filter == "All Categories":
                recipes = self.db.all_recipes()
            elif category_filter == "Recent Recipes":
                recipes = self.db.recent_recipes(100)
            elif category_filter == "Most Popular":
                recipes = self.db.most_viewed_recipes(100)
            else:
                # Find category ID
                category_id = None
                for cat in categories:
                    if cat[1] == category_filter:
                        category_id = cat[0]
                        break
                if category_id:
                    recipes = self.db.recipes_by_category(category_id)
                else:
                    recipes = self.db.all_recipes()
            
            display_recipes(recipes)
        
        # Auto-filter when category is selected
        category_menu.bind('<<ComboboxSelected>>', lambda e: filter_recipes())
        
        # Recipes display area
        recipes_display = tk.Frame(win, bg="#f8f9fa")
        recipes_display.pack(fill="both", expand=True, padx=20, pady=10)
        
        def display_recipes(recipes_list):
            # Clear display
            for widget in recipes_display.winfo_children():
                widget.destroy()
            
            if not recipes_list:
                tk.Label(recipes_display, text="No recipes found", 
                        font=("Segoe UI", 14), bg="#f8f9fa", fg="#7f8c8d").pack(pady=50)
                return
            
            # Create canvas for scrolling
            canvas = tk.Canvas(recipes_display, bg="#f8f9fa", highlightthickness=0)
            scrollbar = ttk.Scrollbar(recipes_display, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
            
            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Display recipes in grid
            row, col = 0, 0
            max_cols = 3
            
            for recipe in recipes_list:
                rid = recipe[0]
                title = recipe[1]
                created_by = recipe[4] if len(recipe) > 4 else "Unknown"
                views = recipe[3] if len(recipe) > 3 and recipe[3] is not None else 0
                prep_time = recipe[6] if len(recipe) > 6 and recipe[6] is not None else 0
                
                card = tk.Frame(scrollable_frame, bg="white", bd=1, relief="solid", 
                              padx=12, pady=10, width=250)
                card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                card.grid_propagate(False)
                
                # Recipe title
                display_title = title if len(title) <= 30 else title[:27] + "..."
                title_label = tk.Label(card, text=display_title, font=("Segoe UI", 11, "bold"), 
                                     bg="white", anchor="w", wraplength=220)
                title_label.pack(fill="x", pady=(0, 5))
                
                # Recipe info
                info_text = f"👤 {created_by}"
                if prep_time:
                    info_text += f"\n⏱ {prep_time} min"
                if views:
                    info_text += f"\n👁 {views} views"
                    
                tk.Label(card, text=info_text, font=("Segoe UI", 9), 
                       bg="white", fg="#7f8c8d", anchor="w", justify="left").pack(fill="x", pady=(0, 10))
                
                # Buttons
                btn_frame = tk.Frame(card, bg="white")
                btn_frame.pack(fill="x")
                
                ModernButton(btn_frame, text="View", command=lambda r=rid: self.view_recipe_window(r),
                           bg="#3498db", font=("Segoe UI", 9), padx=15, pady=3).pack(side="left", expand=True, fill="x", padx=(0, 2))
                
                if created_by == self.username or self.user_role == "admin":
                    ModernButton(btn_frame, text="Edit", command=lambda r=rid: self.edit_recipe_window(r),
                               bg="#f39c12", font=("Segoe UI", 9), padx=15, pady=3).pack(side="left", expand=True, fill="x", padx=(2, 0))
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            # Configure grid columns
            for i in range(max_cols):
                scrollable_frame.columnconfigure(i, weight=1)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
        
        # Initial display
        display_recipes(self.db.all_recipes())
    
    def show_admin_window(self):
        """Show admin window"""
        if self.user_role != "admin":
            messagebox.showerror("Access Denied", "Admin access required")
            return
        
        win = tk.Toplevel(self.root)
        win.title("Admin Panel")
        win.configure(bg='#f8f9fa')
        center(win, 1200, 700)
        win.transient(self.root)  # Make window modal
        win.grab_set()  # Make window modal
        
        # Create notebook for admin tabs
        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Dashboard tab
        dashboard_frame = tk.Frame(notebook, bg="#f8f9fa")
        notebook.add(dashboard_frame, text="📊 Dashboard")
        
        self.create_admin_dashboard(dashboard_frame)
        
        # User Management tab
        users_frame = tk.Frame(notebook, bg="#f8f9fa")
        notebook.add(users_frame, text="👥 Users")
        
        self.create_user_management(users_frame)
    
    def create_admin_dashboard(self, parent):
        """Create admin dashboard with system overview"""
        # Header
        header_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=15)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="👑 Admin Dashboard", 
                font=("Segoe UI", 24, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(anchor="w")
        
        # Get system stats
        stats = self.db.get_system_stats()
        
        # Stats cards
        stats_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=10)
        stats_frame.pack(fill="x")
        
        stats_data = [
            ("Total Users", str(stats.get('total_users', 0)), "#e74c3c", "👥"),
            ("Total Recipes", str(stats.get('total_recipes', 0)), "#3498db", "📋"),
            ("Total Views", str(stats.get('total_views', 0)), "#2ecc71", "👁️"),
            ("Total Categories", str(stats.get('total_categories', 0)), "#9b59b6", "🏷️"),
            ("Recent Activity (7d)", str(stats.get('recent_activity', 0)), "#f39c12", "📊"),
            ("New Recipes (7d)", str(stats.get('recent_recipes', 0)), "#1abc9c", "🆕"),
        ]
        
        for i, (title, value, color, icon) in enumerate(stats_data):
            if i % 3 == 0:
                row_frame = tk.Frame(stats_frame, bg="#f8f9fa")
                row_frame.pack(fill="x", pady=5)
            
            card = tk.Frame(row_frame, bg="white", bd=1, relief="solid", padx=15, pady=15)
            card.pack(side="left", expand=True, fill="x", padx=5)
            
            # Icon and value
            top_frame = tk.Frame(card, bg="white")
            top_frame.pack(fill="x")
            
            tk.Label(top_frame, text=icon, font=("Segoe UI", 20), 
                   bg="white", fg=color).pack(side="left", padx=(0, 10))
            tk.Label(top_frame, text=value, font=("Segoe UI", 24, "bold"), 
                   bg="white", fg=color).pack(side="left")
            
            # Title
            tk.Label(card, text=title, font=("Segoe UI", 10), 
                   bg="white", fg="#7f8c8d").pack(anchor="w", pady=(5, 0))
        
        # Top users section
        top_users_frame = tk.LabelFrame(parent, text="🏆 Top Users", 
                                      font=("Segoe UI", 14, "bold"), bg="#f8f9fa", padx=20, pady=15)
        top_users_frame.pack(fill="x", padx=20, pady=20)
        
        if stats.get('top_users'):
            for i, (username, recipe_count, total_views) in enumerate(stats['top_users']):
                user_frame = tk.Frame(top_users_frame, bg="white" if i % 2 == 0 else "#f8f9fa", padx=15, pady=10)
                user_frame.pack(fill="x", pady=2)
                
                # Rank
                rank_colors = ["#FFD700", "#C0C0C0", "#CD7F32", "#3498db", "#2ecc71"]
                rank_color = rank_colors[i] if i < 5 else "#95a5a6"
                tk.Label(user_frame, text=f"{i+1}.", font=("Segoe UI", 12, "bold"), 
                       bg=user_frame['bg'], fg=rank_color, width=4).pack(side="left")
                
                # Username
                tk.Label(user_frame, text=username, font=("Segoe UI", 12), 
                       bg=user_frame['bg'], width=20).pack(side="left", padx=(0, 10))
                
                # Stats
                tk.Label(user_frame, text=f"📋 {recipe_count} recipes", font=("Segoe UI", 10), 
                       bg=user_frame['bg'], fg="#3498db").pack(side="left", padx=(0, 10))
                tk.Label(user_frame, text=f"👁 {total_views} views", font=("Segoe UI", 10), 
                       bg=user_frame['bg'], fg="#2ecc71").pack(side="left", padx=(0, 10))
        else:
            tk.Label(top_users_frame, text="No user data available", 
                    font=("Segoe UI", 12), bg="#f8f9fa", fg="#7f8c8d").pack(pady=20)
    
    def create_user_management(self, parent):
        """Create user management panel with recipe viewing"""
        # Header
        header_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=15)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text="👥 User Management", 
                font=("Segoe UI", 20, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(anchor="w")
        
        # Search frame
        search_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=10)
        search_frame.pack(fill="x")
        
        tk.Label(search_frame, text="Search Username:", font=("Segoe UI", 11), 
                bg="#f8f9fa").pack(side="left", padx=(0, 10))
        
        search_var = tk.StringVar()
        search_entry = ModernEntry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side="left", padx=(0, 10))
        
        def search_users():
            query = search_var.get().strip()
            if not query:
                # If query is empty, show all users
                users = self.db.get_all_users()
            else:
                # Use the FIXED search_users method (searches for exact matches or starts with)
                users = self.db.search_users(query)
            
            for widget in users_display.winfo_children():
                widget.destroy()
            
            if not users:
                tk.Label(users_display, text="No users found", 
                        font=("Segoe UI", 12), bg="#f8f9fa", fg="#7f8c8d").pack(pady=50)
                return
            
            display_users(users)
        
        ModernButton(search_frame, text="🔍 Search", command=search_users,
                   bg="#3498db", padx=15).pack(side="left")
        
        search_entry.bind('<Return>', lambda e: search_users())
        
        # Users display area
        users_display = tk.Frame(parent, bg="#f8f9fa")
        users_display.pack(fill="both", expand=True, padx=20, pady=10)
        
        def display_users(users_list):
            canvas = tk.Canvas(users_display, bg="#f8f9fa", highlightthickness=0)
            scrollbar = ttk.Scrollbar(users_display, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
            
            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            for user in users_list:
                user_id, username, role, created_at, last_login, recipe_count = user
                
                user_card = tk.Frame(scrollable_frame, bg="white", bd=1, relief="solid", padx=15, pady=12)
                user_card.pack(fill="x", pady=5)
                
                # User info
                info_frame = tk.Frame(user_card, bg="white")
                info_frame.pack(fill="x", side="left", expand=True)
                
                # Username and role
                role_icon = "👑" if role == "admin" else "👤"
                tk.Label(info_frame, text=f"{role_icon} {username}", 
                        font=("Segoe UI", 12, "bold"), bg="white", anchor="w").pack(fill="x")
                
                # Additional info
                info_text = f"Role: {role} | Recipes: {recipe_count} | Joined: {created_at}"
                if last_login:
                    info_text += f" | Last Login: {last_login}"
                    
                tk.Label(info_frame, text=info_text, font=("Segoe UI", 9), 
                       bg="white", fg="#7f8c8d", anchor="w").pack(fill="x", pady=(5, 0))
                
                # Action buttons
                action_frame = tk.Frame(user_card, bg="white")
                action_frame.pack(side="right")
                
                # View user's recipes button
                ModernButton(action_frame, text="View Recipes", 
                           command=lambda u=username: self.show_user_recipes(u),
                           bg="#3498db", font=("Segoe UI", 9), padx=10).pack(side="left", padx=2)
                
                # Admin can edit any user's recipes directly from this panel
                ModernButton(action_frame, text="Edit Recipes", 
                           command=lambda u=username: self.show_user_recipes_for_edit(u),
                           bg="#f39c12", font=("Segoe UI", 9), padx=10).pack(side="left", padx=2)
                
                # Don't allow admin to delete their own account
                if username != self.username:
                    ModernButton(action_frame, text="Delete User", 
                               command=lambda u=username: self.delete_user(u),
                               bg="#e74c3c", font=("Segoe UI", 9), padx=10).pack(side="left", padx=2)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
        
        # Initial display - show all users
        display_users(self.db.get_all_users())
    
    def show_user_recipes(self, username):
        """Show recipes created by a specific user"""
        win = tk.Toplevel(self.root)
        win.title(f"Recipes by {username}")
        win.configure(bg='#f8f9fa')
        center(win, 800, 600)
        win.transient(self.root)  # Make window modal
        win.grab_set()  # Make window modal
        
        # Header
        header_frame = tk.Frame(win, bg="#f8f9fa", padx=20, pady=20)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text=f"📝 Recipes by {username}", 
                font=("Segoe UI", 24, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(anchor="w")
        
        # Get user's recipes
        user_recipes = self.db.get_user_recipes(username)
        
        # Stats
        stats_frame = tk.Frame(win, bg="#f8f9fa", padx=20, pady=10)
        stats_frame.pack(fill="x")
        
        total_recipes = len(user_recipes)
        total_views = sum(recipe[2] for recipe in user_recipes) if user_recipes else 0
        
        stats_data = [
            (f"Total Recipes: {total_recipes}", "#3498db"),
            (f"Total Views: {total_views}", "#2ecc71"),
        ]
        
        for i, (text, color) in enumerate(stats_data):
            stat_label = tk.Label(stats_frame, text=text, font=("Segoe UI", 12, "bold"), 
                                bg="#f8f9fa", fg=color)
            stat_label.pack(side="left", padx=(0, 20))
        
        # Recipes display
        recipes_frame = tk.Frame(win, bg="#f8f9fa")
        recipes_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        if not user_recipes:
            tk.Label(recipes_frame, text="No recipes found", 
                    font=("Segoe UI", 14), bg="#f8f9fa", fg="#7f8c8d").pack(pady=50)
            return
        
        # Create canvas for scrolling
        canvas = tk.Canvas(recipes_frame, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(recipes_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for recipe in user_recipes:
            rid, title, views, created_at, prep_time = recipe
            
            recipe_card = tk.Frame(scrollable_frame, bg="white", bd=1, relief="solid", padx=15, pady=12)
            recipe_card.pack(fill="x", pady=5)
            
            # Recipe title
            tk.Label(recipe_card, text=title, font=("Segoe UI", 12, "bold"), 
                   bg="white", anchor="w").pack(fill="x")
            
            # Recipe info
            info_text = f"👤 {username}"
            if prep_time:
                info_text += f" | ⏱ {prep_time} min"
            if views:
                info_text += f" | 👁 {views} views"
            info_text += f" | 📅 {created_at}"
                
            tk.Label(recipe_card, text=info_text, font=("Segoe UI", 10), 
                   bg="white", fg="#7f8c8d", anchor="w").pack(fill="x", pady=(5, 10))
            
            # Buttons - Admin can edit/delete any user's recipe
            btn_frame = tk.Frame(recipe_card, bg="white")
            btn_frame.pack(anchor="e")
            
            ModernButton(btn_frame, text="View", command=lambda r=rid: self.view_recipe_window(r),
                       bg="#3498db", font=("Segoe UI", 10), padx=15).pack(side="left", padx=2)
            
            # Admin can edit any recipe
            if self.user_role == "admin":
                ModernButton(btn_frame, text="Edit", command=lambda r=rid: self.edit_recipe_window(r),
                           bg="#f39c12", font=("Segoe UI", 10), padx=15).pack(side="left", padx=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_user_recipes_for_edit(self, username):
        """Show recipes for editing directly from admin panel"""
        win = tk.Toplevel(self.root)
        win.title(f"Edit Recipes by {username}")
        win.configure(bg='#f8f9fa')
        center(win, 900, 600)
        win.transient(self.root)  # Make window modal
        win.grab_set()  # Make window modal
        
        # Header
        header_frame = tk.Frame(win, bg="#f8f9fa", padx=20, pady=20)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text=f"✏️ Edit Recipes by {username}", 
                font=("Segoe UI", 24, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(anchor="w")
        
        tk.Label(header_frame, text="Admin can edit or delete any user's recipe", 
                font=("Segoe UI", 12), bg="#f8f9fa", fg="#7f8c8d").pack(anchor="w", pady=(0, 10))
        
        # Get user's recipes
        user_recipes = self.db.get_user_recipes(username)
        
        # Stats
        stats_frame = tk.Frame(win, bg="#f8f9fa", padx=20, pady=10)
        stats_frame.pack(fill="x")
        
        total_recipes = len(user_recipes)
        total_views = sum(recipe[2] for recipe in user_recipes) if user_recipes else 0
        
        stats_data = [
            (f"Total Recipes: {total_recipes}", "#3498db"),
            (f"Total Views: {total_views}", "#2ecc71"),
        ]
        
        for i, (text, color) in enumerate(stats_data):
            stat_label = tk.Label(stats_frame, text=text, font=("Segoe UI", 12, "bold"), 
                                bg="#f8f9fa", fg=color)
            stat_label.pack(side="left", padx=(0, 20))
        
        # Recipes display
        recipes_frame = tk.Frame(win, bg="#f8f9fa")
        recipes_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        if not user_recipes:
            tk.Label(recipes_frame, text="No recipes found for this user", 
                    font=("Segoe UI", 14), bg="#f8f9fa", fg="#7f8c8d").pack(pady=50)
            return
        
        # Create canvas for scrolling
        canvas = tk.Canvas(recipes_frame, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(recipes_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        for recipe in user_recipes:
            rid, title, views, created_at, prep_time = recipe
            
            recipe_card = tk.Frame(scrollable_frame, bg="white", bd=1, relief="solid", padx=15, pady=12)
            recipe_card.pack(fill="x", pady=5)
            
            # Recipe title
            tk.Label(recipe_card, text=title, font=("Segoe UI", 12, "bold"), 
                   bg="white", anchor="w").pack(fill="x")
            
            # Recipe info
            info_text = f"👤 {username}"
            if prep_time:
                info_text += f" | ⏱ {prep_time} min"
            if views:
                info_text += f" | 👁 {views} views"
            info_text += f" | 📅 {created_at}"
                
            tk.Label(recipe_card, text=info_text, font=("Segoe UI", 10), 
                   bg="white", fg="#7f8c8d", anchor="w").pack(fill="x", pady=(5, 10))
            
            # Buttons - Admin can edit/delete any user's recipe
            btn_frame = tk.Frame(recipe_card, bg="white")
            btn_frame.pack(anchor="e")
            
            ModernButton(btn_frame, text="View", command=lambda r=rid: self.view_recipe_window(r),
                       bg="#3498db", font=("Segoe UI", 10), padx=15).pack(side="left", padx=2)
            
            # Admin can edit any recipe
            ModernButton(btn_frame, text="Edit", command=lambda r=rid: self.edit_recipe_window(r),
                       bg="#f39c12", font=("Segoe UI", 10), padx=15).pack(side="left", padx=2)
            
            # Admin can delete any recipe
            ModernButton(btn_frame, text="Delete", 
                       command=lambda r=rid, t=title: self.delete_recipe_from_admin(r, t, username),
                       bg="#e74c3c", font=("Segoe UI", 10), padx=15).pack(side="left", padx=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def delete_recipe_from_admin(self, recipe_id, recipe_title, username):
        """Delete a recipe from admin panel"""
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete recipe '{recipe_title}' by {username}?\n\n"
                              f"This action cannot be undone!"):
            if self.db.delete_recipe(recipe_id, self.username):
                messagebox.showinfo("Success", "Recipe deleted successfully!")
                # Refresh the window
                self.show_admin_window()
            else:
                messagebox.showerror("Error", "Failed to delete recipe")
    
    def delete_user(self, username):
        """Delete a user (admin only)"""
        if username == self.username:
            messagebox.showerror("Error", "You cannot delete your own account!")
            return
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Are you sure you want to delete user '{username}'?\n\n"
                              f"This will also delete all their recipes!"):
            try:
                # First, get all recipes by this user
                user_recipes = self.db.execute_safe(
                    "SELECT id FROM recipes WHERE created_by=%s",
                    (username,),
                    "fetchall"
                ) or []
                
                # Delete each recipe (soft delete)
                for recipe in user_recipes:
                    self.db.delete_recipe(recipe[0], self.username)
                
                # Delete user account
                success = self.db.execute_safe(
                    "DELETE FROM users WHERE username=%s",
                    (username,)
                )
                
                if success:
                    messagebox.showinfo("Success", f"User '{username}' deleted successfully!")
                    # Refresh user list
                    self.show_admin_window()
                else:
                    messagebox.showerror("Error", "Failed to delete user")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete user: {e}")
    
    def edit_recipe_window(self, recipe_id):
        """Edit recipe window - Admin can edit any recipe"""
        data = self.db.get_recipe(recipe_id)
        
        if not data:
            messagebox.showerror("Error", "Recipe not found")
            return
        
        meta = data['meta']
        # Allow admin to edit any recipe, regular users only their own
        if meta[4] != self.username and self.user_role != "admin":
            messagebox.showerror("Permission Denied", "You can only edit your own recipes")
            return
        
        win = tk.Toplevel(self.root)
        win.title(f"Edit Recipe: {meta[1]}")
        win.configure(bg='#f8f9fa')
        center(win, 800, 700)
        win.transient(self.root)  # Make window modal
        win.grab_set()  # Make window modal
        
        # Create scrollable frame
        main_frame = tk.Frame(win, bg="#f8f9fa")
        main_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(main_frame, bg="#f8f9fa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f8f9fa")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        title_text = f"✏️ Edit Recipe" if self.user_role != "admin" else f"✏️ Edit Recipe (Admin)"
        tk.Label(scrollable_frame, text=title_text, 
                font=("Segoe UI", 20, "bold"), bg="#f8f9fa", fg="#2c3e50").pack(anchor="w", padx=20, pady=(15, 10))
        
        # Show owner info for admin
        if self.user_role == "admin":
            owner_frame = tk.Frame(scrollable_frame, bg="#f8f9fa", padx=20, pady=5)
            owner_frame.pack(fill="x")
            tk.Label(owner_frame, text=f"Recipe Owner: {meta[4]}", 
                    font=("Segoe UI", 11), bg="#f8f9fa", fg="#7f8c8d").pack(anchor="w")
        
        # Form container
        form_frame = tk.Frame(scrollable_frame, bg="white", bd=1, relief="solid", padx=20, pady=20)
        form_frame.pack(fill="x", padx=20, pady=10)
        
        # Recipe Title
        tk.Label(form_frame, text="Recipe Title *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=0, column=0, sticky="w", pady=(0, 5))
        title_entry = ModernEntry(form_frame, width=50)
        title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        title_entry.insert(0, meta[1])
        
        # Preparation Time
        tk.Label(form_frame, text="Preparation Time (minutes) *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=2, column=0, sticky="w", pady=(0, 5))
        prep_time_entry = ModernEntry(form_frame, width=15)
        prep_time_entry.grid(row=3, column=0, sticky="w", pady=(0, 15))
        prep_time_entry.insert(0, str(meta[6] if meta[6] is not None else 30))
        
        # Categories
        tk.Label(form_frame, text="Categories", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=4, column=0, sticky="w", pady=(0, 5))
        
        # Category selection frame
        cat_frame = tk.Frame(form_frame, bg="white")
        cat_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # Existing categories
        all_categories = self.db.all_categories()
        cat_vars = {}
        current_categories = [cat[0] for cat in data['categories']]
        
        # Create cat_check_frame even if empty
        cat_check_frame = tk.Frame(cat_frame, bg="white")
        cat_check_frame.pack(fill="x", pady=5)
        
        if all_categories:
            tk.Label(cat_frame, text="Select existing categories:", 
                    font=("Segoe UI", 10), bg="white").pack(anchor="w", pady=(0, 5))
            
            for cid, cname in all_categories:
                var = tk.IntVar()
                # Check if this category is currently selected
                if cid in current_categories:
                    var.set(1)
                cb = tk.Checkbutton(cat_check_frame, text=cname, variable=var,
                                  font=("Segoe UI", 9), bg="white")
                cb.pack(side="left", padx=10)
                cat_vars[cid] = var
        else:
            # If no categories exist, show a message
            tk.Label(cat_check_frame, text="No categories yet. Add one below!", 
                    font=("Segoe UI", 9), bg="white", fg="#7f8c8d").pack(pady=5)
        
        # Add new category
        tk.Label(cat_frame, text="Or add new category:", 
                font=("Segoe UI", 10), bg="white").pack(anchor="w", pady=(10, 5))
        
        new_cat_frame = tk.Frame(cat_frame, bg="white")
        new_cat_frame.pack(fill="x")
        
        new_cat_entry = ModernEntry(new_cat_frame, width=30)
        new_cat_entry.pack(side="left", fill="x", expand=True)
        
        def add_new_category():
            try:
                category_name = new_cat_entry.get().strip()
                if not category_name:
                    messagebox.showwarning("Input Error", "Please enter a category name")
                    return
                
                cid = self.db.add_category(category_name)
                if cid:
                    # Clear the "no categories" message if it exists
                    for widget in cat_check_frame.winfo_children():
                        if isinstance(widget, tk.Label) and "No categories" in widget.cget("text"):
                            widget.destroy()
                    
                    # Remove the "Select existing categories:" label if it doesn't exist yet
                    if not all_categories:
                        # Add the label for existing categories
                        tk.Label(cat_frame, text="Select existing categories:", 
                                font=("Segoe UI", 10), bg="white").pack(anchor="w", pady=(0, 5), before=cat_check_frame)
                    
                    # Add checkbox for new category
                    var = tk.IntVar()
                    cb = tk.Checkbutton(cat_check_frame, text=category_name, variable=var,
                                      font=("Segoe UI", 9), bg="white")
                    cb.pack(side="left", padx=10)
                    cat_vars[cid] = var
                    new_cat_entry.delete(0, tk.END)
                    messagebox.showinfo("Success", f"Category '{category_name}' added!")
                else:
                    messagebox.showinfo("Info", f"Category '{category_name}' already exists")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add category: {e}")
        
        ModernButton(new_cat_frame, text="Add Category", command=add_new_category,
                   bg="#9b59b6", padx=15).pack(side="left", padx=5)
        
        # Ingredients with scrollable section
        tk.Label(form_frame, text="Ingredients *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=6, column=0, sticky="w", pady=(0, 5))
        
        # Ingredients container with scrollbar
        ingredients_container = tk.Frame(form_frame, bg="white", height=200)
        ingredients_container.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
        
        # Create canvas and scrollbar for ingredients
        ingredients_canvas = tk.Canvas(ingredients_container, bg="white", highlightthickness=0)
        ingredients_scrollbar = ttk.Scrollbar(ingredients_container, orient="vertical", command=ingredients_canvas.yview)
        ingredients_scrollable_frame = tk.Frame(ingredients_canvas, bg="white")
        
        ingredients_scrollable_frame.bind("<Configure>", lambda e: ingredients_canvas.configure(scrollregion=ingredients_canvas.bbox("all")))
        ingredients_canvas.create_window((0, 0), window=ingredients_scrollable_frame, anchor="nw")
        ingredients_canvas.configure(yscrollcommand=ingredients_scrollbar.set)
        
        ingredients_list = []
        
        def add_ingredient_field(ingredient="", quantity=""):
            frame = tk.Frame(ingredients_scrollable_frame, bg="white")
            frame.pack(fill="x", pady=2, padx=5)
            
            tk.Label(frame, text="Ingredient:", bg="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
            
            ing_entry = ModernEntry(frame, width=25)
            ing_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
            ing_entry.insert(0, ingredient)
            
            tk.Label(frame, text="Quantity:", bg="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
            
            qty_entry = ModernEntry(frame, width=20)
            qty_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
            qty_entry.insert(0, quantity)
            
            def remove_field():
                frame.destroy()
                if (ing_entry, qty_entry) in ingredients_list:
                    ingredients_list.remove((ing_entry, qty_entry))
            
            ModernButton(frame, text="✕ Remove", command=remove_field,
                       bg="#e74c3c", font=("Segoe UI", 9), padx=10).pack(side="left")
            
            ingredients_list.append((ing_entry, qty_entry))
        
        # Add existing ingredients
        for ing, qty in data['ingredients']:
            add_ingredient_field(ing, qty)
        
        # Button to add more ingredients (outside the scrollable area)
        button_frame = tk.Frame(ingredients_container, bg="white")
        button_frame.pack(side="bottom", fill="x", pady=(5, 0))
        
        ModernButton(button_frame, text="➕ Add Another Ingredient", 
                   command=lambda: add_ingredient_field(),
                   bg="#34495e", font=("Segoe UI", 9)).pack(pady=5)
        
        # Pack ingredients canvas and scrollbar
        ingredients_canvas.pack(side="left", fill="both", expand=True)
        ingredients_scrollbar.pack(side="right", fill="y")
        
        # Instructions
        tk.Label(form_frame, text="Instructions *", 
                font=("Segoe UI", 12, "bold"), bg="white").grid(row=8, column=0, sticky="w", pady=(0, 5))
        
        instructions_text = tk.Text(form_frame, height=10, width=60, font=("Segoe UI", 10), wrap="word")
        instructions_text.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        instructions_text.insert("1.0", meta[2])
        
        # Buttons frame
        button_frame = tk.Frame(scrollable_frame, bg="#f8f9fa")
        button_frame.pack(pady=20)
        
        def save_changes():
            try:
                # Validate all inputs
                title = Validator.validate_recipe_title(title_entry.get())
                instructions = Validator.validate_instructions(instructions_text.get("1.0", tk.END))
                prep_time = Validator.validate_prep_time(prep_time_entry.get())
                
                # Get selected categories
                selected_categories = [int(cid) for cid, var in cat_vars.items() if var.get() == 1]
                
                # Get ingredients
                ingredients = []
                for ing_entry, qty_entry in ingredients_list:
                    ing = ing_entry.get().strip()
                    qty = qty_entry.get().strip()
                    if ing:
                        ing, qty = Validator.validate_ingredient(ing, qty)
                        ingredients.append((ing, qty))
                
                if not ingredients:
                    raise ValidationError("At least one ingredient is required")
                
                # Update recipe
                success = self.db.update_recipe(
                    recipe_id=recipe_id,
                    title=title,
                    instructions=instructions,
                    category_ids=selected_categories,
                    ingredients=ingredients,
                    prep_time=prep_time
                )
                
                if success:
                    messagebox.showinfo("Success", f"Recipe '{title}' updated successfully!")
                    win.destroy()
                    self.show_dashboard()  # Refresh dashboard
                else:
                    messagebox.showerror("Error", "Failed to update recipe")
                    
            except ValidationError as e:
                messagebox.showerror("Validation Error", str(e))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update recipe: {e}")
        
        def delete_recipe():
            owner = meta[4] if self.user_role == "admin" else "your"
            if messagebox.askyesno("Confirm Delete", 
                                  f"Are you sure you want to delete {owner} recipe '{meta[1]}'?\n\n"
                                  f"This action cannot be undone!"):
                if self.db.delete_recipe(recipe_id, self.username):
                    messagebox.showinfo("Success", "Recipe deleted successfully!")
                    win.destroy()
                    self.show_dashboard()  # Refresh dashboard
                else:
                    messagebox.showerror("Error", "Failed to delete recipe")
        
        ModernButton(button_frame, text="💾 Save Changes", command=save_changes,
                   bg="#27ae60", font=("Segoe UI", 12), pady=12, padx=20).pack(side="left", padx=5)
        
        ModernButton(button_frame, text="🗑️ Delete Recipe", command=delete_recipe,
                   bg="#e74c3c", font=("Segoe UI", 12), pady=12, padx=20).pack(side="left", padx=5)
        
        ModernButton(button_frame, text="Cancel", command=win.destroy,
                   bg="#95a5a6", font=("Segoe UI", 12), pady=12, padx=20).pack(side="left", padx=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def view_recipe_window(self, recipe_id):
        """View recipe in a new window"""
        self.db.increment_view(recipe_id, self.username)
        data = self.db.get_recipe(recipe_id)
        
        if not data:
            messagebox.showerror("Error", "Recipe not found")
            return
        
        win = tk.Toplevel(self.root)
        win.title(f"Recipe: {data['meta'][1]}")
        win.configure(bg='#f8f9fa')
        center(win, 800, 600)
        win.transient(self.root)  # Make window modal
        win.grab_set()  # Make window modal
        
        # Create notebook for recipe sections
        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Overview tab
        overview_frame = tk.Frame(notebook, bg="#f8f9fa")
        notebook.add(overview_frame, text="📖 Overview")
        
        self.display_recipe_overview(overview_frame, data)
        
        # Ingredients tab
        ingredients_frame = tk.Frame(notebook, bg="#f8f9fa")
        notebook.add(ingredients_frame, text="🥕 Ingredients")
        
        self.display_recipe_ingredients(ingredients_frame, data)
        
        # Instructions tab
        instructions_frame = tk.Frame(notebook, bg="#f8f9fa")
        notebook.add(instructions_frame, text="👨‍🍳 Instructions")
        
        self.display_recipe_instructions(instructions_frame, data)
    
    def display_recipe_overview(self, parent, data):
        meta = data['meta']
        cats = [c[1] for c in data['categories']]
        
        # Header
        header_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=15)
        header_frame.pack(fill="x")
        
        tk.Label(header_frame, text=meta[1], font=("Segoe UI", 24, "bold"), 
                bg="#f8f9fa", fg="#2c3e50").pack(anchor="w")
        
        # Recipe stats
        prep_time = meta[6] if meta[6] is not None else 0
        views = meta[3] if meta[3] is not None else 0
        
        stats_text = f"👤 By {meta[4]} | ⏱ {prep_time} minutes | 👁 {views} views | 📅 {meta[5]}"
        tk.Label(header_frame, text=stats_text, font=("Segoe UI", 12), 
                bg="#f8f9fa", fg="#7f8c8d").pack(anchor="w", pady=5)
        
        # Categories
        if cats:
            tk.Label(header_frame, text="🏷️ " + ", ".join(cats), font=("Segoe UI", 11), 
                    bg="#f8f9fa", fg="#3498db").pack(anchor="w")
        
        # Action buttons (for owner or admin)
        if meta[4] == self.username or self.user_role == "admin":
            action_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=10)
            action_frame.pack(fill="x")
            
            ModernButton(action_frame, text="✏️ Edit Recipe", 
                       command=lambda: self.edit_recipe_window(meta[0]),
                       bg="#f39c12", font=("Segoe UI", 11)).pack(side="left", padx=(0, 10))
    
    def display_recipe_ingredients(self, parent, data):
        ingredients = data['ingredients']
        
        content_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=15)
        content_frame.pack(fill="both", expand=True)
        
        if not ingredients:
            tk.Label(content_frame, text="No ingredients listed", 
                    font=("Segoe UI", 12), bg="#f8f9fa", fg="#7f8c8d").pack(pady=20)
            return
        
        for i, (ingredient, quantity) in enumerate(ingredients):
            ing_frame = tk.Frame(content_frame, bg="white", bd=1, relief="solid", padx=15, pady=10)
            ing_frame.pack(fill="x", pady=5)
            
            tk.Label(ing_frame, text=f"• {ingredient}", font=("Segoe UI", 11, "bold"), 
                   bg="white", anchor="w").pack(side="left", fill="x", expand=True)
            tk.Label(ing_frame, text=quantity, font=("Segoe UI", 11), 
                   bg="white", fg="#7f8c8d").pack(side="right")
    
    def display_recipe_instructions(self, parent, data):
        instructions = data['meta'][2]
        
        content_frame = tk.Frame(parent, bg="#f8f9fa", padx=20, pady=15)
        content_frame.pack(fill="both", expand=True)
        
        text_widget = tk.Text(content_frame, wrap="word", font=("Segoe UI", 11), 
                            padx=10, pady=10, bg="white", relief="flat", height=20)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.insert("1.0", instructions)
        text_widget.config(state="disabled")
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def logout(self):
        """Handle user logout"""
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.root.destroy()
            root = tk.Tk()
            RoleSelector(root, self.db)
            root.mainloop()

# ---------------- Role Selector ----------------
class RoleSelector:
    def __init__(self, root, db: Database):
        self.root = root
        self.db = db
        self.root.title("Recipe Manager - Welcome")
        self.root.configure(bg='#f8f9fa')
        center(self.root, 800, 500)
        self.build_ui()

    def build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#f8f9fa", pady=30)
        header.pack(fill="x")
        
        tk.Label(header, text="🍳 Recipe Manager", font=("Segoe UI", 32, "bold"), 
                bg="#f8f9fa", fg="#2c3e50").pack()
        tk.Label(header, text="Your digital recipe collection", font=("Segoe UI", 14), 
                bg="#f8f9fa", fg="#7f8c8d").pack(pady=5)
        
        # Role selection cards
        body = tk.Frame(self.root, bg="#f8f9fa")
        body.pack(expand=True, fill="both", padx=50, pady=30)
        
        # User card
        user_card = self.create_role_card(body, "👤 User", "Browse and manage your recipes", 
                                        "#3498db", 0)
        
        # Admin card  
        admin_card = self.create_role_card(body, "👑 Admin", "Manage users and system analytics",
                                         "#e74c3c", 1)
        
        # Footer
        footer = tk.Frame(self.root, bg="#f8f9fa", pady=20)
        footer.pack(fill="x")
        
        tk.Label(footer, text="Select your role to continue", font=("Segoe UI", 11),
                bg="#f8f9fa", fg="#7f8c8d").pack()

    def create_role_card(self, parent, title, description, color, column):
        card = tk.Frame(parent, bg="white", bd=1, relief="solid", padx=25, pady=25)
        card.grid(row=0, column=column, padx=20, sticky="nsew")
        parent.columnconfigure(column, weight=1)
        
        # Title
        tk.Label(card, text=title, font=("Segoe UI", 18, "bold"), 
                bg="white", fg=color).pack(anchor="w")
        
        # Description
        tk.Label(card, text=description, font=("Segoe UI", 11), 
                bg="white", fg="#7f8c8d", wraplength=250, justify="left").pack(anchor="w", pady=10)
        
        # Buttons
        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(fill="x", pady=(15, 0))
        
        role = "user" if "User" in title else "admin"
        
        ModernButton(btn_frame, text="Login", command=lambda r=role: LoginDialog(self.root, self.db, r),
                   bg=color, font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        
        ModernButton(btn_frame, text="Register", command=lambda r=role: RegisterDialog(self.root, self.db, r),
                   bg="#95a5a6", font=("Segoe UI", 10)).pack(side="left")
        
        return card

# ---------------- Login Dialog ----------------
class LoginDialog:
    def __init__(self, parent, db: Database, role="user"):
        self.db = db
        self.role = role
        self.win = tk.Toplevel(parent)
        self.win.title(f"{role.title()} Login")
        self.win.configure(bg='#f8f9fa')
        center(self.win, 400, 320)
        self.win.transient(parent)  # Make window modal
        self.win.grab_set()  # Make window modal
        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.win, bg="#f8f9fa", padx=30, pady=30)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        role_icon = "👑" if self.role == "admin" else "👤"
        tk.Label(main_frame, text=f"{role_icon} {self.role.title()} Login", 
                font=("Segoe UI", 18, "bold"), bg="#f8f9fa").pack(pady=(0, 20))
        
        # Username
        tk.Label(main_frame, text="Username", font=("Segoe UI", 11, "bold"), 
                bg="#f8f9fa").pack(anchor="w", pady=(10, 5))
        self.user_entry = ModernEntry(main_frame, width=30)
        self.user_entry.pack(fill="x", pady=(0, 15))
        self.user_entry.focus()
        
        # Password
        tk.Label(main_frame, text="Password", font=("Segoe UI", 11, "bold"), 
                bg="#f8f9fa").pack(anchor="w", pady=(5, 5))
        self.pass_entry = ModernEntry(main_frame, width=30, show="•")
        self.pass_entry.pack(fill="x", pady=(0, 20))
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg="#f8f9fa")
        btn_frame.pack(fill="x", pady=10)
        
        ModernButton(btn_frame, text="Login", command=self.login, 
                   bg="#27ae60", font=("Segoe UI", 11)).pack(side="left", padx=(0, 10))
        
        ModernButton(btn_frame, text="Cancel", command=self.win.destroy,
                   bg="#95a5a6", font=("Segoe UI", 11)).pack(side="left")
        
        # Bind Enter key to login
        self.win.bind('<Return>', lambda e: self.login())

    def login(self):
        try:
            username = self.user_entry.get().strip()
            password = self.pass_entry.get().strip()
            
            if not username or not password:
                messagebox.showwarning("Input Error", "Please enter both username and password")
                return
            
            user_role = self.db.login_user(username, password)
            
            if user_role is None:
                messagebox.showerror("Login Failed", "Invalid username or password")
                return
            
            if self.role == "admin" and user_role != "admin":
                messagebox.showerror("Access Denied", "Admin login requires admin privileges")
                return
            
            self.win.destroy()
            self.win.master.destroy()  # Close the role selector window
            root = tk.Tk()
            RecipeApp(root, self.db, username=username, user_role=user_role)
            root.mainloop()
                
        except Exception as e:
            messagebox.showerror("Login Error", f"An error occurred during login: {e}")

# ---------------- Register Dialog ----------------
class RegisterDialog:
    def __init__(self, parent, db: Database, role="user"):
        self.db = db
        self.role = role
        self.win = tk.Toplevel(parent)
        self.win.title(f"Register as {role.title()}")
        self.win.configure(bg='#f8f9fa')
        center(self.win, 400, 450)
        self.win.transient(parent)  # Make window modal
        self.win.grab_set()  # Make window modal
        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.win, bg="#f8f9fa", padx=30, pady=30)
        main_frame.pack(fill="both", expand=True)
        
        role_icon = "👑" if self.role == "admin" else "👤"
        tk.Label(main_frame, text=f"{role_icon} Register as {self.role.title()}", 
                font=("Segoe UI", 18, "bold"), bg="#f8f9fa").pack(pady=(0, 20))
        
        # Username
        tk.Label(main_frame, text="Username", font=("Segoe UI", 11, "bold"), 
                bg="#f8f9fa").pack(anchor="w", pady=(5, 5))
        self.user_entry = ModernEntry(main_frame, width=30)
        self.user_entry.pack(fill="x", pady=(0, 10))
        
        # Password
        tk.Label(main_frame, text="Password", font=("Segoe UI", 11, "bold"), 
                bg="#f8f9fa").pack(anchor="w", pady=(5, 5))
        self.pass_entry = ModernEntry(main_frame, width=30, show="•")
        self.pass_entry.pack(fill="x", pady=(0, 10))
        
        # Confirm Password
        tk.Label(main_frame, text="Confirm Password", font=("Segoe UI", 11, "bold"), 
                bg="#f8f9fa").pack(anchor="w", pady=(5, 5))
        self.confirm_pass_entry = ModernEntry(main_frame, width=30, show="•")
        self.confirm_pass_entry.pack(fill="x", pady=(0, 20))
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg="#f8f9fa")
        btn_frame.pack(fill="x", pady=10)
        
        ModernButton(btn_frame, text="Register", command=self.register,
                   bg="#27ae60", font=("Segoe UI", 11)).pack(side="left", padx=(0, 10))
        
        ModernButton(btn_frame, text="Cancel", command=self.win.destroy,
                   bg="#95a5a6", font=("Segoe UI", 11)).pack(side="left")
        
        # Bind Enter key
        self.win.bind('<Return>', lambda e: self.register())

    def register(self):
        try:
            username = self.user_entry.get().strip()
            password = self.pass_entry.get().strip()
            confirm_password = self.confirm_pass_entry.get().strip()
            
            if not username or not password:
                messagebox.showwarning("Input Error", "Please enter both username and password")
                return
            
            if password != confirm_password:
                messagebox.showerror("Registration Error", "Passwords do not match!")
                return
            
            # For admin registration, check passphrase
            if self.role == "admin":
                secret = simpledialog.askstring("Admin Passphrase", 
                                              "Enter admin creation passphrase:", 
                                              show="*")
                if not secret:
                    return  # User cancelled
                
                if secret != CREATE_ADMIN_PASSPHRASE:
                    messagebox.showerror("Access Denied", "Invalid admin passphrase!")
                    return
            
            # Try to register the user
            success = self.db.register_user(username, password, role=self.role)
            
            if success:
                messagebox.showinfo("Success", f"Registration successful! You can now login as {self.role}.")
                self.win.destroy()
            else:
                messagebox.showerror("Registration Failed", "Registration failed. Username may already exist.")
                    
        except ValidationError as e:
            messagebox.showerror("Validation Error", str(e))
        except DatabaseError as e:
            messagebox.showerror("Registration Error", str(e))
        except Exception as e:
            messagebox.showerror("Registration Error", f"An unexpected error occurred: {e}")

# ---------------- Main Application Entry Point ----------------
if __name__ == "__main__":
    try:
        # Initialize database
        db = Database()
        
        # Create main window
        root = tk.Tk()
        
        # Set application icon and title
        root.title("Recipe Manager")
        
        # Start with role selector
        RoleSelector(root, db)
        
        # Start main loop
        root.mainloop()
        
    except DatabaseError as e:
        logging.critical(f"Database initialization failed: {e}")
        messagebox.showerror("Database Error", f"Cannot connect to database:\n{e}")
    except Exception as e:
        logging.critical(f"Application failed to start: {e}")
        messagebox.showerror("Fatal Error", f"Application failed to start:\n{e}")
