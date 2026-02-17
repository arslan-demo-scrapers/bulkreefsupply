# Bulk Reef Supply Inventory Scraper

## Project Overview

This web scraper designed to monitor and extract product inventory data from www.bulkreefsupply.com.

The scraper implements a custom Binary Search Algorithm to minimize HTTP requests, reducing proxy costs by 60% while maintaining high data accuracy.

---

# Setup & Installation Guide

## Virtual Environment Setup

This project is built using Python 3.

If you need help creating a virtual environment, refer to:

https://www.geeksforgeeks.org/python-virtual-environment/

After installing Python 3, create and activate a virtual environment:

```bash
python3 -m venv my_venv
source my_venv/bin/activate
```
---
## Step 1 – Install IDE

Install an IDE to manage the project.

Recommended:

PyCharm Community Edition

After installation, open the extracted project folder in PyCharm.

---

## Step 2 – Install Required Dependencies

Open the terminal inside PyCharm and install the required modules:

```bash
pip install Scrapy==2.6.3
pip install scrapy-crawlera==1.7.2
pip install python-dotenv==0.21.1
pip install scrapeops-scrapy-proxy-sdk==1.0
```

Alternative – Install Using requirements.txt

If a requirements.txt file is available, run:

> pip install -r requirements.txt

**Troubleshooting Installation Issues**

If you face dependency or compilation issues:

[Download compiled Windows libraries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#twisted)

Fix broken Python installation (Linux):

sudo apt install --reinstall python3 python python3-minimal --fix-broken

**Important Note**

Make sure your Project Interpreter in PyCharm is set to the environment where Scrapy and dependencies are installed.

---

##  Running the Spider
##  Step 3 – Navigate to Spiders Directory

Before running the spider, ensure you are inside:

`/bulkreefsupply/bulkreefsupply/spiders`

Run the Spider
> python3 -m bulkreefsupply_spider.py

Run Spider in Background (Linux Server)\
> nohup python3 -m scrapy crawl bulkreefsupply_spider &

This spider extracts products information from the website and store the structured data in CSV file.

---

##  Output Data

After successful execution: Navigate to the output directory. You will find the file `bulkreefsupply_products.csv`

This CSV file contains structured product inventory data extracted from the website.

---

##  Support

For any questions, configuration issues, or assistance, please feel free to reach out.

Kind regards,
Arslan Shakar
