from flask import Flask, render_template, request,redirect,session
import openai
import re
import mysql.connector
from config_db import openai, create_database_connection
#from customers import app as customers_app
from customers import customers_bp

app = Flask(__name__)
app.secret_key = '112233'
app.register_blueprint(customers_bp)

openai.api_key = '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'

db_connection = mysql.connector.connect(
    host="198.12.233.20",
    user="ai_qrvino_user",
    password="ai_qrvino_user",
    database="ai_qrvino"
)

db_connection = create_database_connection()
cursor = db_connection.cursor(dictionary=True)

def get_chatbot_response(messages):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    return response.choices[0].message["content"]


def extract_clickable_headings(response):
    headings = re.findall(r'(\w+(?:\/\w+)?)\: (?:.|\n)+?(?=\n\n|$)', response)
    formatted_response = re.sub(r'(\w+(?:\/\w+)?)\: ((?:.|\n)+?)(?=\n\n|$)', '- <a href="#\\1">\\1</a>: \\2<br>', response)
    return formatted_response, headings

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form.get("user_input")
        wine_option = request.form.get('wine_option')
        customer_name = request.form.get('customer_name')
        if customer_name:
           return redirect("/chatGPT_response_table?chatbot_input=" + user_input + "&chatbot_radio=" + wine_option + "&customerName=" + customer_name)
        else:
            return redirect("/chatGPT_response?chatbot_input=" + user_input + "&chatbot_radio=" + wine_option)
    
    incoming = request.args.get('incoming')
    return render_template("main.html", incoming=incoming)

@app.route('/dropdown', methods=["GET", "POST"])
def dropdown():
    incoming = request.args.get('incoming')
    selected_option = request.args.get('selectedOption')
    if int(selected_option) == 5 or int(selected_option) == 7:
        return render_template("beer.html", incoming=incoming, selected_option=selected_option)
    else:
        return render_template("wine.html", incoming=incoming, selected_option=selected_option)

@app.route("/chatGPT_response")
def chatGPT_response():
    user_input = request.args.get("chatbot_input", "")
    wine_option = request.args.get("chatbot_radio", "")
    if db_connection.is_connected():
        cursor = db_connection.cursor(dictionary=True)
        query = "SELECT RSTRNT_NM,RSTRNT_KEY FROM ai_rstrnt WHERE ChatGPT_IND = 'Y'"
        cursor.execute(query)
        restaurants = cursor.fetchall()
    conversation = [
            {"role": "system", "content": "You are WineBuddy, the Virtual Sommelier."},
            {"role": "system", "content": f'According to famous sommeliers, what {user_input}? {wine_option}'},

        ]
    print(conversation)
    chatbot_response = get_chatbot_response(conversation)
    #formatted_response, headings = extract_clickable_headings(chatbot_response)

    matched_varietals = []

        # Query the database to get varietals that match the headings
    if db_connection.is_connected():
        cursor = db_connection.cursor()
        #for heading in headings:
        query = "SELECT VRTL_NM,VRTL_KEY FROM AI_VRTL"
        cursor.execute(query)
        matched_varietals = cursor.fetchall()
    formatted_response = chatbot_response
    for varietal, varietal_key in matched_varietals:
        varietal_link = f'<a href="/restaurants?key={varietal_key}">{varietal}</a>'
        formatted_response = formatted_response.replace(varietal, varietal_link, 1)

    # Split response into paragraphs while preserving links
    paragraphs_with_links = formatted_response.split('\n\n')

    return render_template("chatGPT_response.html", paragraphs_with_links=paragraphs_with_links,test=matched_varietals)

@app.route("/restaurants")
def restaurants():
    key = request.args.get("key")

    if db_connection.is_connected():
        cursor = db_connection.cursor(dictionary=True)
        query = "SELECT RSTRNT_NM,RSTRNT_KEY FROM ai_rstrnt WHERE ChatGPT_IND = 'Y'"
        cursor.execute(query)
        restaurants = cursor.fetchall()
        return render_template("restaurants.html", restr=restaurants, key_value=key)


@app.route("/external_URL", methods=["GET", "POST"])
def external_URL():
    if request.method == "POST":
        selected_restaurant_key = request.form.get("selected_restaurant")
        keyValue = request.form.get("keyvalue")
            # Replace your_vrtl_key_here with the appropriate value
            # Get the target URL using the separate function
        target_url = get_target_url(selected_restaurant_key,keyValue)
        if target_url:
            return redirect(target_url)
        else:
            # Handle the case where target_url is not available
            return """
                <html>
                <head>
                    <script>
                        alert("Target URL not found");
                        window.location.href = "/restaurants";  // Redirect to the restaurants URL
                    </script>
                </head>
                <body>
                    <p>If you are not redirected, <a href="/restaurants">click here</a>.</p>
                </body>
                </html>
            """, 404
    else:
        # Handle GET request or other methods
        return "Invalid request method", 405


def get_target_url(restaurant_key, vrtl_key):
    if db_connection.is_connected():
        cursor = db_connection.cursor(dictionary=True)
        query = """
            SELECT AFLT_VTRL_URL FROM aflt_vtrl_url
            WHERE RSTRNT_KEY = %s AND VRTL_KEY = %s
        """
        cursor.execute(query, (restaurant_key, vrtl_key))
        url_result = cursor.fetchone()

        if url_result:
            return url_result["AFLT_VTRL_URL"]
    else:
        # Handle GET request or other methods
        return "Invalid request method", 405

@app.route("/restaurant")
def restaurant():
    ai_cstmr_key = request.args.get('ai_cstmr_key')
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True)
    query="""SELECT distinct WINE_SELR.WINE_SELR_NM, CSTMR_WIN_SELR.CSTMR_WINE_URL FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""

    cursor.execute(query, (ai_cstmr_key,))
    restaurants = cursor.fetchall()
    return render_template("restraunt.html", wines = restaurants)

@app.route("/explore-beer")
def explore_beer():
    return render_template('beer.html')

@app.route("/explore-wine")
def explore_wine():
    return render_template('wine.html')

from flask import jsonify
import base64

@app.route('/homescreen', methods=['GET'])
def get_homescreen():
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True)
        # query = """SELECT logo, tagline, wine_image, wine_heading, wine_description, beer_image, beer_heading, beer_description FROM ai_homescreen"""
        query = """SELECT logo_img_urlbb_txt, tagline, wine_img_urlbb_txt, wine_heading, wine_description, beer_img_urlbb_txt, beer_heading, beer_description, input_field_text FROM ai_homescreen"""
        cursor.execute(query)
        data = cursor.fetchall()

        # for i in data:
        #     if i['logo']:
        #         i['logo'] = base64.b64encode(i['logo']).decode('utf-8')

        #     if i['wine_image']:
        #         i['wine_image'] = base64.b64encode(i['wine_image']).decode('utf-8')

        #     if i['beer_image']:
        #         i['beer_image'] = base64.b64encode(i['beer_image']).decode('utf-8')

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/wines', methods=['GET'])
def get_wines_country():
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True)
    try:
        query_wine_logo = """SELECT logo_img_urlbb_txt FROM ai_homescreen"""
        cursor.execute(query_wine_logo)
        query_wine_logo = cursor.fetchall()

        query = """SELECT AI_CSTMR_NAME, IMG_URLBB_TXT FROM ai_cstmr WHERE ACTV_IND = 'Y' AND IS_WINE = 'Y'"""
        cursor.execute(query)
        wines_country = cursor.fetchall()

        # for wine in wines_country:
        #     if wine['CHTBX_LOGO_IMG']:
        #         wine['CHTBX_LOGO_IMG'] = base64.b64encode(wine['CHTBX_LOGO_IMG']).decode('utf-8')

        query_wine_pairings = """SELECT WINE_HEADING, WINE_DESCRIPTION FROM pairings_screen"""
        cursor.execute(query_wine_pairings)
        query_wine_pairings = cursor.fetchall()

        # for i in query_wine_pairings:
        #     if i['LOGO']:
        #         i['LOGO'] = base64.b64encode(i['LOGO']).decode('utf-8')

        combined_data = {
            "wines_country": wines_country,
            "query_wine_pairings": query_wine_pairings,
            "query_wine_logo" : query_wine_logo
        }

        return jsonify(combined_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/beers', methods=['GET'])
def get_beers_country():
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True)
    try:
        query_beer_logo = """SELECT logo_img_urlbb_txt FROM ai_homescreen"""
        cursor.execute(query_beer_logo)
        query_beer_logo = cursor.fetchall()

        query = """SELECT AI_CSTMR_NAME, IMG_URLBB_TXT FROM ai_cstmr WHERE ACTV_IND = 'Y' AND IS_BEER = 'Y'"""
        cursor.execute(query)
        beers_country = cursor.fetchall()

        for beer in beers_country:
            beer['NAME'] = beer['AI_CSTMR_NAME'][4:]
            # if beer['CHTBX_LOGO_IMG']:
            #     beer['CHTBX_LOGO_IMG'] = base64.b64encode(beer['CHTBX_LOGO_IMG']).decode('utf-8')

        query_beer_pairings = """SELECT BEER_HEADING, BEER_DESCRIPTION FROM pairings_screen"""
        cursor.execute(query_beer_pairings)
        query_beer_pairings = cursor.fetchall()

        # for i in query_beer_pairings:
        #     if i['LOGO']:
        #         i['LOGO'] = base64.b64encode(i['LOGO']).decode('utf-8')

        combined_data = {
            "beers_country": beers_country,
            "query_beer_pairings": query_beer_pairings,
            "query_beer_logo": query_beer_logo
        }

        return jsonify(combined_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/capture_food', methods=['POST'])
def capture_food():
    data = request.get_json()
    food_input = data.get('food')
    session['food_input'] = food_input
    return jsonify({'message': 'Input received successfully!'})

@app.route('/display_food', methods=['GET'])
def display_food_api():
    food_input = session.get('food_input', 'No food input provided')
    return jsonify({'food_input': food_input})


if __name__ == "__main__":
    app.run(debug=True)


