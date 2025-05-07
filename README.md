# 📦 Inventory Management System

A Dockerized, scalable, and secure Inventory Management System built with Django.  
Designed for companies to efficiently manage their stock while supporting role-based access for admins and staff, with PostgreSQL as the backend database.

---

## 🚀 Features

- 🔐 Secure login & session management
- 📊 Admin & staff dashboards
- 📦 Inventory tracking, creation, and update
- 👤 Admin user management (add/remove/update users, assign roles)
- 🧩 Modular, scalable Django architecture
- 🐳 Dockerized for easy development & deployment
- 🌍 Environment-variable-based configuration for production safety

---

## 🛠 Technologies Used

- **Python 3.11**
- **Django**
- **PostgreSQL**
- **Docker & Docker Compose**
- **Gunicorn**
- **HTML/CSS/Bootstrap** for frontend templates

---

## 📁 Project Structure (Highlights)

```plaintext
Inventory-Management-System/
│
├── Inventory_MS/               # Main Django project
├── IMS_production/                  # for database
├── authentication/                      # Custom user management
├── permission/                      # permission management
├── IMS_admin/                      # for dashboard of admin
├── IMS_staff/                      # for dashboard of staff
├── staticfiles/                      # for static files
├── entrypoint.sh               # Docker entry script (runs migrations, creates superuser)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                        # Environment variables (excluded in .gitignore)
└── README.md


Here’s an updated and professional `README.md` file for your Django-based Inventory Management System, complete with Docker and environment setup instructions based on your current project:

---

````markdown
# 📦 Inventory Management System

A Dockerized, scalable, and secure Inventory Management System built with Django.  
Designed for companies to efficiently manage their stock while supporting role-based access for admins and staff, with PostgreSQL as the backend database.

---

## 🚀 Features

- 🔐 Secure login & session management
- 📊 Admin & staff dashboards
- 📦 Inventory tracking, creation, and update
- 👤 Admin user management (add/remove/update users, assign roles)
- 🧩 Modular, scalable Django architecture
- 🐳 Dockerized for easy development & deployment
- 🌍 Environment-variable-based configuration for production safety

---

## 🛠 Technologies Used

- **Python 3.11**
- **Django**
- **PostgreSQL**
- **Docker & Docker Compose**
- **Gunicorn**
- **HTML/CSS/Bootstrap** for frontend templates

---

## 📁 Project Structure (Highlights)

```plaintext
Inventory-Management-System/
│
├── Inventory_MS/               # Main Django project
├── inventory/                  # Inventory app
├── users/                      # Custom user management
├── entrypoint.sh               # Docker entry script (runs migrations, creates superuser)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                        # Environment variables (excluded in .gitignore)
└── README.md
````

---

## ⚙️ Setup & Installation (Dockerized)

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Iradukunda-Fils/Inventory-Management-System.git
cd Inventory-Management-System
```

### 2️⃣ Create a `.env` file

Create a `.env` file in the project root:

```env
DEBUG=False
SECRET_KEY=your-django-secret-key
ALLOWED_HOSTS="*"

DATABASE_NAME=inventory
DATABASE_USER=postgres
PASSWORD=your-db-password
DATABASE_HOST=db
PORT=5432

DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin123
```

### 3️⃣ Build and run with Docker Compose

```bash
docker-compose up --build
```

This will:

* Build the Docker containers
* Apply migrations
* Create a Django superuser automatically using environment variables
* Run the app via Gunicorn on `localhost:8000`

---

## ✅ Creating a Superuser (Optional)

If not automatically created or you want to do it manually:

```bash
docker exec -it inventory_ms python manage.py createsuperuser
```

---

## 🧪 Testing Database Connection

Access the PostgreSQL container:

```bash
docker exec -it postgres psql -U postgres -d inventory
```

---

## 📎 Additional Notes

* Static files are collected using `collectstatic` during image build.
* Default Django admin can be accessed at `/admin/`.
* Staff/admin role-based permissions are handled in the `users` app.

---

## 🙌 Contributing

Feel free to fork this repo, make improvements, and submit a pull request!

---

## 📄 License

This project is licensed under the MIT License.

---

## 👤 Author

**Iradukunda Fils**
[GitHub](https://github.com/Iradukunda-Fils)

**Youtube Channel to subscribe for learning programming in Kinyarwanda**
[Youtube] (https://www.youtube.com/@digitalrwanda)

```

---

Would you like a separate `.env.example` template to include in your repo as well?
```
