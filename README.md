# Café Management System

This project is a full-stack web application built to streamline the ordering process for both café customers and staff.

**About This Project**:
I developed this application as a testing project to expand my knowledge of the Django framework. My goal was to build a "production-style" product. It tackles real-world development challenges such as dual-role user flows, containerization with Docker, integrating REST APIs with traditional server-side rendering, and managing time-sensitive database records.

*Note: The whole app's interface is made in the Czech language.*

## Features

### Dual-Role System

The application serves two distinct user types with tailored interfaces:

  * **Customers:** Can view table-specific information via scanned QR codes, browse the menu, order drinks, and track the real-time status of their table's orders.
  * **Employees:** Have access to a dedicated dashboard to manage incoming orders. They can track the remaining time to accept or complete an order, update order statuses, and clear out old, completed orders.

### Technical Highlights

  * **Hybrid Rendering:** Uses classic Django template rendering for the main interfaces, supplemented by custom REST API endpoints for dynamic data fetching.
  * **Database & Storage:** Powered by a **PostgreSQL** database for storage of customers, staff, orders, and menu items.
  * **Smart Ordering:** Orders are sorted by time and include automated time limits for staff action.
  * **QR Code Integration:** Utilizes `django-qr-code` to generate unique, scannable QR codes for each table.
  * **Security:** Features a custom token-based authentication system for seamless employee logins, with all passwords securely hashed using Django's native cryptographic functions.
  * **Automated Testing:** Includes a suite of tests covering Models, Views, and others (like order time limits) to ensure stability.

-----

## Getting Started

### Prerequisites

Make sure you have [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed.

### Installation

To start the application, simply start up the Docker containers:

```bash
docker compose up --build
```

### Initial Setup & Test User

To run the Django app properly, you should create a `.env` file. You should use the `.env.example` file to see how it should look like. It's recommended to keep everything in the example file other than the secret key. You should generate that key using Django or [here](https://djecrety.ir/) on the web.

To test the admin panel, you can use the pre-configured test user:

  * **Username:** `admin`
  * **Password:** `1234`

*Note: For the customer view to work, you will need to log into the admin panel and create at least one Table and a few Drink items. You also will need to create a Staff User in the admin panel to access the employee dashboard.* 

-----

## Navigation & URLs

Once the Docker container is running, you can access the following routes:

  * **Employee Dashboard:** [`http://localhost:8000/staff/`](http://localhost:8000/staff/)
      * *Requires registration/login via the UI or using the test user above.*
  * **Django Admin Panel:** [`http://localhost:8000/admin/`](http://localhost:8000/admin/)
  * **Customer View (Table Info):** [`http://localhost:8000/table/<uuid>/`](http://localhost:8000/table/)
      * *Replace the UUID with a valid table ID generated in your database.*

-----

## Running Tests

Tests have been written to verify the integrity of the application. **Note:** These commands work only when the Docker container running the application is active.

You can run the tests locally:

```bash
python manage.py test
```

Or execute them directly inside the running web container:

```bash
docker compose exec web python manage.py test
```