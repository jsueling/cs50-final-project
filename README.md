# MyPortfolios

This project was created as the final project for Harvard's [CS50x](https://cs50.harvard.edu/x/) course.

**Video Demo:** [https://www.youtube.com/watch?v=5i8XTZZDeNs](https://www.youtube.com/watch?v=5i8XTZZDeNs)

<img width="2112" height="1632" alt="CS50" src="https://github.com/user-attachments/assets/3ee4cbe0-274c-4224-a7f2-40b22e449ede" />

## ⚠️ Project Status: Archived

This project is no longer actively maintained or deployed. The IEX Cloud API, which was used for fetching stock data, has since changed its service offerings, which prevents the application from functioning as originally designed. The code is preserved here for archival and demonstration purposes.

---

## Overview

MyPortfolios is a web application for tracking and visualising stock portfolios, inspired by the CS50 Finance project. It expands on the core concepts by introducing a unique portfolio visualisation feature that provides clarity on portfolio performance and the relative performance between different share purchases.

The application is built using Python and Flask for the back-end, JavaScript for front-end interactivity, and PostgreSQL for the database. It is deployed on Heroku and uses the IEX Cloud API to fetch stock price data.

## Key Features

*   **Portfolio Visualisation:** The main feature is a stacked horizontal bar chart that represents the user's current portfolio. This chart is generated dynamically using only CSS Flexbox and HTML.
*   **Relative Performance:** Each segment of the bar represents a specific share purchase. The size of the segment is relative to the gain or loss of the best-performing asset in the portfolio, making it easy to see the relative contribution of each holding.
*   **Interactive Chart:** Mousing over a bar segment causes it to grow, highlighting its performance details, including its percentage contribution to the portfolio's overall net profit. Clicking a segment navigates to a detailed view of that specific purchase.
*   **User & Portfolio Management:** Users can register, create multiple portfolios, add or remove share purchases, and delete portfolios or their entire account.
*   **Historical Data:** The app fetches historical prices to calculate performance from the date of purchase to the present day. It intelligently handles non-trading days (weekends, holidays) by finding the nearest available trading day's data.

## Technology Stack

*   **Back-End:** Python, Flask
*   **Front-End:** HTML, CSS, JavaScript, Bootstrap
*   **Database:** PostgreSQL (Production), SQLite (Development)
*   **API:** IEX Cloud API for stock data
*   **Deployment:** Heroku

## Setup and Installation

To run this project locally, you will need to configure the following:

1.  **Clone the repository:**
    ````bash
    git clone <your-repository-url>
    cd cs50-final-project
    ````
2.  **Install dependencies:**
    ````bash
    pip install -r requirements.txt
    ````
3.  **Set Environment Variables:** The application requires an API key from IEX Cloud and a database URL. Create a `.env` file in the root directory:
    ````
    API_KEY="your_iex_cloud_api_key"
    DATABASE_URL="your_database_url"
    ````
4.  **Run the application:**
    ````bash
    flask run
    ````

## Database Schema

The application uses three tables to manage user data, portfolios, and shares.

````sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolios (
    id INT REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
    portfolio_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS shares (
    symbol VARCHAR(50) NOT NULL,
    purchase_quantity INT NOT NULL CHECK (purchase_quantity > 0),
    purchase_price NUMERIC NOT NULL CHECK (purchase_price > 0),
    purchase_date DATE NOT NULL,
    portfolio_name VARCHAR(50) REFERENCES portfolios (portfolio_name) ON DELETE CASCADE ON UPDATE CASCADE,
    id INT REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
);
