from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
from flask_paginate import Pagination, get_page_args
from math import ceil
from flask import jsonify


app = Flask(__name__)

# Function to get pagination parameters
def get_paginated_crypto_data(offset=0, per_page=20):
    return list(collection.find().skip(offset).limit(per_page))

# Connect to MongoDB
client = MongoClient("mongodb+srv://admin:admin@cluster0.476b0ts.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['crypto']
collection = db['crypto_table']

# Define datetimeformat filter
def datetimeformat(value):
    # Convert UTC timestamp to EDT (Eastern Daylight Time - GMT-4)
    utc_time = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
    eastern = pytz.timezone('America/New_York')
    edt_time = utc_time.replace(tzinfo=pytz.utc).astimezone(eastern)
    return edt_time.strftime('%Y-%m-%d %H:%M:%S')

# Register datetimeformat filter with Jinja2
app.jinja_env.filters['datetimeformat'] = datetimeformat

# Pagination configuration
PER_PAGE = 20

def get_paginated_data(offset=0):
    return collection.find().skip(offset).limit(PER_PAGE)

# Add a new route for the charts page
@app.route('/charts')
def charts():
    # Fetch data for line chart (Bitcoin prices over time)
    bitcoin_data = list(collection.find({'symbol': 'BTC'}, {'_id': 0, 'timestamp': 1, 'price': 1}))
    bitcoin_data = [{'timestamp': entry['timestamp'], 'price': entry['price']} for entry in bitcoin_data]

    # Fetch data for bar chart (Top 5 cryptocurrencies by maximum price)
    top_cryptos_data = list(collection.aggregate([
        {
            "$group": {
                "_id": "$symbol",
                "maxPrice": {"$max": "$price"}
            }
        },
        {"$sort": {"maxPrice": -1}},
        {"$limit": 5}
    ]))

    top_cryptos_data = [{'symbol': entry['_id'], 'price': entry['maxPrice']} for entry in top_cryptos_data]

    return render_template('charts.html', bitcoin_data=bitcoin_data, top_cryptos_data=top_cryptos_data)


@app.route('/')
def index():
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    total = collection.count_documents({})
    pagination_crypto_data = get_paginated_data(offset=offset)

    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')

    total_pages = ceil(total / per_page)  # Calculate total pages
    return render_template('index.html', crypto_data=pagination_crypto_data, page=page, per_page=per_page, pagination=pagination, total_pages=total_pages)


@app.route('/filter', methods=['GET', 'POST'])
def filtered_data():
    if request.method == 'POST':
        cryptos = request.form.get('cryptos')
        selected_crypto_symbols = [symbol.strip() for symbol in cryptos.split(',')]

        # Pagination parameters
        page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')

        # Fetch filtered data based on pagination parameters
        filtered_crypto_data = collection.find({'symbol': {'$in': selected_crypto_symbols}}).skip(offset).limit(per_page)
        
        # Total count of filtered data
        total = collection.count_documents({'symbol': {'$in': selected_crypto_symbols}})

        # Calculate total pages
        total_pages = ceil(total / per_page)

        pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')

        return render_template('filtered.html', crypto_data=filtered_crypto_data, pagination=pagination, cryptos=cryptos, total_pages=total_pages)
    else:
        # Handle GET request
        return render_template('filtered.html', crypto_data=[], pagination=None)

    
if __name__ == "__main__":
    app.run(debug=True)
