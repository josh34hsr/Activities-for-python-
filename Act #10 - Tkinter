import tkinter as tk
from tkinter import messagebox
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # default XAMPP password is empty
    database="login_db"
)

cursor = db.cursor()

def login_page():
    global login_window
    login_window = tk.Tk()
    login_window.title("Login")
    login_window.geometry("300x230")
    login_window.config(bg="lightblue")

    tk.Label(login_window, text="Login", font=("Arial", 16, "bold"), bg="lightblue").pack(pady=10)

    tk.Label(login_window, text="Username", bg="lightblue").pack()
    user_entry = tk.Entry(login_window, width=25)
    user_entry.pack()

    tk.Label(login_window, text="Password", bg="lightblue").pack()
    pass_entry = tk.Entry(login_window, width=25, show="*")
    pass_entry.pack()

    def login():
        username = user_entry.get()
        password = pass_entry.get()

        cursor.execute("SELECT * FROM accounts WHERE username=%s AND password=%s", (username, password))
        result = cursor.fetchone()

        if result:
            messagebox.showinfo("Success", "Login Successful!")
        else:
            messagebox.showerror("Failed", "Invalid Username or Password")

    def open_register():
        login_window.destroy()
        register_page()

    tk.Button(login_window, text="Login", command=login, bg="green", fg="white", width=10).pack(pady=5)
    tk.Button(login_window, text="Register", command=open_register, bg="blue", fg="white", width=10).pack()
    tk.Button(login_window, text="Exit", command=login_window.destroy, bg="red", fg="white", width=10).pack(pady=5)

    login_window.mainloop()

def register_page():
    global register_window
    register_window = tk.Tk()
    register_window.title("Register")
    register_window.geometry("300x230")
    register_window.config(bg="lightyellow")

    tk.Label(register_window, text="Create Account", font=("Arial", 16, "bold"), bg="lightyellow").pack(pady=10)

    tk.Label(register_window, text="New Username", bg="lightyellow").pack()
    new_user = tk.Entry(register_window, width=25)
    new_user.pack()

    tk.Label(register_window, text="New Password", bg="lightyellow").pack()
    new_pass = tk.Entry(register_window, width=25, show="*")
    new_pass.pack()

    def register():
        username = new_user.get()
        password = new_pass.get()

        try:
            cursor.execute("INSERT INTO accounts (username, password) VALUES (%s, %s)", (username, password))
            db.commit()
            messagebox.showinfo("Success", "Account Created!")
            register_window.destroy()
            login_page()
        except:
            messagebox.showerror("Error", "Username already exists!")

    def back():
        register_window.destroy()
        login_page()

    tk.Button(register_window, text="Register", command=register, bg="green", fg="white", width=10).pack(pady=5)
    tk.Button(register_window, text="Back", command=back, bg="blue", fg="white", width=10).pack()
    tk.Button(register_window, text="Exit", command=register_window.destroy, bg="red", fg="white", width=10).pack(pady=5)

    register_window.mainloop()

# Run login page
login_page()
