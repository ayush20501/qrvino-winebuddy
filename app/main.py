from flask import Flask, render_template, request,redirect,session
import openai
import re
import mysql.connector
from app.config import openai, create_database_connection
from app.customer_routes import customers_bp

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = '112233'
app.register_blueprint(customers_bp)

openai.api_key = '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'

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
           return redirect("/customer/recommendations?chatbot_input=" + user_input + "&chatbot_radio=" + wine_option + "&customerName=" + customer_name)
        else:
            return redirect("/recommendations?chatbot_input=" + user_input + "&chatbot_radio=" + wine_option)
    
    incoming = request.args.get('incoming')
    return render_template("home.html", incoming=incoming)

@app.route('/brands', methods=["GET", "POST"])
def show_brands():
    incoming = request.args.get('incoming')
    selected_option = request.args.get('selectedOption')
    if int(selected_option) == 5 or int(selected_option) == 7:
        return render_template("beer_brands.html", incoming=incoming, selected_option=selected_option)
    else:
        return render_template("wine_brands.html", incoming=incoming, selected_option=selected_option)

@app.route("/recommendations")
def get_recommendations():
    user_input = request.args.get("chatbot_input", "")
    wine_option = request.args.get("chatbot_radio", "")
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(buffered=True)
        query = "SELECT VRTL_NM,VRTL_KEY FROM AI_VRTL"
        cursor.execute(query)
        matched_varietals = cursor.fetchall()
    except Exception as e:
        matched_varietals = []
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

    conversation = [
            {"role": "system", "content": "You are WineBuddy, the Virtual Sommelier."},
            {"role": "system", "content": f'According to famous sommeliers, what {user_input}? {wine_option}'},
        ]
    chatbot_response = get_chatbot_response(conversation)

    formatted_response = chatbot_response
    for varietal, varietal_key in matched_varietals:
        varietal_link = f'<a href="/stores?key={varietal_key}">{varietal}</a>'
        formatted_response = formatted_response.replace(varietal, varietal_link, 1)

    paragraphs_with_links = formatted_response.split('\n\n')

    return render_template("recommendations_text.html", paragraphs_with_links=paragraphs_with_links,test=matched_varietals)

@app.route("/stores")
def show_stores():
    key = request.args.get("key")
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = "SELECT RSTRNT_NM,RSTRNT_KEY FROM ai_rstrnt WHERE ChatGPT_IND = 'Y'"
        cursor.execute(query)
        restaurants = cursor.fetchall()
        template = "store_selection_modal.html" if request.args.get("modal") == "1" else "store_selection.html"
        return render_template(template, restr=restaurants, key_value=key)
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

@app.route("/redirect", methods=["GET", "POST"])
def redirect_external():
    if request.method == "POST":
        selected_restaurant_key = request.form.get("selected_restaurant")
        vrtl_key = request.form.get("vrtlkey") or request.form.get("keyvalue")
        reg_key = request.form.get("regkey")
        is_customer = "vrtlkey" in request.form
        
        if is_customer:
            from app.customer_routes import get_target_url as get_cust_target_url
            if vrtl_key and reg_key:
                from app.customer_routes import get_target_url_reg
                target_url = get_target_url_reg(selected_restaurant_key, reg_key, vrtl_key)
            else:
                target_url = get_cust_target_url(selected_restaurant_key, vrtl_key)
        else:
            target_url = get_target_url(selected_restaurant_key, vrtl_key)
            
        if target_url:
            return redirect(target_url)
        else:
            back_url = "/customer/stores" if is_customer else "/stores"
            return f"""
                <html>
                <head>
                    <script>
                        alert("Target URL not found");
                        window.location.href = "{back_url}";
                    </script>
                </head>
                <body>
                    <p>If you are not redirected, <a href="{back_url}">click here</a>.</p>
                </body>
                </html>
            """, 404
    else:
        return "Invalid request method", 405

def get_target_url(restaurant_key, vrtl_key):
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = """
            SELECT AFLT_VTRL_URL FROM aflt_vtrl_url
            WHERE RSTRNT_KEY = %s AND VRTL_KEY = %s
        """
        cursor.execute(query, (restaurant_key, vrtl_key))
        url_result = cursor.fetchone()
        if url_result:
            return url_result["AFLT_VTRL_URL"]
    except Exception as e:
        pass
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
    return False

@app.route("/wines/selection")
def select_wine():
    ai_cstmr_key = request.args.get('ai_cstmr_key')
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query="""SELECT distinct WINE_SELR.WINE_SELR_NM, CSTMR_WIN_SELR.CSTMR_WINE_URL FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
        cursor.execute(query, (ai_cstmr_key,))
        restaurants = cursor.fetchall()
        return render_template("wine_selection.html", wines = restaurants)
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

@app.route("/explore-beer")
def explore_beer():
    return render_template('beer_brands.html')

@app.route("/explore-wine")
def explore_wine():
    return render_template('wine_brands.html')

from flask import jsonify
import base64

@app.route('/homescreen', methods=['GET'])
def get_homescreen():
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = """SELECT logo_img_urlbb_txt, tagline, wine_img_urlbb_txt, wine_heading, wine_description, beer_img_urlbb_txt, beer_heading, beer_description, input_field_text FROM ai_homescreen"""
        cursor.execute(query)
        data = cursor.fetchall()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

@app.route('/wines', methods=['GET'])
def get_wines_country():
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query_wine_logo = """SELECT logo_img_urlbb_txt FROM ai_homescreen"""
        cursor.execute(query_wine_logo)
        query_wine_logo = cursor.fetchall()

        query = """SELECT AI_CSTMR_NAME, IMG_URLBB_TXT FROM ai_cstmr WHERE ACTV_IND = 'Y' AND IS_WINE = 'Y'"""
        cursor.execute(query)
        wines_country = cursor.fetchall()

        query_wine_pairings = """SELECT WINE_HEADING, WINE_DESCRIPTION FROM pairings_screen"""
        cursor.execute(query_wine_pairings)
        query_wine_pairings = cursor.fetchall()

        combined_data = {
            "wines_country": wines_country,
            "query_wine_pairings": query_wine_pairings,
            "query_wine_logo" : query_wine_logo
        }
        return jsonify(combined_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

@app.route('/beers', methods=['GET'])
def get_beers_country():
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query_beer_logo = """SELECT logo_img_urlbb_txt FROM ai_homescreen"""
        cursor.execute(query_beer_logo)
        query_beer_logo = cursor.fetchall()

        query = """SELECT AI_CSTMR_NAME, IMG_URLBB_TXT FROM ai_cstmr WHERE ACTV_IND = 'Y' AND IS_BEER = 'Y'"""
        cursor.execute(query)
        beers_country = cursor.fetchall()

        for beer in beers_country:
            beer['NAME'] = beer['AI_CSTMR_NAME'][4:]

        query_beer_pairings = """SELECT BEER_HEADING, BEER_DESCRIPTION FROM pairings_screen"""
        cursor.execute(query_beer_pairings)
        query_beer_pairings = cursor.fetchall()

        combined_data = {
            "beers_country": beers_country,
            "query_beer_pairings": query_beer_pairings,
            "query_beer_logo": query_beer_logo
        }
        return jsonify(combined_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

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
