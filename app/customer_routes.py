from flask import Flask, render_template, request, redirect, g, Blueprint, session
from app.config import openai, create_database_connection, OPENAI_MODEL
import re
import mysql.connector
from bs4 import BeautifulSoup
import os
import logging
import base64
import time
import json

customers_bp = Blueprint('customers', __name__)

def make_clickable(match):
        word = match.group(1)
        return f'<a href="#" style="color:yellow" class="highlighted-word" onclick="selectCut(\'{word}\')">{word}</a>'

def slugify(text):
    text = str(text).strip().lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^\w\-]+', '', text)
    text = re.sub(r'\-\-+', '-', text)
    return text.strip('-')

def find_customer_by_slug(slug):
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT AI_CSTMR_START_TXT FROM ai_cstmr")
        rows = cursor.fetchall()
        for row in rows:
            raw_name = row['AI_CSTMR_START_TXT'].strip()
            if slugify(raw_name) == slug:
                return raw_name
    except Exception as e:
        logging.error(f"Error matching slug: {e}")
    finally:
        cursor.close()
        db_connection.close()
    return None

@customers_bp.route('/chat/<slug>')
def show_image(slug):
    page_name = find_customer_by_slug(slug)
    if not page_name:
        return redirect('/')
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = "SELECT CANA_IND, BEER_IND from ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query,('%' + page_name + '%',))
        result = cursor.fetchone()

        if result is not None and result['CANA_IND'] == 'Y':
            query = "SELECT RSTRNT_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,CHTBX_LOGO_IMG, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()
            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                prime_ind = result['PRIME_IND']
                image_data = result['CHTBX_LOGO_IMG']
                image_data_base64 = base64.b64encode(image_data).decode('utf-8') if image_data else ""
                first_line = result['CHTBX_FRST_LINE']
                second_line_from_database = result['CHTBX_SCND_LINE']
                ai_cstmr_key = result['AI_CSTMR_KEY']
                session['ai_cstmr_key'] = ai_cstmr_key

                options_list = []
                for i in range(1, 11):
                    opt = result[f'OPTION_{i}_TXT']
                    if opt and opt != 'null' and opt != '':
                        options_list.append({'id': i, 'text': opt})

                if meat_cut_ind == 'Y':
                    second_line_from_database = re.sub(r'\*([^\*]+)\*', make_clickable, second_line_from_database)
                session['theme_color'] = 'Y'
                return render_template('customer_chat.html', image_data=image_data_base64, first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "Y", options = options_list, rstrnt_ind=rstrnt_ind, prime_ind=prime_ind)
            else:
                return {'page_name': page_name}

        elif result is not None and result['BEER_IND'] == 'Y':
            query = "SELECT RSTRNT_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,CHTBX_LOGO_IMG, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()

            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                prime_ind = result['PRIME_IND']
                image_data = result['CHTBX_LOGO_IMG']
                image_data_base64 = base64.b64encode(image_data).decode('utf-8') if image_data else ""
                first_line = result['CHTBX_FRST_LINE']
                second_line_from_database = result['CHTBX_SCND_LINE']
                ai_cstmr_key = result['AI_CSTMR_KEY']
                session['ai_cstmr_key'] = ai_cstmr_key

                options_list = []
                for i in range(1, 11):
                    opt = result[f'OPTION_{i}_TXT']
                    if opt and opt != 'null' and opt != '':
                        options_list.append({'id': i, 'text': opt})
                
                matches_list = []
                intro_text = ""
                if meat_cut_ind == 'Y':
                    intro_text_match = re.match(r'([^*]+):', second_line_from_database)
                    intro_text = intro_text_match.group(1)+":" if intro_text_match else ""
                    matches_list = re.findall(r'\*([^\*]+)\*', second_line_from_database)

                matches_list = sorted(matches_list)
                session['theme_color'] = 'G'
                return render_template('customer_chat.html',intro_text=intro_text, matches_list = matches_list,image_data=image_data_base64, first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "G", options = options_list, rstrnt_ind=rstrnt_ind, prime_ind=prime_ind)
            else:
                return {'page_name': page_name}
        else:
            query = "SELECT RSTRNT_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,CHTBX_LOGO_IMG, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()
            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                prime_ind = result['PRIME_IND']
                image_data = result['CHTBX_LOGO_IMG']
                image_data_base64 = base64.b64encode(image_data).decode('utf-8') if image_data else ""
                first_line = result['CHTBX_FRST_LINE']
                second_line_from_database = result['CHTBX_SCND_LINE']
                ai_cstmr_key = result['AI_CSTMR_KEY']
                session['ai_cstmr_key'] = ai_cstmr_key

                options_list = []
                for i in range(1, 11):
                    opt = result[f'OPTION_{i}_TXT']
                    if opt and opt != 'null' and opt != '':
                        options_list.append({'id': i, 'text': opt})

                query = "SELECT CSTMR_WINE_URL FROM CSTMR_WIN_SELR WHERE AI_CSTMR_KEY = %s"
                cursor.execute(query, (ai_cstmr_key,))
                result = cursor.fetchone()
                image_url = result['CSTMR_WINE_URL']

                if image_url == '' or image_url == 'null':
                    image_url = False
                
                matches_list = []
                intro_text = ""

                if meat_cut_ind == 'Y':
                    intro_text_match = re.match(r'([^*]+):', second_line_from_database)
                    intro_text = intro_text_match.group(1)+":" if intro_text_match else ""
                    matches_list = re.findall(r'\*([^\*]+)\*', second_line_from_database)
                matches_list = sorted(matches_list)
                session['theme_color'] = 'N'
                return render_template('customer_chat.html',intro_text=intro_text, matches_list = matches_list, ai_cstmr_key = ai_cstmr_key, image_data=image_data_base64,image_url = image_url,
                first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "N", options = options_list, rstrnt_ind=rstrnt_ind, prime_ind=prime_ind)
            else:
                return {'page_name': page_name}
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

@customers_bp.route('/customer/recommendations', methods=['POST'])
def get_customer_recommendations():
    db_connection = None
    cursor = None
    try:
        link_exists = False
        link_reg_exists = False
        both_links_exist = False
        myflag=0
        cl=None
        user_input = request.form.get("user_input")
        wine_option = request.form.get('wine_option')
        customer_name = request.form.get('customer_name')
        
        if not wine_option or not str(wine_option).isdigit() or not (1 <= int(wine_option) <= 10):
            wine_option = "1"
            
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)

        query = "SELECT RSTRNT_IND, NO_WINE_BEER_IND FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query, ('%' + customer_name + '%',))
        rstrnt_result = cursor.fetchone()
        rstrnt_ind = rstrnt_result['RSTRNT_IND'] if rstrnt_result else 'N'
        no_wine_beer_ind = rstrnt_result['NO_WINE_BEER_IND'] if rstrnt_result else 'N'

        prompt_column = f"PROMPT_TXT_{wine_option}"
        query = f"SELECT {prompt_column} FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query, ('%' + customer_name + '%',))
        cstmr_result = cursor.fetchone()
        prompt_result = str(cstmr_result[prompt_column]) if cstmr_result else ""

        theme_color = session.get('theme_color', 'N')

        if theme_color == 'G':
            beer_pairings = get_beer_pairings(prompt_result, user_input)
            if not beer_pairings:
                return "No response from chatbot"
            cursor.execute("SELECT VRTL_NM,VRTL_KEY FROM ai_vrtl")
            beer_varietals = cursor.fetchall()
            headers = ["Varietal", "Sommelier Notes"]
            html_table = "<table>\n<thead>\n" + "".join(f"<th>{h}</th>\n" for h in headers) + "\n</thead><tbody>\n"
            for p in beer_pairings:
                name = (p.get("name") or "").strip()
                matched = next((item for item in beer_varietals if item['VRTL_NM'].strip().lower() == name.lower()), None)
                name_cell = f'<a href="/customer/stores?key={matched["VRTL_KEY"]}&testflag=1">{matched["VRTL_NM"]}</a>' if matched else name
                raw_notes = p.get("sommelier_notes", "")
                formatted_notes = raw_notes.replace("\n", "<br>")
                formatted_notes = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_notes)
                html_table += (
                    "<tr>\n"
                    f"<td>{name_cell}</td>\n"
                    f"<td>{formatted_notes}</td>\n"
                    "</tr>\n"
                )
            html_table += "</tbody>\n</table>"
            return render_template("recommendations_table.html", token=1, var=html_table, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=theme_color)

        if theme_color == 'N':
            wine_pairings = get_wine_pairings(prompt_result, user_input)
            if not wine_pairings:
                return "No response from chatbot"
            cursor.execute("SELECT VRTL_NM,VRTL_KEY FROM ai_vrtl")
            wine_varietals = cursor.fetchall()
            headers = ["Varietal", "Sommelier Notes"]
            html_table = "<table>\n<thead>\n" + "".join(f"<th>{h}</th>\n" for h in headers) + "\n</thead><tbody>\n"
            for p in wine_pairings:
                name = (p.get("name") or "").strip()
                matched = next((item for item in wine_varietals if item['VRTL_NM'].strip().lower() == name.lower()), None)
                name_cell = f'<a href="/customer/stores?key={matched["VRTL_KEY"]}&testflag=1">{matched["VRTL_NM"]}</a>' if matched else name
                raw_notes = p.get("sommelier_notes", "")
                formatted_notes = raw_notes.replace("\n", "<br>")
                formatted_notes = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', formatted_notes)
                html_table += (
                    "<tr>\n"
                    f"<td>{name_cell}</td>\n"
                    f"<td>{formatted_notes}</td>\n"
                    "</tr>\n"
                )
            html_table += "</tbody>\n</table>"
            return render_template("recommendations_table.html", token=1, var=html_table, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=theme_color)

        table_instruction = ("Please return response in tabular format with exactly 5 columns: "
                             "Wine Style Name | Flavor Profile | Pairing Notes | Best Glass | Best Serving Temperature. "
                             "Flavor Profile column: Flavor: <value>, Aroma: <value>, Tannins: <value>, Taste: <value>, ABV: <value>. "
                             "Pairing Notes column: 2-3 sentences explaining why this wine pairs well with the dish. "
                             "Best Glass column: only the glass type. "
                             "Best Serving Temperature column: only the serving temperature.")

        conversation = [
            {"role": "system", "content": "You are WineBuddy and BeerBuddy the Virtual Sommelier for wine and beer. You can recommend wine or beer as asked. " + table_instruction},
            {"role": "user", "content": f'{prompt_result}? {user_input}'},
        ]
        print("--- SYSTEM PROMPT ---")
        print(conversation[0]["content"])
        print("--- USER PROMPT (DB + USER INPUT) ---")
        print(conversation[1]["content"])
        print("-------------------------------------")
        chatbot_response = get_chatbot_response(conversation)
        matched_varietals = []
        query = "SELECT VRTL_NM,VRTL_KEY FROM ai_vrtl"
        cursor.execute(query)
        matched_varietals = cursor.fetchall()
        matched_regions = []
        query = "SELECT CNTRGN_KEY,CNTRGN_NM FROM CNTRGN"
        cursor.execute(query)
        matched_regions = cursor.fetchall()
        if chatbot_response is not None:
            matched_column_no = None
            tabular_pattern = re.compile(r'\|')
            if tabular_pattern.search(chatbot_response):
                lines = chatbot_response.strip().split('\n')
                start_index = next((index for index, line in enumerate(lines) if '|' in line), None)
                if start_index is not None:
                    headers = [header.strip() for header in lines[start_index].split('|') if header.strip()]
                    data_lines = [line.strip() for line in lines[start_index + 2:]]
                    target_words = ["regions", "countries", "regions/countries","countries/regions"]
                    for i, header in enumerate(headers, 1):
                        for word in target_words:
                            if word in header.lower():
                                matched_column_no = i
                                break
                        if matched_column_no is not None:
                            cl=matched_column_no-1
                            break
                html_table = "<table>\n<thead>\n"
                html_table += "".join([f"<th>{header}</th>\n" for header in headers])
                html_table += "\n</thead><tbody>\n"

                for line in data_lines:
                    if '---' in line:
                        continue
                    columns = [column.strip() for column in line.split('|') if column.strip()]
                    if len(columns)<=0:
                        break
                    if columns and columns[0]:
                        matched = next((item for item in matched_varietals if item['VRTL_NM'].strip().lower() == columns[0].strip().lower()), None)
                        if matched:
                            link_exists = True
                            myflag=1
                            link = f'<a href="/customer/stores?key={matched["VRTL_KEY"]}&testflag={myflag}">{matched["VRTL_NM"]}</a>'
                            columns[0] = link
                    if cl is not None :
                        column_words_processed = [(word.split('(')[0].replace(" ", "").lower().strip() if '(' in word else word.replace(" ", "").lower().strip())
                        for word in columns[matched_column_no - 1].split(',')]
                        matched_reg = next((itemreg for itemreg in matched_regions if any(word in itemreg['CNTRGN_NM'].replace(" ", "").lower().strip() for word in column_words_processed)), None)
                        if matched_reg:
                            link_reg_exists = True
                            if link_exists and link_reg_exists:
                                myflag=3
                            link_reg = f'<a href="/customer/stores?testflag={myflag}&vrtlkey={matched["VRTL_KEY"]}&keyreg={matched_reg["CNTRGN_KEY"]}">{matched_reg["CNTRGN_NM"]}</a>'
                            columns[matched_column_no-1] = link_reg
                    html_table += "<tr>\n"
                    html_table += "".join([f"<td>{column}</td>\n" for column in columns])
                    html_table += "</tr>\n"
                html_table += "</tbody>\n</table>"
                return render_template("recommendations_table.html", token=1, var=html_table, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=session.get('theme_color', 'N'))
            else:
                formatted_response = chatbot_response
                for varietal, varietal_key in matched_varietals:
                    varietal_link = f'<a href="/customer/stores?key={varietal_key}">{varietal}</a>'
                    formatted_response = formatted_response.replace(varietal, varietal_link, 1)
                paragraphs_with_links = formatted_response.split('\n\n')
                return render_template("recommendations_table.html", paragraphs_with_links=paragraphs_with_links, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=session.get('theme_color', 'N'))
        else:
            return "No response from chatbot"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

def get_chatbot_response(messages):
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0
    }
    print("--- OPENAI API PAYLOAD ---")
    print(json.dumps(payload, indent=2))
    print("--------------------------")
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0
            )
            return response.choices[0].message["content"]
        except Exception as e:
            logging.error(f"OpenAI attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(1)
    return None

def get_beer_pairings(prompt_result, user_input):
    functions = [{
        "name": "return_beer_pairings",
        "description": "Return a list of beer pairing recommendations for the requested dish.",
        "parameters": {
            "type": "object",
            "properties": {
                "pairings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Beer style, brand or variety name"},
                            "sommelier_notes": {
                                "type": "string",
                                "description": "Sommelier notes about the beer. You must strictly follow the user's prompt instructions for what details to include, formatting each detail/field label in bold and on a new line using markdown format (e.g., '**Label:** Value\\n')."
                            }
                        },
                        "required": ["name", "sommelier_notes"]
                    }
                }
            },
            "required": ["pairings"]
        }
    }]
    messages = [
        {"role": "system", "content": (
            "You are BeerBuddy, an expert virtual beer sommelier. Recommend suitable beers and strictly return them using the return_beer_pairings function. "
            "CRITICAL RULES FOR 'sommelier_notes': You must dynamically identify every specific detail requested by the user prompt. "
            "You are strictly forbidden from grouping multiple details into a single paragraph. "
            "You must format the notes as a strict vertical list where each requested detail is on its own separate new line (\\n). "
            "Every field label you extract must be strictly wrapped in double asterisks followed by a colon and a space. "
            "For example, if the user asks for origin and taste, output exactly: '**Origin:** [value]\\n**Taste:** [value]'. "
            "If they ask for grape and body, output exactly: '**Grape:** [value]\\n**Body:** [value]'. "
            "Failure to follow this exact bolded, line-by-line format will result in a system error."
        )},
        {"role": "user", "content": f'{prompt_result}? {user_input}'}
    ]
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "functions": functions,
        "function_call": {"name": "return_beer_pairings"},
        "temperature": 0
    }
    print("--- OPENAI API PAYLOAD ---")
    print(json.dumps(payload, indent=2))
    print("--------------------------")
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                functions=functions,
                function_call={"name": "return_beer_pairings"},
                temperature=0
            )
            arguments = response.choices[0].message["function_call"]["arguments"]
            return json.loads(arguments).get("pairings", [])
        except Exception as e:
            logging.error(f"OpenAI beer attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(1)
    return None

def get_wine_pairings(prompt_result, user_input):
    functions = [{
        "name": "return_wine_pairings",
        "description": "Return a list of wine pairing recommendations for the requested dish.",
        "parameters": {
            "type": "object",
            "properties": {
                "pairings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Wine style, varietal or brand name"},
                            "sommelier_notes": {
                                "type": "string",
                                "description": "Sommelier notes about the wine. You must strictly follow the user's prompt instructions for what details to include, formatting each detail/field label in bold and on a new line using markdown format (e.g., '**Label:** Value\\n')."
                            }
                        },
                        "required": ["name", "sommelier_notes"]
                    }
                }
            },
            "required": ["pairings"]
        }
    }]
    messages = [
        {"role": "system", "content": (
            "You are WineBuddy, an expert virtual wine sommelier. Recommend suitable wines and strictly return them using the return_wine_pairings function. "
            "CRITICAL RULES FOR 'sommelier_notes': You must dynamically identify every specific detail requested by the user prompt. "
            "You are strictly forbidden from grouping multiple details into a single paragraph. "
            "You must format the notes as a strict vertical list where each requested detail is on its own separate new line (\\n). "
            "Every field label you extract must be strictly wrapped in double asterisks followed by a colon and a space. "
            "For example, if the user asks for origin and taste, output exactly: '**Origin:** [value]\\n**Taste:** [value]'. "
            "If they ask for grape and body, output exactly: '**Grape:** [value]\\n**Body:** [value]'. "
            "Failure to follow this exact bolded, line-by-line format will result in a system error."
        )},
        {"role": "user", "content": f'{prompt_result}? {user_input}'}
    ]
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "functions": functions,
        "function_call": {"name": "return_wine_pairings"},
        "temperature": 0
    }
    print("--- OPENAI API PAYLOAD ---")
    print(json.dumps(payload, indent=2))
    print("--------------------------")
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                functions=functions,
                function_call={"name": "return_wine_pairings"},
                temperature=0
            )
            arguments = response.choices[0].message["function_call"]["arguments"]
            return json.loads(arguments).get("pairings", [])
        except Exception as e:
            logging.error(f"OpenAI wine attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(1)
    return None

def _store_selection_template():
    return "store_selection_modal.html" if request.args.get("modal") == "1" else "store_selection.html"

@customers_bp.route('/customer/stores')
def show_customer_stores():
    testflag = request.args.get("testflag")
    db_connection = None
    cursor = None
    if testflag == "3":
        if 'key' in request.args:
            ai_vrtl_key = request.args.get("key")
            session['ai_vrtl_key'] = ai_vrtl_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True, buffered=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template(_store_selection_template(), restr=restaurants, vrtl_key=ai_vrtl_key)
            except Exception as e:
                return f"Error1: {str(e)}"
            finally:
                if cursor:
                    cursor.close()
                if db_connection:
                    db_connection.close()
        else:
            ai_reg_key = request.args.get("keyreg")
            aivrtlkey = request.args.get("vrtlkey")
            session['ai_reg_key'] = ai_reg_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True, buffered=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template(_store_selection_template(), restr=restaurants,reg_key=ai_reg_key,vrtl=aivrtlkey)
            except Exception as e:
                return f"Error2: {str(e)}"
            finally:
                if cursor:
                    cursor.close()
                if db_connection:
                    db_connection.close()
    elif testflag == "1":
       if 'key' in request.args:
            ai_vrtl_key = request.args.get("key")
            session['ai_vrtl_key'] = ai_vrtl_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True, buffered=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template(_store_selection_template(), restr=restaurants, vrtl_key=ai_vrtl_key)
            except Exception as e:
                return f"Error3: {str(e)}"
            finally:
                if cursor:
                    cursor.close()
                if db_connection:
                    db_connection.close()
    else:
        return"There is no match wine seller"

def get_target_url(restaurant_key, vrtl_key):
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = """
            SELECT AFLT_VTRL_URL FROM aflt_vtrl_url
            WHERE WINE_SELR_KEY = %s AND VRTL_KEY = %s
            """
        cursor.execute(query, (restaurant_key, vrtl_key))
        url_result = cursor.fetchone()
        if url_result:
            return url_result["AFLT_VTRL_URL"]
    except Exception as e:
        logging.error(f"Error in get_target_url: {e}")
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
    return False

def get_target_url_reg(restaurant_key,reg_key,vrtl):
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = """
            SELECT AFLT_VTRL_URL_TXT FROM AFLT_CNTRGN_URL
            WHERE WINE_SELR_KEY = %s AND CNTRGN_KEY = %s AND VRTL_KEY = %s
            """
        cursor.execute(query, (restaurant_key, reg_key,vrtl))
        url_result = cursor.fetchone()
        if url_result:
            return url_result["AFLT_VTRL_URL_TXT"]
    except Exception as e:
        logging.error(f"Error in get_target_url_reg: {e}")
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
    return False
